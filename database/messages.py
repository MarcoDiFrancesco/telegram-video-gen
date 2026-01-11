"""Track individual messages with details."""
import sqlite3
import os
from datetime import datetime
from typing import Optional, List, Dict
from config.settings import DEFAULT_MODEL, DEFAULT_DURATION, DEFAULT_RESOLUTION

# Use on-disk SQLite database
db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database.db")
conn = sqlite3.connect(db_path, check_same_thread=False)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Create messages table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        username TEXT,
        timestamp TEXT NOT NULL,
        prompt_tokens INTEGER DEFAULT 0,
        output_prompt_tokens INTEGER DEFAULT 0,
        model TEXT NOT NULL,
        cost REAL DEFAULT 0.0,
        duration_seconds INTEGER NOT NULL,
        resolution TEXT NOT NULL,
        status TEXT NOT NULL
    )
""")
conn.commit()


def create_message(
    user_id: int,
    username: Optional[str],
    model: str,
    duration_seconds: int,
    resolution: str,
    prompt_tokens: int = 0,
    output_prompt_tokens: int = 0,
    cost: float = 0.0,
    status: str = "pending"
) -> int:
    """Create a new message record and return its ID."""
    timestamp = datetime.utcnow().isoformat()
    cursor.execute("""
        INSERT INTO messages (
            user_id, username, timestamp, prompt_tokens, output_prompt_tokens,
            model, cost, duration_seconds, resolution, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id, username, timestamp, prompt_tokens, output_prompt_tokens,
        model, cost, duration_seconds, resolution, status
    ))
    conn.commit()
    return cursor.lastrowid


def update_message(
    message_id: int,
    prompt_tokens: Optional[int] = None,
    output_prompt_tokens: Optional[int] = None,
    cost: Optional[float] = None,
    status: Optional[str] = None
):
    """Update message record."""
    updates = []
    values = []
    
    if prompt_tokens is not None:
        updates.append("prompt_tokens = ?")
        values.append(prompt_tokens)
    if output_prompt_tokens is not None:
        updates.append("output_prompt_tokens = ?")
        values.append(output_prompt_tokens)
    if cost is not None:
        updates.append("cost = ?")
        values.append(cost)
    if status is not None:
        updates.append("status = ?")
        values.append(status)
    
    if updates:
        values.append(message_id)
        cursor.execute(
            f"UPDATE messages SET {', '.join(updates)} WHERE id = ?",
            values
        )
        conn.commit()


def get_stats() -> Dict[str, any]:
    """Get aggregated statistics across all users."""
    cursor.execute("""
        SELECT 
            COUNT(*) as total_messages,
            COUNT(DISTINCT user_id) as unique_users,
            SUM(cost) as total_cost,
            SUM(prompt_tokens) as total_prompt_tokens,
            SUM(output_prompt_tokens) as total_output_prompt_tokens,
            SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful_messages,
            SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_messages
        FROM messages
    """)
    row = cursor.fetchone()
    
    return {
        "total_messages": row["total_messages"] or 0,
        "unique_users": row["unique_users"] or 0,
        "total_cost": row["total_cost"] or 0.0,
        "total_prompt_tokens": row["total_prompt_tokens"] or 0,
        "total_output_prompt_tokens": row["total_output_prompt_tokens"] or 0,
        "successful_messages": row["successful_messages"] or 0,
        "failed_messages": row["failed_messages"] or 0
    }


def get_successful_videos_count() -> int:
    """Get total count of successfully generated videos across all users."""
    cursor.execute("""
        SELECT COUNT(*) as count FROM messages WHERE status = 'success'
    """)
    row = cursor.fetchone()
    return row["count"] or 0


def get_total_cost() -> float:
    """Get total cost of all successfully generated videos across all users."""
    cursor.execute("""
        SELECT SUM(cost) as total FROM messages WHERE status = 'success'
    """)
    row = cursor.fetchone()
    return row["total"] or 0.0

