"""
eprtool - Secure file packing/unpacking tool with six-layer encryption.

This package implements a production-quality CLI tool for securely packing
directory trees with multi-stage compression and six layers of encryption.
"""

__version__ = "1.0.0"
__author__ = "EPRTool Team"

from .pack import pack_directory
from .unpack import unpack_directory

__all__ = ["pack_directory", "unpack_directory"]
