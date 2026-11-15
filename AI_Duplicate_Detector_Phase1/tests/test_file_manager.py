
import hashlib
import tempfile
from pathlib import Path

from AI_Duplicate_Detector_Phase1.core.file_manager import (
    calculate_sha256,
    move_exact_duplicates_to_recycle_bin,
    FileSafetyError,
)


def run_test():
    with tempfile.TemporaryDirectory() as temp_dir:
        folder = Path(temp_dir)

        # Create two files with identical content.
        original = folder / "original.txt"
        duplicate = folder / "duplicate.txt"

        content = "This is a genuine duplicate file test.\n" * 100

        original.write_text(content, encoding="utf-8")
        duplicate.write_text(content, encoding="utf-8")

        expected_hash = hashlib.sha256(
            original.read_bytes()
        ).hexdigest()
        print("Expected hash:", expected_hash)
        print("Original hash:", calculate_sha256(str(original)))
        print("Duplicate hash:", calculate_sha256(str(duplicate)))

        print("TEST 1: SHA-256 verification")

        assert calculate_sha256(str(original)) == expected_hash
        assert calculate_sha256(str(duplicate)) == expected_hash

        print("PASSED: Both files have matching SHA-256 hashes.")

        print("\nTEST 2: Safe duplicate removal")

        result = move_exact_duplicates_to_recycle_bin(
            keep_path=str(original),
            remove_paths=[str(duplicate)],
            expected_sha256=expected_hash,
        )

        assert result.success, result.message
        assert original.exists(), "Original file was not retained."
        assert original.read_text(encoding="utf-8") == content
        assert not duplicate.exists(), "Duplicate was not moved."

        print("PASSED: Original file was retained.")
        print("PASSED: Duplicate was moved to the Recycle Bin.")
        print(f"Recovered bytes: {result.recovered_bytes}")

        print("\nALL TESTS PASSED!")


if __name__ == "__main__":
    run_test()
