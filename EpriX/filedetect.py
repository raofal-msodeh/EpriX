"""
File type detection and encoding identification.
"""

import logging
import magic
import chardet
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


def is_text_file(file_path: Path, include_binaries: bool = False) -> Tuple[bool, Optional[str]]:
    """
    Detect if a file is a text file and determine its encoding.
    
    Args:
        file_path: Path to file to check
        include_binaries: If True, include all files
        
    Returns:
        Tuple of (is_text, encoding)
    """
    if include_binaries:
        encoding = detect_encoding(file_path)
        return (True, encoding if encoding else 'utf-8')
    
    try:
        mime = magic.from_file(str(file_path), mime=True)
        
        if mime.startswith('text/'):
            encoding = detect_encoding(file_path)
            return (True, encoding if encoding else 'utf-8')
        
        if mime in ['application/json', 'application/xml', 'application/javascript',
                    'application/x-yaml', 'application/x-sh']:
            encoding = detect_encoding(file_path)
            return (True, encoding if encoding else 'utf-8')
        
        encoding = detect_encoding(file_path)
        if encoding:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    f.read(1024)
                return (True, encoding)
            except (UnicodeDecodeError, LookupError):
                pass
        
        return (False, None)
        
    except Exception as e:
        logger.warning(f"Error detecting file type for {file_path}: {e}")
        return (False, None)


def detect_encoding(file_path: Path) -> Optional[str]:
    """
    Detect the encoding of a text file.
    
    Args:
        file_path: Path to file
        
    Returns:
        Detected encoding or None
    """
    try:
        with open(file_path, 'rb') as f:
            raw_data = f.read(10000)
        
        if raw_data.startswith(b'\xff\xfe') or raw_data.startswith(b'\xfe\xff'):
            return 'utf-16'
        elif raw_data.startswith(b'\xef\xbb\xbf'):
            return 'utf-8-sig'
        
        result = chardet.detect(raw_data)
        if result and result['encoding'] and result['confidence'] > 0.7:
            encoding = result['encoding']
            
            if encoding.lower() in ['ascii', 'utf-8', 'utf-16', 'utf-16-le', 'utf-16-be', 
                                     'iso-8859-1', 'windows-1252']:
                return encoding
        
        try:
            raw_data.decode('utf-8')
            return 'utf-8'
        except UnicodeDecodeError:
            pass
        
        return None
        
    except Exception as e:
        logger.debug(f"Error detecting encoding for {file_path}: {e}")
        return None
