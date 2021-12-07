"""Validation of the user provided input."""

from pathlib import Path


def check_directory_exists(mandatory_dir):
    """Makes sure the mandatory directory exists.
    Raises
    ------
    FileNotFoundError
        Raised when the directory is not found.
    """
    f_path = Path(mandatory_dir)
    if not f_path.is_dir():
        raise FileNotFoundError(f"No directory is found at: {str(f_path)}")