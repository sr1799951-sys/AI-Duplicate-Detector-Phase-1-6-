
import json
import os
import tempfile

from datetime import datetime
from pathlib import Path


class StatisticsManager:
    """Stores and calculates persistent application statistics."""

    def __init__(self):
        self.data_directory = (
            Path.home() / ".ai_duplicate_detector"
        )

        self.data_file = (
            self.data_directory / "statistics.json"
        )

        self.data_directory.mkdir(
            parents=True,
            exist_ok=True
        )

        self.data = self.load_data()

    def load_data(self):
        """Load saved statistics, or create an empty history."""

        default_data = {
            "total_storage_recovered_bytes": 0,
            "scan_history": []
        }

        if not self.data_file.exists():
            return default_data

        try:
            with self.data_file.open(
                "r",
                encoding="utf-8"
            ) as file:
                data = json.load(file)

            if not isinstance(data, dict):
                return default_data

            history = data.get("scan_history", [])

            if not isinstance(history, list):
                history = []

            recovered = data.get(
                "total_storage_recovered_bytes",
                0
            )

            if not isinstance(recovered, int) or recovered < 0:
                recovered = 0

            return {
                "total_storage_recovered_bytes": recovered,
                "scan_history": history
            }

        except (OSError, json.JSONDecodeError):
            return default_data

    def save_data(self):
        """Save statistics safely using an atomic file replacement."""

        self.data_directory.mkdir(
            parents=True,
            exist_ok=True
        )

        temporary_path = None

        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.data_directory,
                suffix=".tmp",
                delete=False
            ) as file:

                json.dump(
                    self.data,
                    file,
                    indent=4
                )

                temporary_path = file.name

            os.replace(
                temporary_path,
                self.data_file
            )

        except OSError:
            if temporary_path and os.path.exists(temporary_path):
                os.remove(temporary_path)

            raise

    def record_scan(self, report, files_scanned):
        """Record one completed analysis."""

        exact = report.get("exact", {})
        partial = report.get("partial", {})
        semantic = report.get("semantic", {})

        groups = exact.get("duplicate_groups", [])

        exact_duplicate_files = sum(
            len(group.get("files", []))
            for group in groups
        )

        potential_bytes = sum(
            max(0, len(group.get("files", [])) - 1)
            * group["files"][0].size_bytes
            for group in groups
            if group.get("files")
        )

        entry = {
            "timestamp": datetime.now().astimezone().isoformat(
                timespec="seconds"
            ),
            "files_scanned": int(files_scanned),
            "exact_groups": len(groups),
            "exact_duplicate_files": exact_duplicate_files,
            "potential_recoverable_bytes": potential_bytes,
            "partial_matches": len(
                partial.get("matches", [])
            ),
            "semantic_matches": len(
                semantic.get("matches", [])
            ),
            "cancelled": any([
                exact.get("cancelled", False),
                partial.get("cancelled", False),
                semantic.get("cancelled", False)
            ])
        }

        self.data["scan_history"].append(entry)

        self.save_data()

        return entry

    def record_recovered_storage(self, recovered_bytes):
        """Record bytes successfully moved to the Recycle Bin."""

        recovered_bytes = int(recovered_bytes)

        if recovered_bytes <= 0:
            return

        self.data["total_storage_recovered_bytes"] += (
            recovered_bytes
        )

        self.save_data()

    def get_summary(self):
        """Calculate totals from saved scan history."""

        history = self.data["scan_history"]

        return {
            "total_scans": len(history),

            "total_files_scanned": sum(
                item.get("files_scanned", 0)
                for item in history
            ),

            "exact_groups": sum(
                item.get("exact_groups", 0)
                for item in history
            ),

            "exact_duplicate_files": sum(
                item.get("exact_duplicate_files", 0)
                for item in history
            ),

            "partial_matches": sum(
                item.get("partial_matches", 0)
                for item in history
            ),

            "semantic_matches": sum(
                item.get("semantic_matches", 0)
                for item in history
            ),

            "potential_recoverable_bytes": sum(
                item.get("potential_recoverable_bytes", 0)
                for item in history
            ),

            "storage_recovered_bytes": (
                self.data["total_storage_recovered_bytes"]
            )
        }
