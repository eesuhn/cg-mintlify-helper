import argparse
import sys
import justsdk

from pathlib import Path
from .add_mint import (
    process_reference_files as add_mint_process_files,
    process_file as add_mint_process_file,
)
from .convert_md_to_mdx import (
    process_reference_files as convert_md_process_files,
    process_file as convert_md_process_file,
    process_demo_files,
    process_pro_files,
    process_mode_files,
)
from ._constants import (
    DEFAULT_REFERENCE_DIR,
    JSON_EXTENSION,
    DEMO_MODE,
    PRO_MODE,
    VALID_MODES,
)


def create_parser():
    parser = argparse.ArgumentParser(
        description="CLI to process OAS for Mintlify",
        prog="mintlify-oas-cli",
    )

    parser.add_argument(
        "mode",
        choices=["add-mint", "convert-mdx"],
        help="Choose the processing mode",
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
        "--output",
        "-o",
        type=str,
        help="Output directory for generated files (only for convert-mdx mode)",
    )

    parser.add_argument(
        "--api-mode",
        choices=VALID_MODES,
        help=f"API mode to process: {', '.join(VALID_MODES)} (only for convert-mdx mode)",
    )

    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose output"
    )

    return parser


def main():
    parser = create_parser()
    args = parser.parse_args()

    if args.mode == "add-mint":
        justsdk.print_info("Starting OpenAPI x-mint field processor...")
        process_file_func = add_mint_process_file
        process_files_func = add_mint_process_files
    elif args.mode == "convert-mdx":
        justsdk.print_info("Starting OpenAPI markdown to MDX converter...")
        process_file_func = convert_md_process_file

        if args.api_mode == DEMO_MODE:
            process_files_func = process_demo_files
        elif args.api_mode == PRO_MODE:
            process_files_func = process_pro_files
        else:
            process_files_func = convert_md_process_files
    else:
        justsdk.print_error(f"Unknown mode: {args.mode}")
        sys.exit(1)

    try:
        if args.file:
            file_path = Path(args.file)
            if not file_path.exists():
                justsdk.print_error(f"Error: File '{file_path}' does not exist.")
                sys.exit(1)

            if not file_path.suffix.lower() == JSON_EXTENSION:
                justsdk.print_error(f"Error: File '{file_path}' is not a JSON file.")
                sys.exit(1)

            if args.mode == "convert-mdx" and args.output:
                output_dir = Path(args.output)
                success = process_file_func(file_path, output_dir)
            else:
                success = process_file_func(file_path)

            if success:
                justsdk.print_success(f"Successfully processed '{file_path.name}'!")
            else:
                justsdk.print_error(f"Failed to process '{file_path.name}'.")
                sys.exit(1)
        else:
            if args.mode == "convert-mdx" and args.api_mode:
                if args.output:
                    success = process_mode_files(args.api_mode, args.dir, args.output)
                else:
                    success = process_mode_files(args.api_mode, args.dir)
            elif args.mode == "convert-mdx" and args.output:
                success = process_files_func(args.dir, args.output)
            else:
                success = process_files_func(args.dir)

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
