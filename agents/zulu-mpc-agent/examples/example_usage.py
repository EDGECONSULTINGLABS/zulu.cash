#!/usr/bin/env python3
"""Example script demonstrating ZULU MPC Agent usage."""

import sys
from pathlib import Path

from agent_core import WhisperDiarizationAgent, load_config, setup_logging


def main():
    """Run example pipeline."""
    
    # Setup
    print("🚀 ZULU MPC Agent - Example Usage\n")
    
    # Load configuration
    print("Loading configuration...")
    config = load_config()
    
    # Setup logging
    setup_logging(level="INFO")
    
    # Initialize agent
    print("Initializing agent...\n")
    agent = WhisperDiarizationAgent(
        db_path=config.database.path,
        whisper_config=config.whisper.model_dump(),
        diarization_config=config.diarization.model_dump(),
        ollama_config=config.ollama.model_dump(),
        embeddings_config=config.embeddings.model_dump(),
        nillion_config=config.nillion.model_dump() if config.nillion.enabled else None,
        privacy_config=config.privacy.model_dump(),
        features_config=config.features.model_dump(),
    )
    
    # Check health
    print("Checking system health...")
    health = agent.health_check()
    for component, status in health.items():
        if component == 'overall':
            continue
        icon = "✅" if status else "❌"
        print(f"{icon} {component.capitalize()}: {status}")
    
    if not health['overall']:
        print("\n❌ System is not healthy. Please check configuration.")
        sys.exit(1)
    
    print("\n✅ System is healthy!\n")
    
    # Check for example audio file
    example_file = Path("examples/sample_call.wav")
    
    if not example_file.exists():
        print(f"ℹ️  No example audio file found at {example_file}")
        print("To process a call, run:")
        print("  python cli.py process path/to/audio.wav --title 'My Call'")
        return
    
    # Process example file
    print(f"Processing example file: {example_file}\n")
    
    session_id = agent.process_call(
        audio_path=str(example_file),
        meta={
            'title': 'Example Call',
            'language': 'en',
        }
    )
    
    print(f"\n✅ Processing complete!")
    print(f"Session ID: {session_id}\n")
    
    # Get summary
    summary = agent.get_session_summary(session_id)
    
    # Display results
    print("=" * 60)
    print("CALL SUMMARY")
    print("=" * 60)
    
    session = summary['session']
    print(f"\nTitle: {session['title']}")
    print(f"Duration: {session['duration_seconds']:.1f} seconds")
    print(f"Language: {session['language']}")
    
    metadata = session.get('metadata', {})
    speaker_stats = metadata.get('speaker_stats', {})
    if speaker_stats:
        print(f"Speakers: {speaker_stats.get('num_speakers', '?')}")
    
    if session.get('summary'):
        print(f"\n{session['summary']}")
    
    # Action items
    action_items = summary['action_items']
    if action_items:
        print(f"\n📋 ACTION ITEMS ({len(action_items)}):")
        for item in action_items:
            owner = item.get('owner_speaker', 'unknown')
            text = item.get('item', '')
            due = item.get('due_date', 'No deadline')
            print(f"  • [{owner}] {text}")
            print(f"    Due: {due}")
    
    # Decisions
    decisions = summary['decisions']
    if decisions:
        print(f"\n✅ DECISIONS ({len(decisions)}):")
        for decision in decisions:
            print(f"  • {decision['decision']}")
    
    # MPC features
    mpc_features = summary.get('mpc_features', [])
    if mpc_features:
        print(f"\n🔒 MPC FEATURES:")
        for feature in mpc_features:
            kind = feature['feature_kind']
            result = feature.get('computation_result')
            if result and isinstance(result, dict):
                score = result.get('score')
                if score:
                    print(f"  • {kind}: {score:.4f}")
    
    print("\n" + "=" * 60)
    print("To view this session again, run:")
    print(f"  python cli.py show {session_id}")
    print("=" * 60 + "\n")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)
