"""Command-line interface for the OpenAPI x-mint processor."""

import argparse
import sys
from pathlib import Path

import justsdk

from .add_mint import process_reference_files, process_file
from ._constants import DEFAULT_REFERENCE_DIR, JSON_EXTENSION


def create_parser():
    """Create and configure the argument parser."""
    parser = argparse.ArgumentParser(
        description="Add x-mint fields to OpenAPI specifications", prog="add-x-mint"
    )

    parser.add_argument(
        "--dir",
        "-d",
        type=str,
        default=DEFAULT_REFERENCE_DIR,
        help=f"Directory containing JSON files to process (default: {DEFAULT_REFERENCE_DIR})",
    )

    parser.add_argument(
        "--file", "-f", type=str, help="Process a single file instead of a directory"
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )

    return parser


def main():
    """Main CLI function."""
    parser = create_parser()
    args = parser.parse_args()

    justsdk.print_info("Starting OpenAPI x-mint field processor...")

    try:
        if args.file:
            # Process single file
            file_path = Path(args.file)
            if not file_path.exists():
                justsdk.print_error(f"Error: File '{file_path}' does not exist.")
                sys.exit(1)

            if not file_path.suffix.lower() == JSON_EXTENSION:
                justsdk.print_error(f"Error: File '{file_path}' is not a JSON file.")
                sys.exit(1)

            success = process_file(file_path)
            if success:
                justsdk.print_success(f"Successfully processed '{file_path.name}'!")
            else:
                justsdk.print_error(f"Failed to process '{file_path.name}'.")
                sys.exit(1)
        else:
            # Process directory
            success = process_reference_files(args.dir)
            if success:
                justsdk.print_success("\nAll files processed successfully!")
            else:
                justsdk.print_warning(
                    "\nSome files could not be processed. Check the errors above."
                )
                sys.exit(1)

    except Exception as e:
        justsdk.print_error(f"Unexpected error: {e}")
        if args.verbose:
            import traceback

            traceback.print_exc()
        sys.exit(1)
