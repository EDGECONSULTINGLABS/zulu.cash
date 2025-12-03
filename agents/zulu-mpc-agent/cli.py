#!/usr/bin/env python3
"""Command-line interface for ZULU MPC Agent."""

# CRITICAL: Set this FIRST, before ANY imports
# PyTorch 2.6+ has weights_only=True by default which breaks PyAnnote models
import os
os.environ['TORCH_FORCE_WEIGHTS_ONLY_LOAD'] = '0'

import json
import sys
import warnings
from pathlib import Path
from typing import Optional

# Suppress pkg_resources deprecation warning from ctranslate2
warnings.filterwarnings("ignore", category=UserWarning, module="ctranslate2")

import click
from rich.console import Console
from rich.table import Table
from rich import print as rprint

from agent_core import WhisperDiarizationAgent, load_config, setup_logging

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

console = Console(force_terminal=True, legacy_windows=False)


@click.group()
@click.option(
    '--config',
    '-c',
    type=click.Path(exists=True),
    help='Path to config file',
)
@click.option(
    '--verbose',
    '-v',
    is_flag=True,
    help='Enable verbose logging',
)
@click.pass_context
def cli(ctx, config: Optional[str], verbose: bool):
    """ZULU MPC Agent - Privacy-preserving voice AI."""
    ctx.ensure_object(dict)
    
    # Load configuration
    cfg = load_config(config)
    
    # Setup logging
    log_level = "DEBUG" if verbose else cfg.logging.level
    setup_logging(
        level=log_level,
        log_file=cfg.logging.file,
        max_size_mb=cfg.logging.max_size_mb,
        backup_count=cfg.logging.backup_count,
    )
    
    ctx.obj['config'] = cfg


@cli.command()
@click.argument('audio_file', type=click.Path(exists=True))
@click.option('--title', '-t', help='Call title')
@click.option('--language', '-l', default='en', help='Audio language')
@click.pass_context
def process(ctx, audio_file: str, title: Optional[str], language: str):
    """Process an audio file."""
    cfg = ctx.obj['config']
    
    console.print(f"\n[bold cyan]Processing:[/bold cyan] {audio_file}\n")
    
    # Initialize agent
    with console.status("[bold green]Initializing agent..."):
        agent = _create_agent(cfg)
    
    # Prepare metadata
    meta = {
        'title': title or Path(audio_file).stem,
        'language': language,
        'source_file': str(audio_file),
    }
    
    # Process call
    try:
        with console.status("[bold green]Processing call..."):
            session_id = agent.process_call(audio_file, meta)
        
        console.print(f"\n[bold green][OK][/bold green] Success!")
        console.print(f"Session ID: [bold]{session_id}[/bold]\n")
        
        # Show summary
        summary = agent.get_session_summary(session_id)
        _display_session_summary(summary)
        
    except Exception as e:
        console.print(f"\n[bold red][X] Error:[/bold red] {e}\n")
        sys.exit(1)


@cli.command()
@click.option('--limit', '-n', default=10, help='Number of sessions to list')
@click.pass_context
def list(ctx, limit: int):
    """List recent sessions."""
    cfg = ctx.obj['config']
    
    # Initialize agent
    agent = _create_agent(cfg)
    
    # Get sessions
    sessions = agent.list_sessions(limit=limit)
    
    if not sessions:
        console.print("\n[yellow]No sessions found.[/yellow]\n")
        return
    
    # Display table
    table = Table(title=f"Recent Sessions (showing {len(sessions)})")
    table.add_column("ID", style="cyan")
    table.add_column("Title", style="white")
    table.add_column("Duration", justify="right")
    table.add_column("Speakers", justify="center")
    table.add_column("Created", style="dim")
    
    for session in sessions:
        duration = session.get('duration_seconds', 0)
        metadata = session.get('metadata', {})
        speaker_stats = metadata.get('speaker_stats', {})
        num_speakers = speaker_stats.get('num_speakers', '?')
        
        table.add_row(
            session['id'][:8],
            session['title'],
            f"{duration:.1f}s",
            str(num_speakers),
            session['created_at'][:19],
        )
    
    console.print()
    console.print(table)
    console.print()


@cli.command()
@click.argument('session_id')
@click.pass_context
def show(ctx, session_id: str):
    """Show detailed session information."""
    cfg = ctx.obj['config']
    
    # Initialize agent
    agent = _create_agent(cfg)
    
    # Get session
    summary = agent.get_session_summary(session_id)
    
    if not summary:
        console.print(f"\n[red]Session not found:[/red] {session_id}\n")
        sys.exit(1)
    
    _display_session_summary(summary)


@cli.command()
@click.argument('session_id')
@click.option('--confirm', is_flag=True, help='Skip confirmation')
@click.pass_context
def delete(ctx, session_id: str, confirm: bool):
    """Delete a session."""
    cfg = ctx.obj['config']
    
    if not confirm:
        if not click.confirm(f"Delete session {session_id}?"):
            return
    
    # Initialize agent
    agent = _create_agent(cfg)
    
    try:
        agent.delete_session(session_id)
        console.print(f"\n[green][OK][/green] Session deleted: {session_id}\n")
    except Exception as e:
        console.print(f"\n[red][X] Error:[/red] {e}\n")
        sys.exit(1)


@cli.command()
@click.pass_context
def health(ctx):
    """Check system health."""
    cfg = ctx.obj['config']
    
    console.print("\n[bold cyan]Health Check[/bold cyan]\n")
    
    # Initialize agent
    with console.status("[bold green]Checking components..."):
        agent = _create_agent(cfg)
        health_status = agent.health_check()
    
    # Display results
    for component, status in health_status.items():
        if component == 'overall':
            continue
        
        icon = "[OK]" if status else "[X]"
        color = "green" if status else "red"
        console.print(f"  [{color}]{icon}[/{color}] {component.capitalize()}: [bold]{status}[/bold]")
    
    console.print()
    overall = health_status.get('overall', False)
    if overall:
        console.print("[bold green]System is healthy[/bold green]\n")
    else:
        console.print("[bold red]System has issues[/bold red]\n")
        sys.exit(1)


@cli.command()
def init():
    """Initialize ZULU agent (create directories, check dependencies)."""
    console.print("\n[bold cyan]Initializing ZULU MPC Agent[/bold cyan]\n")
    
    # Create directories
    dirs = [
        "data/models/whisper",
        "data/backups",
        "data/temp",
        "logs",
    ]
    
    for dir_path in dirs:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        console.print(f"[green][OK][/green] Created: {dir_path}")
    
    # Check environment variables
    import os
    console.print("\n[bold]Environment Check:[/bold]")
    
    required_vars = {
        'ZULU_DB_KEY': 'Database encryption key',
    }
    
    optional_vars = {
        'NILLION_API_KEY': 'Nillion MPC API key (optional)',
        'HF_TOKEN': 'HuggingFace token for diarization (optional)',
    }
    
    for var, desc in required_vars.items():
        if os.getenv(var):
            console.print(f"  [green][OK][/green] {var}: Set")
        else:
            console.print(f"  [red][X][/red] {var}: Not set - {desc}")
    
    console.print()
    for var, desc in optional_vars.items():
        if os.getenv(var):
            console.print(f"  [green][OK][/green] {var}: Set")
        else:
            console.print(f"  [yellow]![/yellow] {var}: Not set - {desc}")
    
    console.print("\n[green]Initialization complete![/green]")
    console.print("\nNext steps:")
    console.print("1. Set ZULU_DB_KEY environment variable")
    console.print("2. Ensure Ollama is running: ollama serve")
    console.print("3. Pull a model: ollama pull llama3.1:8b")
    console.print("4. Process a call: zulu process <audio_file>\n")


def _create_agent(cfg) -> WhisperDiarizationAgent:
    """Create agent from config."""
    return WhisperDiarizationAgent(
        db_path=cfg.database.path,
        whisper_config=cfg.whisper.model_dump(),
        diarization_config=cfg.diarization.model_dump(),
        ollama_config=cfg.ollama.model_dump(),
        embeddings_config=cfg.embeddings.model_dump(),
        nillion_config=cfg.nillion.model_dump() if cfg.nillion.enabled else None,
        privacy_config=cfg.privacy.model_dump(),
        features_config=cfg.features.model_dump(),
    )


def _display_session_summary(summary: dict):
    """Display a session summary."""
    session = summary['session']
    utterances = summary['utterances']
    action_items = summary['action_items']
    decisions = summary['decisions']
    
    console.print("\n[bold cyan]Session Details[/bold cyan]")
    console.print(f"ID: [bold]{session['id']}[/bold]")
    console.print(f"Title: {session['title']}")
    console.print(f"Duration: {session['duration_seconds']:.1f}s")
    console.print(f"Language: {session['language']}")
    
    metadata = session.get('metadata', {})
    speaker_stats = metadata.get('speaker_stats', {})
    if speaker_stats:
        console.print(f"Speakers: {speaker_stats.get('num_speakers', '?')}")
    
    # Summary
    if session.get('summary'):
        console.print(f"\n[bold]Summary:[/bold]")
        console.print(session['summary'])
    
    # Action Items
    if action_items:
        console.print(f"\n[bold]Action Items ({len(action_items)}):[/bold]")
        for item in action_items:
            owner = item.get('owner_speaker', 'unknown')
            text = item.get('item', '')
            due = item.get('due_date', 'No deadline')
            console.print(f"  • [{owner}] {text} (Due: {due})")
    
    # Decisions
    if decisions:
        console.print(f"\n[bold]Decisions ({len(decisions)}):[/bold]")
        for decision in decisions:
            console.print(f"  • {decision['decision']}")
    
    # MPC Features
    mpc_features = summary.get('mpc_features', [])
    if mpc_features:
        console.print(f"\n[bold]MPC Features:[/bold]")
        for feature in mpc_features:
            kind = feature['feature_kind']
            result = feature.get('computation_result')
            if result and isinstance(result, dict):
                score = result.get('score')
                if score:
                    console.print(f"  • {kind}: {score:.4f}")
    
    console.print()


@cli.command()
@click.option('--model-size', '-m', default='medium', help='Whisper model size')
@click.option('--no-mpc', is_flag=True, help='Disable Nillion MPC integration')
@click.option('--keep-audio', is_flag=True, help='Keep audio file after processing')
def live_whisperx(model_size: str, no_mpc: bool, keep_audio: bool):
    """
    Run ZULU as a live privacy-first meeting assistant.
    
    Features:
    - Real-time audio capture from microphone
    - WhisperX transcription + speaker diarization (local)
    - Encrypted storage (SQLCipher)
    - Optional Nillion MPC for privacy-preserving analytics
    - Local LLM summarization
    
    Press Ctrl+C to stop recording and process the call.
    """
    console.print("\n[bold cyan]ZULU Live WhisperX Agent[/bold cyan]")
    console.print("="*60 + "\n")
    
    try:
        from live_whisperx_agent import ZuluLiveWhisperXMPC
    except ImportError as e:
        console.print("[bold red][X] Error:[/bold red] WhisperX dependencies not installed")
        console.print("\nInstall with:")
        console.print("  pip install whisperx sounddevice soundfile")
        console.print(f"\nDetails: {e}\n")
        sys.exit(1)
    
    try:
        # Initialize agent
        console.print("[*] Initializing live agent...\n")
        agent = ZuluLiveWhisperXMPC(
            model_size=model_size,
            enable_mpc=not no_mpc,
        )
        
        # Run live capture
        result = agent.run(auto_delete_audio=not keep_audio)
        
        # Display result
        if result['status'] == 'success':
            console.print(f"\n[bold green][OK] Session Complete[/bold green]")
            console.print(f"Session ID: [bold]{result['session_id']}[/bold]")
            console.print(f"Turns: {result['turns']}")
            console.print(f"Speakers: {result['speakers']}")
            console.print(f"Duration: {result['duration']:.1f}s")
            if result['mpc_enabled']:
                console.print("[MPC] MPC: Enabled (only embeddings sent)")
            console.print()
        else:
            console.print(f"\n[yellow]Status: {result['status']}[/yellow]\n")
            
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Interrupted by user[/yellow]\n")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[bold red][X] Error:[/bold red] {e}\n")
        import traceback
        if '--verbose' in sys.argv or '-v' in sys.argv:
            traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    cli()
