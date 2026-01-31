"""
Helper utility functions for the PDF Email Extractor.
"""
import os
import time
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)


def cleanup_old_files(directory: Path, max_age_seconds: int) -> int:
    """
    Remove files older than max_age_seconds from a directory.
    
    Args:
        directory: Path to the directory to clean
        max_age_seconds: Maximum age of files in seconds (0 = delete all)
        
    Returns:
        Number of files deleted
    """
    if not directory.exists():
        return 0
    
    deleted_count = 0
    current_time = time.time()
    
    for file_path in directory.iterdir():
        if file_path.is_file() and file_path.name != '.gitkeep':
            try:
                file_age = current_time - file_path.stat().st_mtime
                if max_age_seconds == 0 or file_age > max_age_seconds:
                    file_path.unlink()
                    deleted_count += 1
                    logger.debug(f"Deleted old file: {file_path}")
            except Exception as e:
                logger.warning(f"Could not delete {file_path}: {e}")
    
    if deleted_count > 0:
        logger.info(f"Cleaned up {deleted_count} old files from {directory}")
    
    return deleted_count


def generate_unique_filename(base_name: str, directory: Path) -> str:
    """
    Generate a unique filename to avoid collisions.
    
    Args:
        base_name: Original filename
        directory: Directory where the file will be saved
        
    Returns:
        Unique filename
    """
    stem = Path(base_name).stem
    suffix = Path(base_name).suffix
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    unique_name = f"{stem}_{timestamp}{suffix}"
    counter = 1
    
    while (directory / unique_name).exists():
        unique_name = f"{stem}_{timestamp}_{counter}{suffix}"
        counter += 1
    
    return unique_name


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to remove potentially dangerous characters.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Remove path separators
    filename = filename.replace('/', '_').replace('\\', '_')
    
    # Remove null bytes
    filename = filename.replace('\x00', '')
    
    # Remove other dangerous characters
    dangerous_chars = '<>:"|?*'
    for char in dangerous_chars:
        filename = filename.replace(char, '_')
    
    # Limit length
    if len(filename) > 200:
        stem = Path(filename).stem[:190]
        suffix = Path(filename).suffix
        filename = f"{stem}{suffix}"
    
    return filename


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted string (e.g., "1.5 MB")
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def setup_logging(log_level: str = "INFO") -> None:
    """
    Configure logging for the application.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )


def is_valid_uuid(uuid_string: str) -> bool:
    """
    Check if a string is a valid UUID.
    
    Args:
        uuid_string: String to check
        
    Returns:
        True if valid UUID, False otherwise
    """
    import uuid
    try:
        uuid.UUID(uuid_string)
        return True
    except (ValueError, AttributeError):
        return False
