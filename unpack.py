"""
Unpack command implementation.
"""

import json
import logging
from pathlib import Path

from .compression import decompress_data
from .crypto import decrypt_multilayer
from .serialization import deserialize_directory_tree

logger = logging.getLogger(__name__)


def unpack_directory(
    input_file: Path,
    keys_file: Path,
    passphrase: str,
    target: Path,
    dry_run: bool = False,
    overwrite: bool = False
) -> None:
    """
    Unpack an encrypted .epr file to a directory.
    
    Args:
        input_file: Input .epr file path
        keys_file: Path to keys.json
        passphrase: Passphrase for decryption
        target: Target directory path
        dry_run: If True, don't write files
        overwrite: If True, allow overwriting existing files
    """
    logger.info(f"Unpacking file: {input_file} -> {target}")
    
    if not input_file.exists():
        raise ValueError(f"Input file does not exist: {input_file}")
    
    if not keys_file.exists():
        raise ValueError(f"Keys file does not exist: {keys_file}")
    
    if target.exists() and not overwrite and not dry_run:
        if any(target.iterdir()):
            raise ValueError(f"Target directory is not empty: {target}. Use --overwrite to proceed.")
    
    logger.info(f"Loading keys from: {keys_file}")
    with open(keys_file, 'r', encoding='utf-8') as f:
        key_metadata = json.load(f)
    
    logger.info(f"Reading .epr file: {input_file}")
    with open(input_file, 'rb') as f:
        encrypted_data = f.read()
    
    logger.info("Decompressing (post-encryption)")
    decrypted_compressed = decompress_data(encrypted_data, stage="post-encryption")
    
    logger.info("Decrypting six layers")
    try:
        decrypted = decrypt_multilayer(decrypted_compressed, key_metadata, passphrase)
    except Exception as e:
        logger.error(f"Decryption failed: {e}")
        raise ValueError("Decryption failed. Possible causes: incorrect passphrase, corrupted file, or tampering detected.")
    
    logger.info("Decompressing (pre-encryption)")
    decompressed = decompress_data(decrypted, stage="pre-encryption")
    
    logger.info("Deserializing directory tree")
    num_files = deserialize_directory_tree(decompressed, target, preserve_perms=True, dry_run=dry_run)
    
    logger.info(f"Unpack complete: {num_files} files {'would be' if dry_run else ''} restored")
