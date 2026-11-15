
import os
import hashlib
from collections import defaultdict

from PySide6.QtCore import QThread, Signal


class HashDetectorWorker(QThread):

    progress_changed = Signal(int, int, str)
    detection_completed = Signal(dict)

    def __init__(self, records):
        super().__init__()
        self.records = records

    def calculate_sha256(self, file_path):

        sha256 = hashlib.sha256()

        with open(file_path, "rb") as file:

            initial_stat = os.fstat(file.fileno())

            while True:

                # Allow cancellation even during large file hashing
                if self.isInterruptionRequested():
                    return None

                chunk = file.read(1024 * 1024)

                if not chunk:
                    break

                sha256.update(chunk)

            final_stat = os.fstat(file.fileno())

            # Avoid using a hash if the file changed during reading
            if (
                initial_stat.st_size != final_stat.st_size
                or initial_stat.st_mtime_ns != final_stat.st_mtime_ns
            ):
                raise OSError("File changed while hashing")

        return sha256.hexdigest()

    def run(self):

        # Stage 1: Group files according to size
        size_groups = defaultdict(list)

        for record in self.records:
            size_groups[record.size_bytes].append(record)

        # Stage 2: Only files sharing a size are candidates
        candidates = []

        for group in size_groups.values():

            if len(group) > 1:
                candidates.extend(group)

        total = len(candidates)

        processed = 0
        hashed_files = 0
        errors = 0
        cancelled = False

        hash_groups = defaultdict(list)

        # Stage 3: Calculate SHA-256 hashes
        for record in candidates:

            if self.isInterruptionRequested():
                cancelled = True
                break

            try:

                digest = self.calculate_sha256(record.path)

                if digest is None:
                    cancelled = True
                    break

                hash_groups[digest].append(record)
                hashed_files += 1

            except OSError:
                errors += 1

            except Exception:
                errors += 1

            processed += 1

            self.progress_changed.emit(
                processed,
                total,
                record.path
            )

        # Stage 4: Keep only files with identical hashes
        duplicate_groups = []

        for digest, files in hash_groups.items():

            if len(files) > 1:

                files.sort(
                    key=lambda item: item.path.lower()
                )

                duplicate_groups.append({
                    "digest": digest,
                    "files": files
                })

        duplicate_groups.sort(
            key=lambda group: group["files"][0].size_bytes,
            reverse=True
        )

        # Stage 5: Return detection report
        self.detection_completed.emit({
            "duplicate_groups": duplicate_groups,
            "candidate_files": total,
            "files_hashed": hashed_files,
            "files_processed": processed,
            "errors": errors,
            "cancelled": cancelled
        })
