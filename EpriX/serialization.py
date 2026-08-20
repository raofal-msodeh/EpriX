"""
Directory tree serialization and deserialization.
"""

import json
import logging
import os
import stat
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def serialize_directory_tree(
    source_dir: Path,
    files: List[Tuple[Path, str, str]],
    preserve_perms: bool = True
) -> bytes:
    """
    Serialize directory tree and file contents to JSON format.
    
    Args:
        source_dir: Source directory path
        files: List of tuples (file_path, encoding, content)
        preserve_perms: Whether to preserve file permissions
        
    Returns:
        Serialized JSON bytes
    """
    logger.info(f"Serializing {len(files)} files from {source_dir}")
    
    manifest = {
        'version': '1.0',
        'source_dir': str(source_dir),
        'created': datetime.now(timezone.utc).isoformat(),
        'preserve_perms': preserve_perms,
        'files': []
    }
    
    for file_path, encoding, content in files:
        rel_path = file_path.relative_to(source_dir)
        
        file_info = {
            'path': str(rel_path).replace('\\', '/'),
            'encoding': encoding,
            'content': content,
            'size': len(content.encode(encoding))
        }
        
        if preserve_perms:
            try:
                file_stat = file_path.stat()
                file_info['mode'] = stat.filemode(file_stat.st_mode)
                file_info['mode_int'] = file_stat.st_mode
                file_info['mtime'] = file_stat.st_mtime
            except Exception as e:
                logger.warning(f"Could not get permissions for {rel_path}: {e}")
        
        manifest['files'].append(file_info)
    
    json_data = json.dumps(manifest, ensure_ascii=False, indent=None, separators=(',', ':'))
    serialized = json_data.encode('utf-8')
    
    logger.info(f"Serialized {len(files)} files to {len(serialized)} bytes")
    
    return serialized


def deserialize_directory_tree(
    data: bytes,
    target_dir: Path,
    preserve_perms: bool = True,
    dry_run: bool = False
) -> int:
    """
    Deserialize directory tree and reconstruct files.
    
    Args:
        data: Serialized JSON data
        target_dir: Target directory path
        preserve_perms: Whether to restore file permissions
        dry_run: If True, don't actually write files
        
    Returns:
        Number of files that would be/were created
    """
    manifest = json.loads(data.decode('utf-8'))
    
    logger.info(f"Deserializing {len(manifest['files'])} files to {target_dir}")
    
    if not dry_run:
        target_dir.mkdir(parents=True, exist_ok=True)
    
    files_created = 0
    
    for file_info in manifest['files']:
        file_path = Path(file_info['path'])
        
        from .utils import sanitize_path
        target_file = sanitize_path(target_dir, str(file_path))
        
        if dry_run:
            logger.info(f"[DRY RUN] Would create: {target_file}")
            files_created += 1
            continue
        
        target_file.parent.mkdir(parents=True, exist_ok=True)
        
        content = file_info['content']
        encoding = file_info['encoding']
        
        with open(target_file, 'w', encoding=encoding) as f:
            f.write(content)
        
        if preserve_perms and manifest.get('preserve_perms') and 'mode_int' in file_info:
            try:
                os.chmod(target_file, stat.S_IMODE(file_info['mode_int']))
            except Exception as e:
                logger.warning(f"Could not restore permissions for {target_file}: {e}")
        
        if 'mtime' in file_info:
            try:
                os.utime(target_file, (file_info['mtime'], file_info['mtime']))
            except Exception as e:
                logger.warning(f"Could not restore mtime for {target_file}: {e}")
        
        files_created += 1
        logger.debug(f"Created: {target_file}")
    
    logger.info(f"{'[DRY RUN] Would create' if dry_run else 'Created'} {files_created} files")
    
    return files_created
