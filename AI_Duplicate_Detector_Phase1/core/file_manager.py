
"""
Safe duplicate file management.

Exact duplicate files are verified using SHA-256 before being moved
to the Windows Recycle Bin. Files are never permanently deleted here.
"""

import hashlib
import os
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import List

CHUNK_SIZE = 1024 * 1024  # 1 MB


class FileSafetyError(Exception):
    """Raised when a file fails a safety verification."""


@dataclass
class FileOperationResult:
    success: bool
    kept_path: str
    moved_paths: List[str]
    failed_paths: List[str]
    recovered_bytes: int
    message: str


def calculate_sha256(file_path: str) -> str:
    """Calculate SHA-256 while checking that the file stays unchanged."""

    path = Path(file_path)

    if not path.exists() or not path.is_file():
        raise FileSafetyError(f"File does not exist or is not a regular file: {path}")

    if path.is_symlink():
        raise FileSafetyError(f"Symbolic links are not allowed: {path}")

    try:
        before = path.stat()
        digest = hashlib.sha256()

        with path.open("rb") as file:
            opened = os.fstat(file.fileno())

            if not stat.S_ISREG(opened.st_mode):
                raise FileSafetyError(f"Not a regular file: {path}")

            while True:
                chunk = file.read(CHUNK_SIZE)
                if not chunk:
                    break
                digest.update(chunk)

            after_open = os.fstat(file.fileno())

        after_path = path.stat()

        if (
            before.st_size != after_open.st_size
            or before.st_mtime_ns != after_open.st_mtime_ns
            or before.st_size != after_path.st_size
            or before.st_mtime_ns != after_path.st_mtime_ns
        ):
            raise FileSafetyError(f"File changed during verification: {path}")

        return digest.hexdigest()

    except OSError as error:
        raise FileSafetyError(f"Cannot read file {path}: {error}") from error


def _is_reparse_point(path: Path) -> bool:
    """Reject Windows junctions and other reparse points."""

    try:
        attributes = getattr(os.stat(path, follow_symlinks=False), "st_file_attributes", 0)
        reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
        return bool(attributes & reparse_flag)
    except OSError as error:
        raise FileSafetyError(f"Cannot inspect file: {path}: {error}") from error


def move_exact_duplicates_to_recycle_bin(
    keep_path: str,
    remove_paths: List[str],
    expected_sha256: str,
) -> FileOperationResult:
    """
    Verify an exact duplicate group and move selected copies to Recycle Bin.

    The caller must supply the SHA-256 digest recorded by the scanner.
    At least one original copy is always retained.
    """

    keep = Path(keep_path).resolve(strict=True)
    selected = [Path(item).resolve(strict=True) for item in remove_paths]

    if not expected_sha256 or len(expected_sha256) != 64:
        raise FileSafetyError("A valid SHA-256 digest is required.")

    if not selected:
        raise FileSafetyError("No files were selected for removal.")

    all_paths = [keep] + selected
    normalized = [os.path.normcase(str(path)) for path in all_paths]

    if len(normalized) != len(set(normalized)):
        raise FileSafetyError("The same file cannot be selected more than once.")

    for path in all_paths:
        if not path.is_file():
            raise FileSafetyError(f"Not a regular file: {path}")

        if path.is_symlink() or _is_reparse_point(path):
            raise FileSafetyError(f"Links and reparse points cannot be managed: {path}")

    # Verify the retained copy first.
    keep_digest = calculate_sha256(str(keep))

    if keep_digest.lower() != expected_sha256.lower():
        raise FileSafetyError(
            "The file selected to keep has changed since the scan. Scan again."
        )

    # Verify every selected copy BEFORE moving any of them.
    verified_sizes = []

    for path in selected:
        digest = calculate_sha256(str(path))

        if digest.lower() != expected_sha256.lower():
            raise FileSafetyError(
                f"Selected file is no longer an exact duplicate: {path}"
            )

        verified_sizes.append(path.stat().st_size)

    # Recheck that the retained copy still exists and matches.
    if not keep.exists() or calculate_sha256(str(keep)).lower() != expected_sha256.lower():
        raise FileSafetyError("The retained copy changed during the operation.")

    # No permanent-delete fallback is allowed.
    try:
        from send2trash import send2trash
    except ImportError as error:
        raise FileSafetyError(
            "The send2trash package is missing. Install it using: "
            "pip install send2trash"
        ) from error

    moved = []
    failed = []
    recovered_bytes = 0

    for path, size in zip(selected, verified_sizes):
        try:
            # Verify once more immediately before moving this file.
            if not path.exists():
                raise FileSafetyError("File disappeared before it could be moved.")

            if calculate_sha256(str(path)).lower() != expected_sha256.lower():
                raise FileSafetyError("File changed immediately before removal.")

            send2trash(str(path))
            moved.append(str(path))
            recovered_bytes += size

        except Exception as error:
            failed.append(f"{path}: {error}")

    success = len(moved) == len(selected)

    if success:
        message = "Selected duplicate copies were moved to the Recycle Bin."
    else:
        message = (
            "The operation was partially completed. Check the failed files "
            "and the Recycle Bin before trying again."
        )

    return FileOperationResult(
        success=success,
        kept_path=str(keep),
        moved_paths=moved,
        failed_paths=failed,
        recovered_bytes=recovered_bytes,
        message=message,
    )
