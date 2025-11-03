"""
Multi-stage compression using Zstandard and LZMA.
"""

import logging
import lzma
import zstandard as zstd
from io import BytesIO

logger = logging.getLogger(__name__)

ZSTD_COMPRESSION_LEVEL = 22
LZMA_PRESET = 9


def compress_data(data: bytes, stage: str = "pre-encryption") -> bytes:
    """
    Compress data using two-stage compression (Zstandard -> LZMA) for pre-encryption,
    or single-stage Zstandard for post-encryption.
    
    Args:
        data: Data to compress
        stage: Either "pre-encryption" (two-stage) or "post-encryption" (single-stage)
        
    Returns:
        Compressed data
    """
    logger.info(f"Starting {stage} compression on {len(data)} bytes")
    
    if stage == "pre-encryption":
        logger.debug("Stage 1: Zstandard compression")
        cctx = zstd.ZstdCompressor(level=ZSTD_COMPRESSION_LEVEL)
        zstd_compressed = cctx.compress(data)
        logger.debug(f"Zstandard: {len(data)} -> {len(zstd_compressed)} bytes "
                    f"({100 * len(zstd_compressed) / len(data):.1f}%)")
        
        logger.debug("Stage 2: LZMA compression")
        lzma_compressed = lzma.compress(
            zstd_compressed,
            format=lzma.FORMAT_XZ,
            preset=LZMA_PRESET
        )
        logger.debug(f"LZMA: {len(zstd_compressed)} -> {len(lzma_compressed)} bytes "
                    f"({100 * len(lzma_compressed) / len(zstd_compressed):.1f}%)")
        
        result = lzma_compressed
        
    else:
        logger.debug("Single-stage Zstandard compression")
        cctx = zstd.ZstdCompressor(level=ZSTD_COMPRESSION_LEVEL)
        result = cctx.compress(data)
        logger.debug(f"Zstandard: {len(data)} -> {len(result)} bytes "
                    f"({100 * len(result) / len(data):.1f}%)")
    
    logger.info(f"{stage} compression complete: {len(data)} -> {len(result)} bytes "
               f"({100 * len(result) / len(data):.1f}%)")
    
    return result


def decompress_data(data: bytes, stage: str = "post-encryption") -> bytes:
    """
    Decompress data using single-stage Zstandard for post-encryption,
    or two-stage (LZMA -> Zstandard) for pre-encryption.
    
    Args:
        data: Compressed data
        stage: Either "post-encryption" (single-stage) or "pre-encryption" (two-stage)
        
    Returns:
        Decompressed data
    """
    logger.info(f"Starting {stage} decompression on {len(data)} bytes")
    
    if stage == "pre-encryption":
        logger.debug("Stage 1: LZMA decompression")
        lzma_decompressed = lzma.decompress(data, format=lzma.FORMAT_XZ)
        logger.debug(f"LZMA: {len(data)} -> {len(lzma_decompressed)} bytes")
        
        logger.debug("Stage 2: Zstandard decompression")
        dctx = zstd.ZstdDecompressor()
        result = dctx.decompress(lzma_decompressed)
        logger.debug(f"Zstandard: {len(lzma_decompressed)} -> {len(result)} bytes")
        
    else:
        logger.debug("Single-stage Zstandard decompression")
        dctx = zstd.ZstdDecompressor()
        result = dctx.decompress(data)
        logger.debug(f"Zstandard: {len(data)} -> {len(result)} bytes")
    
    logger.info(f"{stage} decompression complete: {len(data)} -> {len(result)} bytes")
    
    return result
