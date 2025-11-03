"""
Utility functions for eprtool.
"""

import os
import secrets
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def secure_random_bytes(length: int) -> bytes:
    """
    Generate cryptographically secure random bytes.
    
    Args:
        length: Number of bytes to generate
        
    Returns:
        Secure random bytes
    """
    return secrets.token_bytes(length)


def atomic_write(file_path: Path, data: bytes) -> None:
    """
    Write data to a file atomically using a temp file and rename.
    
    Args:
        file_path: Target file path
        data: Data to write
    """
    temp_path = file_path.with_suffix(file_path.suffix + '.tmp')
    try:
        with open(temp_path, 'wb') as f:
            f.write(data)
        temp_path.replace(file_path)
        logger.debug(f"Atomically wrote {len(data)} bytes to {file_path}")
    except Exception as e:
        if temp_path.exists():
            temp_path.unlink()
        raise e


def sanitize_path(base_path: Path, target_path: str) -> Path:
    """
    Sanitize and validate a path to prevent directory traversal attacks.
    
    Args:
        base_path: Base directory path
        target_path: Target relative path to validate
        
    Returns:
        Resolved safe path
        
    Raises:
        ValueError: If path attempts to escape base directory
    """
    base_resolved = base_path.resolve()
    target_resolved = (base_path / target_path).resolve()
    
    try:
        target_resolved.relative_to(base_resolved)
    except ValueError:
        raise ValueError(f"Path traversal detected: {target_path} escapes {base_path}")
    
    return target_resolved


def setup_logging(verbose: bool = False, quiet: bool = False) -> None:
    """
    Set up logging configuration.
    
    Args:
        verbose: Enable verbose (DEBUG) logging
        quiet: Enable quiet mode (WARNING and ERROR only)
    """
    if quiet:
        level = logging.WARNING
    elif verbose:
        level = logging.DEBUG
    else:
        level = logging.INFO
    
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    logging.getLogger('eprtool').setLevel(level)
