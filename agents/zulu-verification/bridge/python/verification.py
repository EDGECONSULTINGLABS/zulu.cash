"""
Zulu Verification System - Python Bridge

Integrates TypeScript verification system with Python Zulu agent.
Uses subprocess to call Node.js verification CLI.
"""

import json
import subprocess
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path


@dataclass
class VerificationResult:
    """Verification result from TypeScript system"""
    success: bool
    artifact_id: str
    root: str
    verified_chunks: int
    total_chunks: int
    error: Optional[str] = None
    timestamp: Optional[str] = None


@dataclass
class SessionExportResult:
    """Session export result"""
    session_id: str
    receipt_hash: str
    root_hash: str
    chunk_count: int
    export_path: str


class VerificationBridge:
    """Bridge between Python and TypeScript verification system"""
    
    def __init__(self, node_path: str = "node", verification_cli: str = None):
        """
        Initialize verification bridge
        
        Args:
            node_path: Path to node executable
            verification_cli: Path to verification CLI script
        """
        self.node_path = node_path
        
        if verification_cli is None:
            # Default to verification CLI in same directory structure
            bridge_dir = Path(__file__).parent.parent.parent
            verification_cli = str(bridge_dir / "dist" / "cli.js")
        
        self.verification_cli = verification_cli
        
        # Check if verification CLI exists
        if not os.path.exists(self.verification_cli):
            raise FileNotFoundError(
                f"Verification CLI not found: {self.verification_cli}\n"
                "Run: npm run build"
            )
    
    def _run_command(self, args: List[str]) -> Dict[str, Any]:
        """Run verification CLI command"""
        cmd = [self.node_path, self.verification_cli] + args
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            
            # Parse JSON output
            return json.loads(result.stdout)
            
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Verification command failed: {e.stderr}")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse verification output: {e}")
    
    def verify_artifact(
        self,
        artifact_path: str,
        manifest_path: str,
        output_path: Optional[str] = None
    ) -> VerificationResult:
        """
        Verify artifact with manifest
        
        Args:
            artifact_path: Path to artifact file
            manifest_path: Path to manifest JSON
            output_path: Optional output path for verified file
        
        Returns:
            VerificationResult with verification status
        """
        args = ["verify", artifact_path, manifest_path]
        if output_path:
            args.extend(["--output", output_path])
        
        result = self._run_command(args)
        
        return VerificationResult(
            success=result["success"],
            artifact_id=result["artifactId"],
            root=result["root"],
            verified_chunks=result["verifiedChunks"],
            total_chunks=result["totalChunks"],
            error=result.get("error"),
            timestamp=result.get("timestamp")
        )
    
    def export_session(
        self,
        session_id: str,
        transcript_path: str,
        summary: str,
        entities: List[Dict],
        embeddings_path: str,
        output_path: str,
        private_key: str
    ) -> SessionExportResult:
        """
        Export session with verified commitment
        
        Args:
            session_id: Session identifier
            transcript_path: Path to transcript JSON
            summary: Session summary text
            entities: Extracted entities
            embeddings_path: Path to embeddings file
            output_path: Output path for export bundle
            private_key: Private key hex for signing
        
        Returns:
            SessionExportResult with export details
        """
        args = [
            "export-session",
            session_id,
            transcript_path,
            summary,
            json.dumps(entities),
            embeddings_path,
            output_path,
            "--key", private_key
        ]
        
        result = self._run_command(args)
        
        return SessionExportResult(
            session_id=result["sessionId"],
            receipt_hash=result["receiptHash"],
            root_hash=result["rootHash"],
            chunk_count=result["chunkCount"],
            export_path=result["exportPath"]
        )
    
    def import_session(self, bundle_path: str) -> Dict[str, Any]:
        """
        Import and verify session bundle
        
        Args:
            bundle_path: Path to session export bundle
        
        Returns:
            Imported session data
        """
        args = ["import-session", bundle_path]
        result = self._run_command(args)
        
        if not result["success"]:
            raise RuntimeError(f"Session import failed: {result.get('error')}")
        
        return result["session"]
    
    def generate_seed_phrase(self, word_count: int = 12) -> str:
        """
        Generate BIP-39 seed phrase
        
        Args:
            word_count: Number of words (12, 15, 18, 21, or 24)
        
        Returns:
            Mnemonic seed phrase
        """
        args = ["generate-seed", "--words", str(word_count)]
        result = self._run_command(args)
        return result["mnemonic"]
    
    def get_expiring_keys(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        Get keys expiring within specified days
        
        Args:
            days: Number of days to check
        
        Returns:
            List of expiring keys with metadata
        """
        args = ["expiring-keys", "--days", str(days)]
        result = self._run_command(args)
        return result["keys"]
    
    def approve_key(self, pubkey_hex: str) -> None:
        """
        Approve a public key for WARN trust policy
        
        Args:
            pubkey_hex: Public key in hex format
        """
        args = ["approve-key", pubkey_hex]
        self._run_command(args)
    
    def revoke_key(self, pubkey_hex: str, reason: str) -> None:
        """
        Revoke a public key
        
        Args:
            pubkey_hex: Public key in hex format
            reason: Revocation reason
        """
        args = ["revoke-key", pubkey_hex, "--reason", reason]
        self._run_command(args)


# Example usage for Zulu agent integration
def integrate_with_zulu_agent():
    """Example integration with Zulu MPC agent"""
    
    # Initialize bridge
    bridge = VerificationBridge()
    
    # 1. Generate seed phrase (first-time setup)
    seed_phrase = bridge.generate_seed_phrase(12)
    print(f"Generated seed: {seed_phrase}")
    print("⚠️  Store this securely!")
    
    # 2. Verify Whisper model before loading
    try:
        result = bridge.verify_artifact(
            artifact_path="models/whisper-tiny-en.gguf",
            manifest_path="models/whisper-tiny-en.manifest.json"
        )
        
        if result.success:
            print(f"✅ Model verified: {result.artifact_id}")
            # Safe to load model in Zulu agent
        else:
            print(f"❌ Model verification failed: {result.error}")
            # Do not load untrusted model
            
    except Exception as e:
        print(f"Verification error: {e}")
    
    # 3. Export session after processing
    session_export = bridge.export_session(
        session_id="session-123",
        transcript_path="data/transcript.json",
        summary="Meeting summary...",
        entities=[{"type": "person", "name": "Alice"}],
        embeddings_path="data/embeddings.bin",
        output_path="exports/session-123.bundle.json",
        private_key="deadbeef..."  # From secure keychain
    )
    
    print(f"✅ Session exported: {session_export.export_path}")
    print(f"   Receipt: {session_export.receipt_hash}")


if __name__ == "__main__":
    integrate_with_zulu_agent()
