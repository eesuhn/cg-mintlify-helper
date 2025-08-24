import re
import requests
import justsdk

from pathlib import Path
from ._constants import (
    HTTP_METHODS,
    DEFAULT_REFERENCE_DIR,
    COINGECKO_DOCS_BASE_URL,
    COINGECKO_DEMO_DOCS_BASE_URL,
    REQUEST_TIMEOUT,
    DEMO_MODE,
    PRO_MODE,
    VALID_MODES,
    DEFAULT_MDX_DIR,
)


def extract_tips_and_notes(content):
    """
    Extract Tips, Notes, and Notice sections from markdown content.
    """
    patterns = [
        # Capture Notice section
        ("notice", r"(>\s*🚧.*?(?:Notice|Warning).*?)(?=\n\n>\s*[👍📘]|\n\n[^>]|\Z)"),
        # Capture Tips section
        ("tips", r"(>\s*👍.*?Tips.*?)(?=\n\n>\s*[📘🚧]|\n\n[^>]|\Z)"),
        # Capture Notes section
        ("notes", r"(>\s*📘.*?Notes.*?)(?=\n\n>\s*[👍🚧]|\n\n[^>]|\Z)"),
    ]

    # Dictionary to store matches by type
    matches_by_type = {"notice": [], "tips": [], "notes": []}

    for section_type, pattern in patterns:
        matches = re.findall(pattern, content, flags=re.MULTILINE | re.DOTALL)
        if matches:
            matches_by_type[section_type].extend(matches)

    # Combine matches in the desired order: Notice, Tips, Notes
    all_matches = []
    for section_type in ["notice", "tips", "notes"]:
        all_matches.extend(matches_by_type[section_type])

    if not all_matches:
        return ""

    unique_matches = []
    for match in all_matches:
        if match not in unique_matches:
            unique_matches.append(match)

    return "\n\n".join(unique_matches)


def convert_blockquote_to_component(content):
    """
    Convert blockquote-style Tips, Notes, and Notice to Mintlify MDX components.
    """

    def process_blockquote_match(match):
        """Process a single blockquote match and convert it to MDX component."""
        full_match = match.group(0)

        # Check the content for section type
        if "👍" in full_match or "Tips" in full_match:
            component_type = "Tip"
            title = "Tips"
        elif "📘" in full_match or "Notes" in full_match:
            component_type = "Note"
            title = "Note"
        elif "🚧" in full_match or "Notice" in full_match or "Warning" in full_match:
            component_type = "Warning"
            title = "Notice"
        else:
            component_type = "Note"
            title = "Note"

        # Process the entire content, removing blockquote markers
        lines = full_match.split("\n")
        cleaned_lines = []

        # Skip the header line (first line with emoji and title)
        content_started = False

        for line in lines:
            # Remove leading > and minimal whitespace
            cleaned_line = re.sub(r"^>\s?", "", line)

            if not content_started:
                if (
                    cleaned_line.strip() == ""
                    or "👍" in cleaned_line
                    and "Tips" in cleaned_line
                    or "📘" in cleaned_line
                    and "Notes" in cleaned_line
                    or "🚧" in cleaned_line
                    and ("Notice" in cleaned_line or "Warning" in cleaned_line)
                ):
                    continue
                content_started = True

            # Convert * to - for consistency, preserving indentation
            cleaned_line = re.sub(r"^(\s*)\*\s+", r"\1- ", cleaned_line)

            cleaned_line = cleaned_line.replace("‘", "'")
            cleaned_line = cleaned_line.replace("’", "'")
            cleaned_line = cleaned_line.replace("“", '"')
            cleaned_line = cleaned_line.replace("”", '"')

            # Remove extra escaping from quotes in URLs/text
            cleaned_line = cleaned_line.replace('`"', '"').replace('"`', '"')

            cleaned_lines.append(cleaned_line)

        component_content = "\n".join(cleaned_lines).strip()

        # Indent the content by 2 spaces for proper MDX formatting
        indented_lines = []
        for line in component_content.split("\n"):
            if line.strip():  # Only indent non-empty lines
                indented_lines.append("  " + line)
            else:
                indented_lines.append(line)
        indented_content = "\n".join(indented_lines)

        mdx_component = f"<{component_type}>\n  ### {title}\n\n{indented_content}\n</{component_type}>"

        return mdx_component

    # Process patterns in the desired order: Notice, Tips, Notes
    patterns = [
        r"(>\s*🚧.*?(?:Notice|Warning).*?)(?=\n\n>\s*[👍📘]|\n\n[^>]|\Z)",
        r"(>\s*👍.*?Tips.*?)(?=\n\n>\s*[📘🚧]|\n\n[^>]|\Z)",
        r"(>\s*📘.*?Notes.*?)(?=\n\n>\s*[👍🚧]|\n\n[^>]|\Z)",
    ]

    converted_content = content

    for pattern in patterns:
        converted_content = re.sub(
            pattern,
            process_blockquote_match,
            converted_content,
            flags=re.MULTILINE | re.DOTALL,
        )

    return converted_content


def convert_reference_links(content, mode=None):
    """
    Convert relative reference links to full CoinGecko documentation URLs.
    Uses different base URLs for demo and pro modes.
    """
    pattern = r"\[`([^`]+)`\]\(/reference/([^)]+)\)"

    def replace_link(match):
        endpoint = match.group(1)
        reference_id = match.group(2)

        if mode == DEMO_MODE:
            base_url = COINGECKO_DEMO_DOCS_BASE_URL
        else:
            base_url = COINGECKO_DOCS_BASE_URL

        return f"[`{endpoint}`](<{base_url}/{reference_id}>)"

    converted_content = re.sub(pattern, replace_link, content)

    return converted_content


def find_operation_path_and_method(openapi_data, target_operation_id):
    """
    Find the path and HTTP method for a given operation ID in OpenAPI data.
    Returns tuple of (path, method) or (None, None) if not found.
    """
    if "paths" not in openapi_data:
        return None, None

    for path, path_item in openapi_data["paths"].items():
        for method in HTTP_METHODS:
            if method in path_item:
                operation = path_item[method]
                if (
                    "operationId" in operation
                    and operation["operationId"] == target_operation_id
                ):
                    return path, method

    return None, None


def convert_md_to_mdx(content, openapi_metadata=None, mode=None):
    """
    Convert markdown content to MDX format with optional OpenAPI frontmatter.
    """
    extracted_content = extract_tips_and_notes(content)

    if not extracted_content:
        return ""

    converted_content = convert_blockquote_to_component(extracted_content)
    converted_content = convert_reference_links(converted_content, mode)

    if openapi_metadata and all(
        key in openapi_metadata for key in ["reference_file", "path", "method"]
    ):
        reference_file = openapi_metadata["reference_file"]
        path = openapi_metadata["path"]
        method = openapi_metadata["method"]

        frontmatter = (
            f"---\nopenapi: api-reference/{reference_file} {method} {path}\n---\n\n"
        )
        converted_content = frontmatter + converted_content

    return converted_content


def fetch_markdown_content(operation_id, mode=None):
    """
    Fetch markdown content from CoinGecko docs for a given operation ID.
    Uses different base URLs for demo and pro modes.
    """
    if mode == DEMO_MODE:
        base_url = COINGECKO_DEMO_DOCS_BASE_URL
    else:
        base_url = COINGECKO_DOCS_BASE_URL

    url = f"{base_url}/{operation_id}.md"

    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()

        justsdk.print_success(
            f"Fetched markdown content for '{operation_id}' from {base_url}"
        )
        return response.text

    except requests.exceptions.RequestException as e:
        justsdk.print_error(f"Failed to fetch '{operation_id}.md' from {base_url}: {e}")
        return None


def extract_operation_ids(openapi_data):
    """
    Extract all operation IDs from OpenAPI specification.
    """
    operation_ids = []

    if "paths" not in openapi_data:
        justsdk.print_warning("No 'paths' found in the OpenAPI specification")
        return operation_ids

    for path, path_item in openapi_data["paths"].items():
        for method in HTTP_METHODS:
            if method in path_item:
                operation = path_item[method]
                if "operationId" in operation:
                    operation_ids.append(operation["operationId"])

    return operation_ids


def process_operation_id(
    operation_id, output_dir, json_filename=None, openapi_data=None, mode=None
):
    """
    Process a single operation ID: fetch markdown and convert to MDX.
    """
    try:
        md_content = fetch_markdown_content(operation_id, mode)

        if md_content is None:
            return False

        # Prepare OpenAPI metadata for frontmatter
        openapi_metadata = None
        if json_filename and openapi_data:
            path, method = find_operation_path_and_method(openapi_data, operation_id)
            if path and method:
                openapi_metadata = {
                    "reference_file": f"{json_filename}.json",
                    "path": path,
                    "method": method,
                }

        mdx_content = convert_md_to_mdx(md_content, openapi_metadata, mode)

        if not mdx_content.strip():
            justsdk.print_debug(
                f"No Tips, Notes, or Notice sections found in '{operation_id}.md', skipping..."
            )
            return True  # Not an error, just no content to convert

        mdx_file_path = output_dir / f"{operation_id}.mdx"
        justsdk.write_file(mdx_content, mdx_file_path, atomic=True)
        justsdk.print_success(f"Created '{operation_id}.mdx'")
        return True

    except Exception as e:
        justsdk.print_error(f"Error processing operation '{operation_id}': {e}")
        return False


def process_file(json_file, output_dir=None, mode=None):
    """
    Process a single OpenAPI JSON file to generate MDX files.
    """
    try:
        justsdk.print_info(f"Processing '{json_file.name}'...")

        openapi_data = justsdk.read_file(json_file, use_orjson=True)
        operation_ids = extract_operation_ids(openapi_data)

        if not operation_ids:
            justsdk.print_warning(f"No operation IDs found in '{json_file.name}'")
            return True

        if output_dir is None:
            output_dir = json_file.parent

        output_dir.mkdir(parents=True, exist_ok=True)
        justsdk.print_info(f"Found {len(operation_ids)} operation IDs to process")

        success_count = 0
        json_filename = json_file.stem

        for operation_id in operation_ids:
            if process_operation_id(
                operation_id, output_dir, json_filename, openapi_data, mode
            ):
                success_count += 1

        justsdk.print_info(
            f"Successfully processed {success_count}/{len(operation_ids)} operations from '{json_file.name}'"
        )
        return success_count == len(operation_ids)

    except Exception as e:
        justsdk.print_error(f"Error processing '{json_file.name}': {e}")
        return False


def process_mode_files(mode, reference_dir=None, output_dir=None):
    """
    Process OpenAPI JSON files for a specific mode (pro or demo).
    """
    if mode not in VALID_MODES:
        justsdk.print_error(
            f"Error: Invalid mode '{mode}'. Valid modes are: {', '.join(VALID_MODES)}"
        )
        return False

    if reference_dir is None:
        reference_dir = Path(DEFAULT_REFERENCE_DIR)
    else:
        reference_dir = Path(reference_dir)

    if output_dir is None:
        output_dir = Path(DEFAULT_MDX_DIR)
    else:
        output_dir = Path(output_dir)

    mode_reference_dir = reference_dir / mode
    mode_output_dir = output_dir / mode

    if not mode_reference_dir.exists():
        justsdk.print_error(
            f"Error: Mode directory '{mode_reference_dir}' does not exist."
        )
        return False

    mode_output_dir.mkdir(parents=True, exist_ok=True)

    json_files = list(mode_reference_dir.glob("*.json"))

    if not json_files:
        justsdk.print_warning(f"No JSON files found in the {mode} directory.")
        return True

    justsdk.print_info(f"Processing {mode} mode with {len(json_files)} JSON file(s):")
    for file in json_files:
        print(f"  - {file.name}")

    success_count = 0

    for json_file in json_files:
        if process_file(json_file, mode_output_dir, mode):
            success_count += 1

    justsdk.print_info(
        f"\nCompleted processing {success_count}/{len(json_files)} {mode} files successfully!"
    )
    return success_count == len(json_files)


def process_demo_files(reference_dir=None, output_dir=None):
    """
    Process demo OpenAPI JSON files to generate MDX files.
    """
    return process_mode_files(DEMO_MODE, reference_dir, output_dir)


def process_pro_files(reference_dir=None, output_dir=None):
    """
    Process pro OpenAPI JSON files to generate MDX files.
    """
    return process_mode_files(PRO_MODE, reference_dir, output_dir)


def process_reference_files(reference_dir=None, output_dir=None, mode=None):
    """
    Process all OpenAPI JSON files in the reference folder to generate MDX files.
    """
    if reference_dir is None:
        reference_dir = Path(DEFAULT_REFERENCE_DIR)
    else:
        reference_dir = Path(reference_dir)

    if output_dir is None:
        output_dir = reference_dir
    else:
        output_dir = Path(output_dir)

    if not reference_dir.exists():
        justsdk.print_error(
            f"Error: Reference directory '{reference_dir}' does not exist."
        )
        return False

    json_files = list(reference_dir.glob("*.json"))

    if not json_files:
        justsdk.print_warning("No JSON files found in the reference directory.")
        return True

    justsdk.print_info(f"Found {len(json_files)} JSON file(s) to process:")
    for file in json_files:
        print(f"  - {file.name}")

    success_count = 0

    for json_file in json_files:
        if process_file(json_file, output_dir, mode):
            success_count += 1

    justsdk.print_info(
        f"\nCompleted processing {success_count}/{len(json_files)} files successfully!"
    )
    return success_count == len(json_files)
