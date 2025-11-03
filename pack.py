"""
Pack command implementation.
"""

import json
import logging
from pathlib import Path
from typing import List, Tuple

from .filedetect import is_text_file
from .ignore import IgnoreFilter
from .serialization import serialize_directory_tree
from .compression import compress_data
from .crypto import encrypt_multilayer
from .utils import atomic_write

logger = logging.getLogger(__name__)


def collect_files(
    source_dir: Path,
    ignore_filter: IgnoreFilter,
    include_binaries: bool = False,
    follow_symlinks: bool = False
) -> List[Tuple[Path, str, str]]:
    """
    Collect all text files from the source directory.
    
    Args:
        source_dir: Source directory path
        ignore_filter: Ignore filter instance
        include_binaries: Include binary files
        follow_symlinks: Follow symbolic links
        
    Returns:
        List of tuples (file_path, encoding, content)
    """
    logger.info(f"Collecting files from {source_dir}")
    
    files = []
    
    def _walk_directory(current_dir: Path) -> None:
        """Recursively walk directory, respecting ignore patterns."""
        try:
            for item in sorted(current_dir.iterdir()):
                if item.is_symlink() and not follow_symlinks:
                    logger.debug(f"Skipping symlink: {item}")
                    continue
                
                if ignore_filter.should_ignore(item):
                    logger.debug(f"Ignored by .eprignore: {item}")
                    continue
                
                if item.is_dir():
                    _walk_directory(item)
                elif item.is_file():
                    is_text, encoding = is_text_file(item, include_binaries)
                    
                    if not is_text:
                        logger.debug(f"Skipping binary file: {item}")
                        continue
                    
                    try:
                        with open(item, 'r', encoding=encoding) as f:
                            content = f.read()
                        
                        files.append((item, encoding, content))
                        logger.debug(f"Added: {item} ({encoding}, {len(content)} chars)")
                        
                    except Exception as e:
                        logger.warning(f"Error reading {item}: {e}")
        except PermissionError as e:
            logger.warning(f"Permission denied accessing {current_dir}: {e}")
    
    _walk_directory(source_dir)
    
    logger.info(f"Collected {len(files)} files")
    
    return files


def pack_directory(
    source: Path,
    output: Path,
    keys_file: Path,
    passphrase: str,
    follow_symlinks: bool = False,
    preserve_perms: bool = True,
    include_binaries: bool = False
) -> None:
    """
    Pack a directory into an encrypted .epr file.
    
    Args:
        source: Source directory path
        output: Output .epr file path
        keys_file: Path to write keys.json
        passphrase: Passphrase for encryption
        follow_symlinks: Follow symbolic links
        preserve_perms: Preserve file permissions
        include_binaries: Include binary files
    """
    logger.info(f"Packing directory: {source} -> {output}")
    
    if not source.exists() or not source.is_dir():
        raise ValueError(f"Source must be an existing directory: {source}")
    
    ignore_filter = IgnoreFilter(source)
    
    files = collect_files(source, ignore_filter, include_binaries, follow_symlinks)
    
    if not files:
        raise ValueError(f"No files to pack in {source}")
    
    logger.info("Serializing directory tree")
    serialized = serialize_directory_tree(source, files, preserve_perms)
    
    logger.info("Compressing (pre-encryption)")
    compressed = compress_data(serialized, stage="pre-encryption")
    
    logger.info("Encrypting with six layers")
    encrypted, key_metadata = encrypt_multilayer(compressed, passphrase)
    
    logger.info("Compressing (post-encryption)")
    final_data = compress_data(encrypted, stage="post-encryption")
    
    logger.info(f"Writing .epr file: {output}")
    atomic_write(output, final_data)
    
    logger.info(f"Writing keys file: {keys_file}")
    keys_json = json.dumps(key_metadata, indent=2)
    atomic_write(keys_file, keys_json.encode('utf-8'))
    
    logger.info(f"Pack complete: {len(files)} files, {len(serialized)} -> {len(final_data)} bytes "
               f"({100 * len(final_data) / len(serialized):.1f}%)")
