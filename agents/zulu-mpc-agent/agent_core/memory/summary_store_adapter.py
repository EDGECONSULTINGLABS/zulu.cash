"""
Adapter to make SessionStore compatible with SummaryStore protocol.
"""

from typing import List, Dict, Any, Optional
import json
from agent_core.memory.session_store import SessionStore


class SummaryStoreAdapter:
    """
    Wraps SessionStore to implement SummaryStore protocol.
    """
    
    def __init__(self, session_store: SessionStore):
        self.store = session_store
        self._ensure_schema()
    
    def _ensure_schema(self):
        """Ensure chunk_summaries and final_summaries tables exist."""
        conn = self.store._get_connection()
        try:
            # Check if tables exist
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='chunk_summaries'"
            )
            if not cursor.fetchone():
                # Run migration
                self._create_tables(conn)
        finally:
            conn.close()
    
    def _create_tables(self, conn):
        """Create summarizer v2 tables."""
        conn.execute('''
            CREATE TABLE IF NOT EXISTS chunk_summaries (
                chunk_id TEXT PRIMARY KEY,
                conversation_id TEXT NOT NULL,
                content TEXT NOT NULL,
                speaker_label TEXT,
                start_time REAL,
                end_time REAL,
                model TEXT,
                created_at TEXT NOT NULL,
                metadata_json TEXT
            )
        ''')
        
        conn.execute('''
            CREATE INDEX IF NOT EXISTS idx_chunk_summaries_conversation 
            ON chunk_summaries(conversation_id)
        ''')
        
        conn.execute('''
            CREATE TABLE IF NOT EXISTS final_summaries (
                conversation_id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                chunk_count INTEGER,
                model TEXT,
                created_at TEXT NOT NULL,
                metadata_json TEXT
            )
        ''')
        
        conn.commit()
        print("[OK] Summarizer v2 tables created")
    
    # ========== SummaryStore Protocol Implementation ==========
    
    def put_chunk_summary(
        self,
        conversation_id: str,
        chunk_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Store a chunk summary."""
        conn = self.store._get_connection()
        try:
            metadata_json = json.dumps(metadata) if metadata else None
            
            conn.execute(
                '''
                INSERT INTO chunk_summaries 
                (chunk_id, conversation_id, content, speaker_label, start_time, end_time, model, created_at, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    chunk_id,
                    conversation_id,
                    content,
                    metadata.get('speaker_label') if metadata else None,
                    metadata.get('start_time') if metadata else None,
                    metadata.get('end_time') if metadata else None,
                    metadata.get('model') if metadata else None,
                    metadata.get('created_at') if metadata else None,
                    metadata_json,
                )
            )
            conn.commit()
        finally:
            conn.close()
    
    def get_chunk_summaries(self, conversation_id: str) -> List[Dict[str, Any]]:
        """Get all chunk summaries for a conversation."""
        conn = self.store._get_connection()
        try:
            cursor = conn.execute(
                '''
                SELECT chunk_id, content, speaker_label, start_time, end_time, model, created_at, metadata_json
                FROM chunk_summaries
                WHERE conversation_id = ?
                ORDER BY created_at
                ''',
                (conversation_id,)
            )
            
            summaries = []
            for row in cursor.fetchall():
                summary = {
                    'chunk_id': row[0],
                    'content': row[1],
                    'speaker_label': row[2],
                    'start_time': row[3],
                    'end_time': row[4],
                    'model': row[5],
                    'created_at': row[6],
                }
                if row[7]:  # metadata_json
                    summary['metadata'] = json.loads(row[7])
                summaries.append(summary)
            
            return summaries
        finally:
            conn.close()
    
    def clear_conversation(self, conversation_id: str) -> None:
        """Clear all chunk summaries for a conversation."""
        conn = self.store._get_connection()
        try:
            conn.execute(
                'DELETE FROM chunk_summaries WHERE conversation_id = ?',
                (conversation_id,)
            )
            conn.commit()
        finally:
            conn.close()
    
    def put_final_summary(
        self,
        conversation_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Store final summary."""
        conn = self.store._get_connection()
        try:
            metadata_json = json.dumps(metadata) if metadata else None
            
            conn.execute(
                '''
                INSERT OR REPLACE INTO final_summaries 
                (conversation_id, content, chunk_count, model, created_at, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?)
                ''',
                (
                    conversation_id,
                    content,
                    metadata.get('chunk_count') if metadata else None,
                    metadata.get('model') if metadata else None,
                    metadata.get('created_at') if metadata else None,
                    metadata_json,
                )
            )
            conn.commit()
        finally:
            conn.close()
    
    def get_final_summary(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """Get final summary for a conversation."""
        conn = self.store._get_connection()
        try:
            cursor = conn.execute(
                '''
                SELECT content, chunk_count, model, created_at, metadata_json
                FROM final_summaries
                WHERE conversation_id = ?
                ''',
                (conversation_id,)
            )
            
            row = cursor.fetchone()
            if not row:
                return None
            
            summary = {
                'conversation_id': conversation_id,
                'content': row[0],
                'chunk_count': row[1],
                'model': row[2],
                'created_at': row[3],
            }
            if row[4]:  # metadata_json
                summary['metadata'] = json.loads(row[4])
            
            return summary
        finally:
            conn.close()
