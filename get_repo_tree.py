import os
from pathlib import Path


def generate_tree(
        start_path: str = '.',
        ignore_dirs: list = None,
        ignore_extensions_in_data: list = None
):
    """
    Generates a visual file tree of the directory structure.

    Args:
        start_path: The root directory to start from.
        ignore_dirs: List of directory names to skip entirely.
        ignore_extensions_in_data: List of extensions to hide specifically within the 'data' folder.
    """
    if ignore_dirs is None:
        ignore_dirs = ['.git', '__pycache__', '.idea', '.vscode', 'venv', 'env', '.venv', 'build', 'dist']

    if ignore_extensions_in_data is None:
        ignore_extensions_in_data = ['.csv']

    start_path = Path(start_path)
    print(f"📁 {start_path.resolve().name}")

    # Walk the tree
    _print_tree(start_path, "", ignore_dirs, ignore_extensions_in_data)


def _print_tree(current_path: Path, prefix: str, ignore_dirs: list, ignore_extensions_in_data: list):
    # Get all items in directory, sorted for consistent output
    try:
        items = sorted(list(current_path.iterdir()))
    except PermissionError:
        return

    # Filter out ignored directories immediately
    items = [item for item in items if item.name not in ignore_dirs]

    # Filter out specific files (CSVs in data folder)
    filtered_items = []
    for item in items:
        # Check if we are currently inside a 'data' folder (or subfolder of data)
        is_in_data = 'data' in item.parts

        if is_in_data and item.is_file() and item.suffix.lower() in ignore_extensions_in_data:
            continue
        filtered_items.append(item)

    count = len(filtered_items)

    for index, item in enumerate(filtered_items):
        connector = "└── " if index == count - 1 else "├── "

        if item.is_dir():
            print(f"{prefix}{connector}📂 {item.name}")
            # Prepare prefix for children
            new_prefix = prefix + ("    " if index == count - 1 else "│   ")
            _print_tree(item, new_prefix, ignore_dirs, ignore_extensions_in_data)
        else:
            print(f"{prefix}{connector}📄 {item.name}")


if __name__ == "__main__":
    # Generate tree for current directory
    generate_tree()