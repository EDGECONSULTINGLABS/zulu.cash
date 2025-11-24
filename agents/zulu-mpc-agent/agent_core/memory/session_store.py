"""SQLCipher-encrypted session storage for ZULU MPC Agent."""

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from agent_core.utils import LoggerMixin


class SessionStore(LoggerMixin):
    """
    Encrypted local storage for call sessions, utterances, and MPC features.
    Uses SQLCipher for encryption at rest.
    """
    
    def __init__(self, db_path: str, encryption_key: Optional[str] = None):
        """
        Initialize session store.
        
        Args:
            db_path: Path to SQLCipher database file.
            encryption_key: Encryption key (hex string). If None, reads from env.
        """
        self.db_path = db_path
        self.encryption_key = encryption_key or os.getenv("ZULU_DB_KEY")
        
        if not self.encryption_key:
            raise ValueError(
                "Database encryption key not provided. "
                "Set ZULU_DB_KEY environment variable or pass encryption_key parameter."
            )
        
        # Create database directory if needed
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_db()
        
        self.logger.info(f"SessionStore initialized at {db_path}")
    
    def _get_connection(self) -> sqlite3.Connection:
        """Create a new database connection with encryption."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        
        # Enable SQLCipher encryption
        conn.execute(f"PRAGMA key = 'x\"{self.encryption_key}\"'")
        conn.execute("PRAGMA cipher_page_size = 4096")
        conn.execute("PRAGMA kdf_iter = 256000")
        conn.execute("PRAGMA cipher_hmac_algorithm = HMAC_SHA512")
        conn.execute("PRAGMA cipher_kdf_algorithm = PBKDF2_HMAC_SHA512")
        
        return conn
    
    def _init_db(self) -> None:
        """Initialize database schema."""
        schema_file = Path(__file__).parent.parent.parent / "data" / "schemas" / "001_core.sql"
        
        if not schema_file.exists():
            raise FileNotFoundError(f"Schema file not found: {schema_file}")
        
        with open(schema_file, 'r') as f:
            schema_sql = f.read()
        
        conn = self._get_connection()
        try:
            conn.executescript(schema_sql)
            conn.commit()
            self.logger.debug("Database schema initialized")
        finally:
            conn.close()
    
    # ========== Session Operations ==========
    
    def insert_session(
        self,
        session_id: str,
        started_at: str,
        title: str,
        ended_at: Optional[str] = None,
        summary: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        audio_path: Optional[str] = None,
        duration_seconds: Optional[float] = None,
        language: str = "en",
    ) -> None:
        """Insert a new session."""
        conn = self._get_connection()
        try:
            metadata_json = json.dumps(metadata) if metadata else None
            
            conn.execute(
                """
                INSERT INTO sessions 
                (id, started_at, ended_at, title, summary, metadata_json, 
                 audio_path, duration_seconds, language)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (session_id, started_at, ended_at, title, summary, metadata_json,
                 audio_path, duration_seconds, language),
            )
            conn.commit()
            self.logger.info(f"Session {session_id} inserted: {title}")
        finally:
            conn.close()
    
    def update_session(
        self,
        session_id: str,
        ended_at: Optional[str] = None,
        summary: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Update an existing session."""
        conn = self._get_connection()
        try:
            updates = []
            params = []
            
            if ended_at is not None:
                updates.append("ended_at = ?")
                params.append(ended_at)
            
            if summary is not None:
                updates.append("summary = ?")
                params.append(summary)
            
            if metadata is not None:
                updates.append("metadata_json = ?")
                params.append(json.dumps(metadata))
            
            if not updates:
                return
            
            params.append(session_id)
            sql = f"UPDATE sessions SET {', '.join(updates)} WHERE id = ?"
            
            conn.execute(sql, params)
            conn.commit()
            self.logger.debug(f"Session {session_id} updated")
        finally:
            conn.close()
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a session by ID."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM sessions WHERE id = ?",
                (session_id,)
            )
            row = cursor.fetchone()
            
            if row:
                result = dict(row)
                if result.get('metadata_json'):
                    result['metadata'] = json.loads(result['metadata_json'])
                return result
            return None
        finally:
            conn.close()
    
    def list_sessions(
        self,
        limit: int = 50,
        offset: int = 0,
        order_by: str = "created_at DESC",
    ) -> List[Dict[str, Any]]:
        """List sessions with pagination."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                f"SELECT * FROM sessions ORDER BY {order_by} LIMIT ? OFFSET ?",
                (limit, offset)
            )
            sessions = []
            for row in cursor.fetchall():
                session = dict(row)
                if session.get('metadata_json'):
                    session['metadata'] = json.loads(session['metadata_json'])
                sessions.append(session)
            return sessions
        finally:
            conn.close()
    
    def update_session_score(self, session_id: str, score: float) -> None:
        """Update attention score in session metadata."""
        conn = self._get_connection()
        try:
            conn.execute(
                """
                UPDATE sessions 
                SET metadata_json = json_set(
                    COALESCE(metadata_json, '{}'), 
                    '$.attention_score', 
                    ?
                )
                WHERE id = ?
                """,
                (score, session_id),
            )
            conn.commit()
        finally:
            conn.close()
    
    # ========== Utterance Operations ==========
    
    def insert_utterance(
        self,
        session_id: str,
        speaker_label: str,
        start_time: float,
        end_time: float,
        text: str,
        confidence: Optional[float] = None,
    ) -> int:
        """Insert a new utterance."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                INSERT INTO utterances 
                (session_id, speaker_label, start_time, end_time, text, confidence)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (session_id, speaker_label, start_time, end_time, text, confidence),
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()
    
    def get_utterances(
        self,
        session_id: str,
        speaker_label: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get all utterances for a session."""
        conn = self._get_connection()
        try:
            if speaker_label:
                cursor = conn.execute(
                    """
                    SELECT * FROM utterances 
                    WHERE session_id = ? AND speaker_label = ?
                    ORDER BY start_time
                    """,
                    (session_id, speaker_label),
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT * FROM utterances 
                    WHERE session_id = ?
                    ORDER BY start_time
                    """,
                    (session_id,),
                )
            
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    # ========== MPC Feature Operations ==========
    
    def insert_mpc_feature(
        self,
        session_id: str,
        feature_kind: str,
        feature_hash: str,
        nillion_handle: str,
        feature_dim: Optional[int] = None,
        computation_result: Optional[Dict[str, Any]] = None,
    ) -> int:
        """Insert MPC feature mapping."""
        conn = self._get_connection()
        try:
            result_json = json.dumps(computation_result) if computation_result else None
            
            cursor = conn.execute(
                """
                INSERT INTO mpc_feature_index
                (session_id, feature_kind, feature_hash, nillion_handle, 
                 feature_dim, computation_result)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (session_id, feature_kind, feature_hash, nillion_handle,
                 feature_dim, result_json),
            )
            conn.commit()
            self.logger.debug(
                f"MPC feature inserted: {feature_kind} for session {session_id}"
            )
            return cursor.lastrowid
        finally:
            conn.close()
    
    def get_mpc_features(
        self,
        session_id: Optional[str] = None,
        feature_kind: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get MPC features."""
        conn = self._get_connection()
        try:
            conditions = []
            params = []
            
            if session_id:
                conditions.append("session_id = ?")
                params.append(session_id)
            
            if feature_kind:
                conditions.append("feature_kind = ?")
                params.append(feature_kind)
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            cursor = conn.execute(
                f"SELECT * FROM mpc_feature_index WHERE {where_clause}",
                params,
            )
            
            features = []
            for row in cursor.fetchall():
                feature = dict(row)
                if feature.get('computation_result'):
                    feature['computation_result'] = json.loads(feature['computation_result'])
                features.append(feature)
            
            return features
        finally:
            conn.close()
    
    # ========== Action Item Operations ==========
    
    def insert_action_item(
        self,
        session_id: str,
        owner_speaker: str,
        item: str,
        due_date: Optional[str] = None,
        status: str = "pending",
    ) -> int:
        """Insert an action item."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                INSERT INTO action_items
                (session_id, owner_speaker, item, due_date, status)
                VALUES (?, ?, ?, ?, ?)
                """,
                (session_id, owner_speaker, item, due_date, status),
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()
    
    def get_action_items(
        self,
        session_id: Optional[str] = None,
        status: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get action items."""
        conn = self._get_connection()
        try:
            conditions = []
            params = []
            
            if session_id:
                conditions.append("session_id = ?")
                params.append(session_id)
            
            if status:
                conditions.append("status = ?")
                params.append(status)
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            cursor = conn.execute(
                f"SELECT * FROM action_items WHERE {where_clause} ORDER BY created_at DESC",
                params,
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    # ========== Decision Operations ==========
    
    def insert_decision(
        self,
        session_id: str,
        decision: str,
        context: Optional[str] = None,
        timestamp_in_call: Optional[float] = None,
    ) -> int:
        """Insert a decision."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                """
                INSERT INTO decisions
                (session_id, decision, context, timestamp_in_call)
                VALUES (?, ?, ?, ?)
                """,
                (session_id, decision, context, timestamp_in_call),
            )
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()
    
    def get_decisions(self, session_id: str) -> List[Dict[str, Any]]:
        """Get decisions for a session."""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM decisions WHERE session_id = ? ORDER BY created_at",
                (session_id,),
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    # ========== Utility Operations ==========
    
    def delete_session(self, session_id: str) -> None:
        """Delete a session and all related data."""
        conn = self._get_connection()
        try:
            conn.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            conn.commit()
            self.logger.info(f"Session {session_id} deleted (cascade)")
        finally:
            conn.close()
    
    def vacuum(self) -> None:
        """Vacuum the database to reclaim space."""
        conn = self._get_connection()
        try:
            conn.execute("VACUUM")
            self.logger.info("Database vacuumed")
        finally:
            conn.close()
