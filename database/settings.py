"""On-disk settings storage using SQLite."""
import sqlite3
import os
from typing import Optional, Dict
from config.settings import DEFAULT_MODEL, DEFAULT_DURATION, DEFAULT_RESOLUTION

# Use on-disk SQLite database
db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "database.db")
conn = sqlite3.connect(db_path, check_same_thread=False)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Create settings table
cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_settings (
        user_id INTEGER PRIMARY KEY,
        model TEXT NOT NULL,
        duration INTEGER NOT NULL,
        resolution TEXT NOT NULL
    )
""")
conn.commit()


def get_user_settings(user_id: int) -> Dict[str, any]:
    """Get user settings or return defaults."""
    cursor.execute("SELECT * FROM user_settings WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    
    if row:
        return {
            "user_id": row["user_id"],
            "model": row["model"],
            "duration": row["duration"],
            "resolution": row["resolution"]
        }
    
    # Return defaults if no settings found
    return {
        "user_id": user_id,
        "model": DEFAULT_MODEL,
        "duration": DEFAULT_DURATION,
        "resolution": DEFAULT_RESOLUTION
    }


def set_user_settings(user_id: int, model: Optional[str] = None, 
                     duration: Optional[int] = None, 
                     resolution: Optional[str] = None) -> Dict[str, any]:
    """Update user settings."""
    current = get_user_settings(user_id)
    
    if model is not None:
        current["model"] = model
    if duration is not None:
        current["duration"] = duration
    if resolution is not None:
        current["resolution"] = resolution
    
    cursor.execute("""
        INSERT OR REPLACE INTO user_settings (user_id, model, duration, resolution)
        VALUES (?, ?, ?, ?)
    """, (user_id, current["model"], current["duration"], current["resolution"]))
    conn.commit()
    
    return current


def reset_user_settings(user_id: int) -> Dict[str, any]:
    """Reset user settings to defaults."""
    cursor.execute("DELETE FROM user_settings WHERE user_id = ?", (user_id,))
    conn.commit()
    return get_user_settings(user_id)

