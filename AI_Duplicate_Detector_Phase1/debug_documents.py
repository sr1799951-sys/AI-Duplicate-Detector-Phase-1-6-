
from pathlib import Path

from PySide6.QtWidgets import QApplication, QFileDialog

from core.text_extractor import (
    extract_document_text,
    split_into_passages
)

app = QApplication([])

folder = QFileDialog.getExistingDirectory(
    None,
    "Select Your Scanner Test Folder"
)

if not folder:
    print("No folder selected.")
    raise SystemExit

folder = Path(folder)

supported = {".pdf", ".docx", ".txt", ".md"}

files = [
    path for path in folder.rglob("*")
    if path.is_file()
]

print("\nSelected folder:", folder)
print("Total files found:", len(files))

documents = [
    path for path in files
    if path.suffix.lower() in supported
]

print("Supported documents:", len(documents))

print("\n========== EXTRACTION RESULTS ==========")

for file_path in documents:

    print("\n" + "=" * 60)
    print("FILE:", file_path.name)
    print("TYPE:", file_path.suffix)

    try:

        text = extract_document_text(str(file_path))

        passages = split_into_passages(text)

        print("STATUS: SUCCESS")
        print("CHARACTERS:", len(text))
        print("PASSAGES:", len(passages))

        print("\nTEXT PREVIEW:")
        print(text[:300])

    except Exception as error:

        print("STATUS: FAILED")
        print("ERROR:", repr(error))

print("\n========== TEST COMPLETED ==========")
