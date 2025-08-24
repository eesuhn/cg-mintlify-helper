"""OpenAPI x-mint field processor module."""

import justsdk
from pathlib import Path

from ._constants import HTTP_METHODS, DEFAULT_REFERENCE_DIR


def add_mint_fields(openapi_data):
    """
    Add x-mint field to each operation in the OpenAPI specification.

    Args:
        openapi_data (dict): The parsed OpenAPI specification

    Returns:
        dict: Modified OpenAPI specification with x-mint fields added
    """
    if "paths" not in openapi_data:
        print("Warning: No 'paths' found in the OpenAPI specification")
        return openapi_data

    operations_processed = 0
    operations_skipped = 0

    # Iterate through all paths
    for path, path_item in openapi_data["paths"].items():
        for method in HTTP_METHODS:
            if method in path_item:
                operation = path_item[method]

                # Check if operationId exists
                if "operationId" in operation:
                    operation_id = operation["operationId"]

                    # Skip if x-mint already exists
                    if "x-mint" in operation:
                        operations_skipped += 1
                        continue

                    # Add x-mint field after operationId
                    # First, we need to preserve the order by creating a new dict
                    new_operation = {}

                    for key, value in operation.items():
                        new_operation[key] = value

                        # Add x-mint right after operationId
                        if key == "operationId":
                            new_operation["x-mint"] = {
                                "href": f"/reference/{operation_id}"
                            }

                    # Replace the operation with the new one
                    path_item[method] = new_operation
                    operations_processed += 1
                    print(
                        f"Added x-mint field to {method.upper()} {path} (operationId: {operation_id})"
                    )
                else:
                    print(f"Warning: No operationId found for {method.upper()} {path}")

    print(f"\nProcessed {operations_processed} operations successfully!")
    if operations_skipped > 0:
        print(
            f"Skipped {operations_skipped} operations that already had x-mint fields."
        )
    return openapi_data


def process_file(json_file):
    """
    Process a single JSON file to add x-mint fields.

    Args:
        json_file (Path): Path to the JSON file to process

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        justsdk.print_info(f"Processing '{json_file.name}'...")

        # Read JSON file using justsdk
        openapi_data = justsdk.read_file(json_file, use_orjson=True)

        # Process the OpenAPI data
        modified_data = add_mint_fields(openapi_data)

        # Write back using justsdk
        justsdk.write_file(modified_data, json_file, use_orjson=True, atomic=True)

        justsdk.print_success(f"Successfully processed '{json_file.name}'!")
        return True

    except Exception as e:
        justsdk.print_error(f"Error processing '{json_file.name}': {e}")
        return False


def process_reference_files(reference_dir=None):
    """
    Process all JSON files in the reference folder.

    Args:
        reference_dir (str, optional): Path to reference directory. Defaults to "reference".

    Returns:
        bool: True if all files processed successfully, False otherwise
    """
    if reference_dir is None:
        reference_dir = Path(DEFAULT_REFERENCE_DIR)
    else:
        reference_dir = Path(reference_dir)

    # Check if reference directory exists
    if not reference_dir.exists():
        justsdk.print_error(
            f"Error: Reference directory '{reference_dir}' does not exist."
        )
        return False

    # Get all JSON files in reference directory
    json_files = list(reference_dir.glob("*.json"))

    if not json_files:
        justsdk.print_warning("No JSON files found in the reference directory.")
        return True

    justsdk.print_info(f"Found {len(json_files)} JSON file(s) to process:")
    for file in json_files:
        print(f"  - {file.name}")

    success_count = 0

    # Process each JSON file
    for json_file in json_files:
        if process_file(json_file):
            success_count += 1

    justsdk.print_info(
        f"\nCompleted processing {success_count}/{len(json_files)} files successfully!"
    )
    return success_count == len(json_files)
