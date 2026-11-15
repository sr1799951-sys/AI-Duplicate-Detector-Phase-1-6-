
import os
from dataclasses import dataclass
from datetime import datetime

from PySide6.QtCore import QThread, Signal


# Supported document extensions
SUPPORTED_EXTENSIONS = {
    ".pdf",
    ".docx",
    ".txt",
    ".md"
}


# Common Windows system directories
SYSTEM_DIRECTORY_NAMES = {
    "windows",
    "program files",
    "program files (x86)",
    "programdata",
    "system volume information",
    "$recycle.bin",
    "recovery",
    "perflogs"
}


@dataclass
class FileRecord:
    name: str
    path: str
    extension: str
    size_bytes: int
    modified_time: str


class FileScannerWorker(QThread):

    # files found, directories visited, current location
    progress_changed = Signal(int, int, str)

    # Final scanning information
    scan_completed = Signal(dict)

    def __init__(
        self,
        folders,
        extensions=None,
        skip_hidden=True
    ):
        super().__init__()

        self.folders = folders

        self.extensions = (
            extensions
            if extensions is not None
            else SUPPORTED_EXTENSIONS
        )

        self.extensions = {
            ext.lower() for ext in self.extensions
        }

        self.skip_hidden = skip_hidden

    def is_hidden_or_system(self, entry, stat_result):

        if not self.skip_hidden:
            return False

        # Hidden files and folders on Windows
        attributes = getattr(
            stat_result,
            "st_file_attributes",
            0
        )

        hidden_attribute = bool(attributes & 0x2)
        system_attribute = bool(attributes & 0x4)

        # Also skip dot-prefixed items
        hidden_name = entry.name.startswith(".")

        return (
            hidden_attribute
            or system_attribute
            or hidden_name
        )

    def run(self):

        records = []

        visited_directories = set()
        visited_files = set()

        directory_count = 0
        error_count = 0
        cancelled = False

        for selected_folder in self.folders:

            if self.isInterruptionRequested():
                cancelled = True
                break

            root = os.path.abspath(selected_folder)

            if not os.path.isdir(root):
                error_count += 1
                continue

            pending_directories = [root]

            while pending_directories:

                if self.isInterruptionRequested():
                    cancelled = True
                    break

                current_directory = (
                    pending_directories.pop()
                )

                normalized_directory = os.path.normcase(
                    os.path.abspath(current_directory)
                )

                if normalized_directory in visited_directories:
                    continue

                visited_directories.add(
                    normalized_directory
                )

                directory_count += 1

                try:

                    with os.scandir(current_directory) as entries:

                        for entry in entries:

                            if self.isInterruptionRequested():
                                cancelled = True
                                break

                            try:

                                stat_result = entry.stat(
                                    follow_symlinks=False
                                )

                                if self.is_hidden_or_system(
                                    entry,
                                    stat_result
                                ):
                                    continue

                                # Check directories
                                if entry.is_dir(
                                    follow_symlinks=False
                                ):

                                    if entry.name.lower() in SYSTEM_DIRECTORY_NAMES:
                                        continue

                                    pending_directories.append(
                                        entry.path
                                    )

                                    continue

                                # Check files
                                if not entry.is_file(
                                    follow_symlinks=False
                                ):
                                    continue

                                extension = os.path.splitext(
                                    entry.name
                                )[1].lower()

                                if extension not in self.extensions:
                                    continue

                                normalized_file = os.path.normcase(
                                    os.path.abspath(entry.path)
                                )

                                if normalized_file in visited_files:
                                    continue

                                visited_files.add(
                                    normalized_file
                                )

                                modified = datetime.fromtimestamp(
                                    stat_result.st_mtime
                                ).strftime(
                                    "%Y-%m-%d %H:%M:%S"
                                )

                                record = FileRecord(
                                    name=entry.name,
                                    path=os.path.abspath(entry.path),
                                    extension=extension,
                                    size_bytes=stat_result.st_size,
                                    modified_time=modified
                                )

                                records.append(record)

                                # Send periodic progress updates
                                if len(records) % 20 == 0:
                                    self.progress_changed.emit(
                                        len(records),
                                        directory_count,
                                        entry.path
                                    )

                            except OSError:
                                error_count += 1
                                continue

                            except Exception:
                                error_count += 1
                                continue

                            if cancelled:
                                break

                except OSError:
                    # Permission denied or inaccessible folder
                    error_count += 1
                    continue

                self.progress_changed.emit(
                    len(records),
                    directory_count,
                    current_directory
                )

                if cancelled:
                    break

            if cancelled:
                break

        # Sort files alphabetically
        records.sort(
            key=lambda item: item.name.lower()
        )

        self.progress_changed.emit(
            len(records),
            directory_count,
            "Scan finished"
        )

        self.scan_completed.emit({
            "files": records,
            "directories": directory_count,
            "errors": error_count,
            "cancelled": cancelled
        })
