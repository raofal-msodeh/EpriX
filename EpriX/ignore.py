"""
.eprignore file handling with gitignore-compatible pattern matching.
"""

import logging
from pathlib import Path
from typing import Set, List
import pathspec

logger = logging.getLogger(__name__)


class IgnoreFilter:
    """
    Filter files based on .eprignore patterns (gitignore syntax).
    """
    
    def __init__(self, source_dir: Path):
        """
        Initialize ignore filter.
        
        Args:
            source_dir: Source directory to search for .eprignore
        """
        self.source_dir = source_dir
        self.spec = None
        self._load_ignore_file()
    
    def _load_ignore_file(self) -> None:
        """Load .eprignore file from source directory."""
        ignore_file = self.source_dir / '.eprignore'
        
        if ignore_file.exists():
            try:
                with open(ignore_file, 'r', encoding='utf-8') as f:
                    patterns = f.read().splitlines()
                
                patterns = [p.strip() for p in patterns if p.strip() and not p.strip().startswith('#')]
                
                if patterns:
                    self.spec = pathspec.PathSpec.from_lines('gitwildmatch', patterns)
                    logger.info(f"Loaded {len(patterns)} patterns from .eprignore")
            except Exception as e:
                logger.warning(f"Error loading .eprignore: {e}")
    
    def should_ignore(self, path: Path) -> bool:
        """
        Check if a path should be ignored.
        
        Args:
            path: Path to check (relative to source_dir)
            
        Returns:
            True if path should be ignored
        """
        if self.spec is None:
            return False
        
        try:
            rel_path = path.relative_to(self.source_dir)
            path_str = str(rel_path).replace('\\', '/')
            
            is_dir = path.is_dir()
            if is_dir and not path_str.endswith('/'):
                path_str += '/'
            
            return self.spec.match_file(path_str)
        except ValueError:
            return False
