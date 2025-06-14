"""Database Service for managing conversation history and analytics"""

import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import logging

from models.request import (
    Conversation, Message, ConversationResponse, 
    MessageResponse, SearchRequest, ConversationAnalytics
)

logger = logging.getLogger(__name__)

class DatabaseService:
    """Service for managing SQLite database operations"""
    
    def __init__(self, db_path: str = "shopping_agent.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize database tables"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT,
                    session_id TEXT NOT NULL,
                    title TEXT,
                    status TEXT DEFAULT 'active',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER NOT NULL,
                    message_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    execution_time REAL,
                    tokens_used INTEGER,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (conversation_id) REFERENCES conversations (id)
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversation_analytics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id INTEGER NOT NULL,
                    total_messages INTEGER DEFAULT 0,
                    avg_response_time REAL DEFAULT 0.0,
                    total_tokens_used INTEGER DEFAULT 0,
                    success_rate REAL DEFAULT 1.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (conversation_id) REFERENCES conversations (id)
                )
            """)
            
            # Create indexes for better performance
            conn.execute("CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_conversations_session_id ON conversations(session_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at)")
            
            conn.commit()
    
    def get_conversations(self, user_id: Optional[str] = None, 
                         limit: int = 50, offset: int = 0) -> List[Conversation]:
        """Get paginated conversations"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            if user_id:
                cursor = conn.execute("""
                    SELECT * FROM conversations 
                    WHERE user_id = ? 
                    ORDER BY updated_at DESC 
                    LIMIT ? OFFSET ?
                """, (user_id, limit, offset))
            else:
                cursor = conn.execute("""
                    SELECT * FROM conversations 
                    ORDER BY updated_at DESC 
                    LIMIT ? OFFSET ?
                """, (limit, offset))
            
            conversations = []
            for row in cursor.fetchall():
                conversations.append(Conversation(
                    id=row['id'],
                    user_id=row['user_id'],
                    session_id=row['session_id'],
                    title=row['title'],
                    status=row['status'],
                    created_at=datetime.fromisoformat(row['created_at']),
                    updated_at=datetime.fromisoformat(row['updated_at'])
                ))
            
            return conversations
    
    def get_conversation_detail(self, conversation_id: int) -> Optional[ConversationResponse]:
        """Get detailed conversation with messages"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Get conversation
            cursor = conn.execute(
                "SELECT * FROM conversations WHERE id = ?", 
                (conversation_id,)
            )
            conv_row = cursor.fetchone()
            
            if not conv_row:
                return None
            
            conversation = Conversation(
                id=conv_row['id'],
                user_id=conv_row['user_id'],
                session_id=conv_row['session_id'],
                title=conv_row['title'],
                status=conv_row['status'],
                created_at=datetime.fromisoformat(conv_row['created_at']),
                updated_at=datetime.fromisoformat(conv_row['updated_at'])
            )
            
            # Get messages
            cursor = conn.execute("""
                SELECT * FROM messages 
                WHERE conversation_id = ? 
                ORDER BY created_at ASC
            """, (conversation_id,))
            
            messages = []
            for row in cursor.fetchall():
                metadata = json.loads(row['metadata']) if row['metadata'] else None
                messages.append(Message(
                    id=row['id'],
                    conversation_id=row['conversation_id'],
                    message_type=row['message_type'],
                    content=row['content'],
                    metadata=metadata,
                    execution_time=row['execution_time'],
                    tokens_used=row['tokens_used'],
                    created_at=datetime.fromisoformat(row['created_at'])
                ))
            
            return ConversationResponse(
                conversation=conversation,
                messages=messages
            )
    
    def search_conversations(self, search_request: SearchRequest, 
                           user_id: Optional[str] = None) -> List[ConversationResponse]:
        """Search conversations by keyword"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Build search query
            base_query = """
                SELECT DISTINCT c.* FROM conversations c
                JOIN messages m ON c.id = m.conversation_id
                WHERE (c.title LIKE ? OR m.content LIKE ?)
            """
            
            params = [f"%{search_request.keyword}%", f"%{search_request.keyword}%"]
            
            if user_id:
                base_query += " AND c.user_id = ?"
                params.append(user_id)
            
            # Apply filters
            if search_request.filters:
                if 'date_from' in search_request.filters:
                    base_query += " AND c.created_at >= ?"
                    params.append(search_request.filters['date_from'])
                
                if 'date_to' in search_request.filters:
                    base_query += " AND c.created_at <= ?"
                    params.append(search_request.filters['date_to'])
            
            base_query += " ORDER BY c.updated_at DESC LIMIT ? OFFSET ?"
            params.extend([str(search_request.limit), str(search_request.offset)])
            
            cursor = conn.execute(base_query, params)
            
            results = []
            for row in cursor.fetchall():
                detail = self.get_conversation_detail(row['id'])
                if detail:
                    results.append(detail)
            
            return results
    
    def create_conversation(self, user_id: Optional[str], session_id: str, 
                          title: Optional[str] = None) -> int:
        """Create a new conversation"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO conversations (user_id, session_id, title)
                VALUES (?, ?, ?)
            """, (user_id, session_id, title))
            
            conversation_id = cursor.lastrowid
            conn.commit()
            
            return conversation_id or 0
    
    def add_message(self, conversation_id: int, message_type: str, content: str,
                   metadata: Optional[Dict[str, Any]] = None,
                   execution_time: Optional[float] = None,
                   tokens_used: Optional[int] = None) -> int:
        """Add a message to conversation"""
        with sqlite3.connect(self.db_path) as conn:
            metadata_json = json.dumps(metadata) if metadata else None
            
            cursor = conn.execute("""
                INSERT INTO messages 
                (conversation_id, message_type, content, metadata, execution_time, tokens_used)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (conversation_id, message_type, content, metadata_json, execution_time, tokens_used))
            
            message_id = cursor.lastrowid
            
            # Update conversation timestamp
            conn.execute("""
                UPDATE conversations 
                SET updated_at = CURRENT_TIMESTAMP 
                WHERE id = ?
            """, (conversation_id,))
            
            conn.commit()
            
            return message_id or 0
    
    def get_conversations_count(self, user_id: Optional[str] = None) -> int:
        """Get total count of conversations"""
        with sqlite3.connect(self.db_path) as conn:
            if user_id:
                cursor = conn.execute(
                    "SELECT COUNT(*) FROM conversations WHERE user_id = ?",
                    (user_id,)
                )
            else:
                cursor = conn.execute("SELECT COUNT(*) FROM conversations")
            
            result = cursor.fetchone()
            return result[0] if result else 0
    
    def get_conversation_by_id(self, conversation_id: int, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get conversation by ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            if user_id:
                cursor = conn.execute(
                    "SELECT * FROM conversations WHERE id = ? AND user_id = ?",
                    (conversation_id, user_id)
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM conversations WHERE id = ?",
                    (conversation_id,)
                )
            
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
    
    def get_conversation_history(self, conversation_id: int, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get conversation history with messages"""
        conversation = self.get_conversation_by_id(conversation_id, user_id)
        if not conversation:
            return []
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
                (conversation_id,)
            )
            
            messages = [dict(row) for row in cursor.fetchall()]
            
        return [{
            'conversation': conversation,
            'messages': messages
        }]
    
    def get_analytics(self, conversation_id: Optional[int] = None, days: int = 30) -> Dict[str, Any]:
        """Get analytics data"""
        with sqlite3.connect(self.db_path) as conn:
            # Basic analytics
            analytics = {
                'total_conversations': 0,
                'total_messages': 0,
                'avg_messages_per_conversation': 0,
                'total_tokens_used': 0,
                'avg_execution_time': 0
            }
            
            # Get conversation count
            if conversation_id:
                cursor = conn.execute("SELECT COUNT(*) FROM conversations WHERE id = ?", (conversation_id,))
            else:
                cursor = conn.execute("SELECT COUNT(*) FROM conversations WHERE created_at >= datetime('now', '-{} days')".format(days))
            
            result = cursor.fetchone()
            analytics['total_conversations'] = result[0] if result else 0
            
            # Get message count and stats
            if conversation_id:
                cursor = conn.execute(
                    "SELECT COUNT(*), AVG(tokens_used), AVG(execution_time) FROM messages WHERE conversation_id = ?",
                    (conversation_id,)
                )
            else:
                cursor = conn.execute(
                    "SELECT COUNT(*), AVG(tokens_used), AVG(execution_time) FROM messages WHERE created_at >= datetime('now', '-{} days')".format(days)
                )
            
            result = cursor.fetchone()
            if result:
                analytics['total_messages'] = result[0] or 0
                analytics['total_tokens_used'] = result[1] or 0
                analytics['avg_execution_time'] = result[2] or 0
            
            if analytics['total_conversations'] > 0:
                analytics['avg_messages_per_conversation'] = analytics['total_messages'] / analytics['total_conversations']
            
            return analytics
    
    def update_conversation_status(self, conversation_id: int, status: str, user_id: Optional[str] = None) -> bool:
        """Update conversation status"""
        with sqlite3.connect(self.db_path) as conn:
            if user_id:
                cursor = conn.execute(
                    "UPDATE conversations SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ? AND user_id = ?",
                    (status, conversation_id, user_id)
                )
            else:
                cursor = conn.execute(
                    "UPDATE conversations SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (status, conversation_id)
                )
            
            conn.commit()
            return cursor.rowcount > 0

    def delete_conversation(self, conversation_id: int, user_id: Optional[str] = None) -> bool:
        """Delete a conversation and its messages"""
        with sqlite3.connect(self.db_path) as conn:
            # Check if conversation exists and belongs to user
            if user_id:
                cursor = conn.execute(
                    "SELECT id FROM conversations WHERE id = ? AND user_id = ?",
                    (conversation_id, user_id)
                )
            else:
                cursor = conn.execute(
                    "SELECT id FROM conversations WHERE id = ?",
                    (conversation_id,)
                )
            
            if not cursor.fetchone():
                return False
            
            # Delete messages first (foreign key constraint)
            conn.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
            
            # Delete analytics
            conn.execute("DELETE FROM conversation_analytics WHERE conversation_id = ?", (conversation_id,))
            
            # Delete conversation
            conn.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
            
            conn.commit()
            return True
    
    def archive_conversation(self, conversation_id: int, user_id: Optional[str] = None) -> bool:
        """Archive a conversation"""
        with sqlite3.connect(self.db_path) as conn:
            if user_id:
                cursor = conn.execute("""
                    UPDATE conversations 
                    SET status = 'archived', updated_at = CURRENT_TIMESTAMP 
                    WHERE id = ? AND user_id = ?
                """, (conversation_id, user_id))
            else:
                cursor = conn.execute("""
                    UPDATE conversations 
                    SET status = 'archived', updated_at = CURRENT_TIMESTAMP 
                    WHERE id = ?
                """, (conversation_id,))
            
            conn.commit()
            return cursor.rowcount > 0
    
    def get_usage_analytics(self, user_id: Optional[str] = None, 
                          days: int = 30) -> Dict[str, Any]:
        """Get usage analytics"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # Base conditions
            date_condition = "WHERE c.created_at >= datetime('now', '-{} days')".format(days)
            user_condition = ""
            params = []
            
            if user_id:
                user_condition = " AND c.user_id = ?"
                params.append(user_id)
            
            # Total conversations
            cursor = conn.execute(f"""
                SELECT COUNT(*) as total FROM conversations c
                {date_condition}{user_condition}
            """, params)
            total_conversations = cursor.fetchone()['total']
            
            # Total messages
            cursor = conn.execute(f"""
                SELECT COUNT(*) as total FROM messages m
                JOIN conversations c ON m.conversation_id = c.id
                {date_condition}{user_condition}
            """, params)
            total_messages = cursor.fetchone()['total']
            
            # Average response time
            cursor = conn.execute(f"""
                SELECT AVG(execution_time) as avg_time FROM messages m
                JOIN conversations c ON m.conversation_id = c.id
                {date_condition}{user_condition}
                AND m.execution_time IS NOT NULL
            """, params)
            avg_response_time = cursor.fetchone()['avg_time'] or 0.0
            
            # Total tokens used
            cursor = conn.execute(f"""
                SELECT SUM(tokens_used) as total FROM messages m
                JOIN conversations c ON m.conversation_id = c.id
                {date_condition}{user_condition}
                AND m.tokens_used IS NOT NULL
            """, params)
            total_tokens = cursor.fetchone()['total'] or 0
            
            return {
                "total_conversations": total_conversations,
                "total_messages": total_messages,
                "avg_response_time": avg_response_time,
                "total_tokens_used": total_tokens,
                "period_days": days
            }

# Global instance
database_service = DatabaseService()