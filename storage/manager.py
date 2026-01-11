"""Temporary file handling."""
import os
import tempfile
from pathlib import Path
from typing import Optional


class StorageManager:
    """Manages temporary file storage for videos."""
    
    def __init__(self, base_dir: Optional[str] = None):
        """Initialize storage manager."""
        if base_dir:
            self.base_dir = Path(base_dir)
            self.base_dir.mkdir(parents=True, exist_ok=True)
        else:
            self.base_dir = Path(tempfile.gettempdir()) / "telegram-video-gen"
            self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def create_temp_file(self, suffix: str = ".mp4") -> Path:
        """Create a temporary file and return its path."""
        fd, path = tempfile.mkstemp(suffix=suffix, dir=self.base_dir)
        os.close(fd)
        return Path(path)
    
    def cleanup(self, file_path: Path):
        """Delete a temporary file."""
        try:
            if file_path.exists():
                file_path.unlink()
        except Exception:
            pass  # Ignore cleanup errors
    
    def cleanup_all(self):
        """Clean up all temporary files in the base directory."""
        try:
            for file_path in self.base_dir.glob("*"):
                if file_path.is_file():
                    file_path.unlink()
        except Exception:
            pass  # Ignore cleanup errors

