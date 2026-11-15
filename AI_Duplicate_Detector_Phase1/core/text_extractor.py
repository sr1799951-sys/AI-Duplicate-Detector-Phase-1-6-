
import os
import re

import pymupdf
from docx import Document


# =====================================================
# PDF EXTRACTION
# =====================================================

def extract_pdf_text(file_path):

    text_parts = []

    with pymupdf.open(file_path) as document:

        for page_number, page in enumerate(document, start=1):

            page_text = page.get_text(
                "text",
                sort=True
            )

            if page_text.strip():
                text_parts.append(page_text)

    return "\n\n".join(text_parts)


# =====================================================
# DOCX TABLE EXTRACTION
# =====================================================

def extract_table_text(table):

    parts = []

    for row in table.rows:

        cells = []

        seen_cells = set()

        for cell in row.cells:

            # Avoid repeating merged cells
            cell_id = id(cell._tc)

            if cell_id in seen_cells:
                continue

            seen_cells.add(cell_id)

            cell_parts = []

            for paragraph in cell.paragraphs:

                value = paragraph.text.strip()

                if value:
                    cell_parts.append(value)

            for nested_table in cell.tables:

                nested_text = extract_table_text(
                    nested_table
                )

                if nested_text:
                    cell_parts.append(nested_text)

            if cell_parts:
                cells.append(" ".join(cell_parts))

        if cells:
            parts.append(" | ".join(cells))

    return "\n".join(parts)


# =====================================================
# DOCX EXTRACTION
# =====================================================

def extract_docx_text(file_path):

    document = Document(file_path)

    text_parts = []

    # Main document paragraphs
    for paragraph in document.paragraphs:

        value = paragraph.text.strip()

        if value:
            text_parts.append(value)

    # Main document tables
    for table in document.tables:

        value = extract_table_text(table)

        if value:
            text_parts.append(value)

    # Headers and footers
    seen_sections = set()

    for section in document.sections:

        for container in (
            section.header,
            section.footer
        ):

            element_id = id(container._element)

            if element_id in seen_sections:
                continue

            seen_sections.add(element_id)

            for paragraph in container.paragraphs:

                value = paragraph.text.strip()

                if value:
                    text_parts.append(value)

            for table in container.tables:

                value = extract_table_text(table)

                if value:
                    text_parts.append(value)

    return "\n\n".join(text_parts)


# =====================================================
# GENERAL DOCUMENT EXTRACTION
# =====================================================

def extract_document_text(file_path):

    extension = os.path.splitext(
        file_path
    )[1].lower()

    if extension == ".pdf":

        return extract_pdf_text(file_path)

    elif extension == ".docx":

        return extract_docx_text(file_path)

    elif extension in (".txt", ".md"):

        with open(file_path, "rb") as file:
            raw_data = file.read()

        for encoding in (
            "utf-8-sig",
            "utf-8",
            "cp1252",
            "latin-1"
        ):

            try:
                return raw_data.decode(encoding)

            except UnicodeDecodeError:
                continue

        raise UnicodeError(
            "Unable to decode document."
        )

    else:

        raise ValueError(
            f"Unsupported file format: {extension}"
        )


# =====================================================
# PASSAGE SEGMENTATION
# =====================================================

def split_into_passages(
    text,
    min_chars=20,
    max_chars=600,
    max_passages=300
):

    if not text:
        return []

    # Normalize line endings
    text = text.replace("\r\n", "\n")
    text = text.replace("\r", "\n")

    # Join ordinary line breaks.
    # Keep blank lines as paragraph boundaries.
    text = re.sub(
        r"(?<!\n)\n(?!\n)",
        " ",
        text
    )

    blocks = re.split(
        r"\n\s*\n+",
        text
    )

    passages = []

    def save_passage(value):

        value = re.sub(
            r"\s+",
            " ",
            value
        ).strip()

        if (
            len(value) >= min_chars
            and len(value.split()) >= 3
        ):
            passages.append(value)

    for block in blocks:

        if len(passages) >= max_passages:
            break

        block = re.sub(
            r"\s+",
            " ",
            block
        ).strip()

        if not block:
            continue

        sentences = re.split(
            r"(?<=[.!?])\s+",
            block
        )

        current = ""

        for sentence in sentences:

            sentence = sentence.strip()

            if not sentence:
                continue

            # Split extremely long sentences.
            if len(sentence) > max_chars:

                if current:
                    save_passage(current)
                    current = ""

                words = sentence.split()

                chunk = ""

                for word in words:

                    candidate = (
                        chunk + " " + word
                    ).strip()

                    if (
                        len(candidate) > max_chars
                        and chunk
                    ):

                        save_passage(chunk)
                        chunk = word

                    else:
                        chunk = candidate

                if chunk:
                    current = chunk

                continue

            candidate = (
                current + " " + sentence
            ).strip()

            if (
                len(candidate) > max_chars
                and current
            ):

                save_passage(current)
                current = sentence

            else:

                current = candidate

        if current:
            save_passage(current)

    return passages[:max_passages]


# =====================================================
# TEXT NORMALIZATION
# =====================================================

def normalize_passage(text):

    text = text.casefold()

    words = re.findall(
        r"\w+",
        text,
        flags=re.UNICODE
    )

    return " ".join(words)
