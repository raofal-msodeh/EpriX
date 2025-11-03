"""
Command-line interface for eprtool.
"""

import sys
import argparse
import logging
from pathlib import Path

from .pack import pack_directory
from .unpack import unpack_directory
from .utils import setup_logging
from .router import app 

logger = logging.getLogger(__name__)


def create_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser."""
    
    parser = argparse.ArgumentParser(
        prog='eprtool',
        description='Secure file packing/unpacking tool with six-layer encryption',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Pack a directory:
    eprtool pack --source ./myproject --output archive.epr --keys keys.json --passphrase "MySecurePass"
    
  Unpack an archive:
    eprtool unpack --input archive.epr --keys keys.json --passphrase "MySecurePass" --target ./restored
    
  Dry-run unpack:
    eprtool unpack --input archive.epr --keys keys.json --passphrase "MySecurePass" --target ./restored --dry-run

Security Notes:
  - Store keys.json separately from .epr files
  - Losing keys.json or passphrase means permanent data loss
  - Use strong passphrases (20+ characters recommended)
        """
    )
    
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose logging')
    parser.add_argument('--quiet', '-q', action='store_true', help='Enable quiet mode (warnings/errors only)')
    
    subparsers = parser.add_subparsers(dest='command', required=True, help='Command to execute')
    
    # Pack command
    pack_parser = subparsers.add_parser('pack', help='Pack a directory into an encrypted .epr file')
    pack_parser.add_argument('--source', '-s', type=Path, required=True, help='Source directory to pack')
    pack_parser.add_argument('--output', '-o', type=Path, required=True, help='Output .epr file path')
    pack_parser.add_argument('--keys', '-k', type=Path, required=True, help='Path to write keys.json')
    pack_parser.add_argument('--passphrase', '-p', type=str, required=True, help='Passphrase for encryption')
    pack_parser.add_argument('--follow-symlinks', action='store_true', help='Follow symbolic links')
    pack_parser.add_argument('--preserve-perms', action='store_true', default=True, help='Preserve file permissions (default: true)')
    pack_parser.add_argument('--include-binaries', action='store_true', help='Include binary files (default: text only)')
    
    # Unpack command
    unpack_parser = subparsers.add_parser('unpack', help='Unpack an encrypted .epr file')
    unpack_parser.add_argument('--input', '-i', type=Path, required=True, help='Input .epr file path')
    unpack_parser.add_argument('--keys', '-k', type=Path, required=True, help='Path to keys.json')
    unpack_parser.add_argument('--passphrase', '-p', type=str, required=True, help='Passphrase for decryption')
    unpack_parser.add_argument('--target', '-t', type=Path, required=True, help='Target directory for unpacked files')
    unpack_parser.add_argument('--dry-run', action='store_true', help='Show what would be done without writing files')
    unpack_parser.add_argument('--overwrite', action='store_true', help='Allow overwriting existing files')
    
    # Server command - الجديد
    server_parser = subparsers.add_parser('server', help='Server operations')
    server_parser.add_argument('--host', '-h', type=str, default="0.0.0.0", 
                          help='Host for the server (default: localhost\"0.0.0.0\")')
    server_parser.add_argument('--port', '-p', type=int, default=8000, 
                          help='Port number for the server (default: 8000)')
                          
    
    return parser


def main() -> int:
    """
    Main entry point for the CLI.
    
    Returns:
        Exit code (0 for success, non-zero for errors)
    """
    parser = create_parser()
    args = parser.parse_args()
    
    setup_logging(verbose=args.verbose, quiet=args.quiet)
    
    try:
        if args.command == 'pack':
            pack_directory(
                source=args.source,
                output=args.output,
                keys_file=args.keys,
                passphrase=args.passphrase,
                follow_symlinks=args.follow_symlinks,
                preserve_perms=args.preserve_perms,
                include_binaries=args.include_binaries
            )
            print(f"✓ Successfully packed {args.source} -> {args.output}")
            return 0
            
        elif args.command == 'unpack':
            unpack_directory(
                input_file=args.input,
                keys_file=args.keys,
                passphrase=args.passphrase,
                target=args.target,
                dry_run=args.dry_run,
                overwrite=args.overwrite
            )
            if args.dry_run:
                print(f"✓ Dry-run complete. Would unpack {args.input} -> {args.target}")
            else:
                print(f"✓ Successfully unpacked {args.input} -> {args.target}")
            return 0
        
        elif args.command == 'server':  # الجديد
            import uvicorn
            uvicorn.run(app, host=args.host, port=args.port)
            return 0
        
    except KeyboardInterrupt:
        logger.error("Operation cancelled by user")
        return 130
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=args.verbose)
        return 1
    
    return 1


if __name__ == '__main__':
    sys.exit(main())