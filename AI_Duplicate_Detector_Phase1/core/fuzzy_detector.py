
import os

from PySide6.QtCore import QThread, Signal
from rapidfuzz import fuzz, process

from core.text_extractor import (
    extract_document_text,
    split_into_passages,
    normalize_passage
)


# Minimum passage requirements.
MIN_PASSAGE_CHARS = 80
MIN_PASSAGE_WORDS = 10


class FuzzyDuplicateWorker(QThread):

    progress_changed = Signal(int, int, str)
    detection_completed = Signal(dict)

    def __init__(
        self,
        records,
        threshold=85,
        excluded_pairs=None
    ):
        super().__init__()

        self.records = records

        self.threshold = max(
            0,
            min(100, int(threshold))
        )

        self.excluded_pairs = excluded_pairs or set()

    @staticmethod
    def path_pair(path_a, path_b):

        path_a = os.path.normcase(
            os.path.abspath(path_a)
        )

        path_b = os.path.normcase(
            os.path.abspath(path_b)
        )

        return tuple(sorted((path_a, path_b)))

    @staticmethod
    def prepare_passages(passages):

        valid_passages = []

        for index, original_text in enumerate(passages):

            normalized_text = normalize_passage(
                original_text
            )

            word_count = len(
                normalized_text.split()
            )

            if not normalized_text:
                continue

            if len(original_text.strip()) < MIN_PASSAGE_CHARS:
                continue

            if word_count < MIN_PASSAGE_WORDS:
                continue

            valid_passages.append((
                index,
                normalized_text
            ))

        return valid_passages

    # Improved passage comparison.
    # Token-set similarity handles reordered words and
    # passages containing additional words more effectively.
    def compare_passages(
        self,
        passages_a,
        passages_b
    ):

        valid_a = self.prepare_passages(
            passages_a
        )

        valid_b = self.prepare_passages(
            passages_b
        )

        if not valid_a or not valid_b:
            return []

        choices_a = [
            text for _, text in valid_a
        ]

        choices_b = [
            text for _, text in valid_b
        ]

        candidates = {}

        # Forward comparison
        for index_a, text_a in valid_a:

            if self.isInterruptionRequested():
                return []

            result = process.extractOne(
                text_a,
                choices_b,
                scorer=fuzz.token_set_ratio,
                processor=None,
                score_cutoff=self.threshold
            )

            if result:

                _, score, position = result

                index_b = valid_b[position][0]

                key = (index_a, index_b)

                candidates[key] = max(
                    candidates.get(key, 0),
                    float(score)
                )

        # Reverse comparison
        for index_b, text_b in valid_b:

            if self.isInterruptionRequested():
                return []

            result = process.extractOne(
                text_b,
                choices_a,
                scorer=fuzz.token_set_ratio,
                processor=None,
                score_cutoff=self.threshold
            )

            if result:

                _, score, position = result

                index_a = valid_a[position][0]

                key = (index_a, index_b)

                candidates[key] = max(
                    candidates.get(key, 0),
                    float(score)
                )

        # Select one-to-one passage matches
        ordered_candidates = sorted(
            [
                (score, index_a, index_b)
                for (index_a, index_b), score
                in candidates.items()
            ],
            reverse=True
        )

        used_a = set()
        used_b = set()

        matches = []

        for score, index_a, index_b in ordered_candidates:

            if index_a in used_a:
                continue

            if index_b in used_b:
                continue

            used_a.add(index_a)
            used_b.add(index_b)

            matches.append({

                "text_a": passages_a[index_a],

                "text_b": passages_b[index_b],

                "score": round(score, 2)

            })

        return matches

    def run(self):

        extracted_documents = []

        extraction_errors = 0
        documents_without_text = 0

        comparisons_checked = 0
        cancelled = False

        total_documents = len(self.records)

        # STEP 1: Extract document text
        for index, record in enumerate(self.records):

            if self.isInterruptionRequested():
                cancelled = True
                break

            try:

                text = extract_document_text(
                    record.path
                )

                passages = split_into_passages(text)

                if passages:

                    extracted_documents.append({

                        "record": record,

                        "passages": passages

                    })

                else:

                    documents_without_text += 1

            except Exception:

                extraction_errors += 1

            self.progress_changed.emit(
                index + 1,
                max(total_documents, 1),
                f"Extracting: {record.name}"
            )

        # STEP 2: Compare document pairs
        total_pairs = (
            len(extracted_documents)
            * (len(extracted_documents) - 1)
            // 2
        )

        matches = []

        if not cancelled:

            for i in range(len(extracted_documents)):

                for j in range(
                    i + 1,
                    len(extracted_documents)
                ):

                    if self.isInterruptionRequested():

                        cancelled = True
                        break

                    doc_a = extracted_documents[i]
                    doc_b = extracted_documents[j]

                    record_a = doc_a["record"]
                    record_b = doc_b["record"]

                    pair = self.path_pair(
                        record_a.path,
                        record_b.path
                    )

                    comparisons_checked += 1

                    # Skip exact duplicate pairs
                    if pair in self.excluded_pairs:

                        self.progress_changed.emit(
                            comparisons_checked,
                            max(total_pairs, 1),
                            "Skipping exact duplicate pair"
                        )

                        continue

                    passage_matches = self.compare_passages(
                        doc_a["passages"],
                        doc_b["passages"]
                    )

                    if self.isInterruptionRequested():

                        cancelled = True
                        break

                    if passage_matches:

                        average_score = sum(
                            item["score"]
                            for item in passage_matches
                        ) / len(passage_matches)

                        matches.append({

                            "file_a": record_a,

                            "file_b": record_b,

                            "similarity": round(
                                average_score,
                                2
                            ),

                            "passages": passage_matches

                        })

                    self.progress_changed.emit(
                        comparisons_checked,
                        max(total_pairs, 1),
                        f"Comparing: {record_a.name} and {record_b.name}"
                    )

                if cancelled:
                    break

        # STEP 3: Sort results
        matches.sort(
            key=lambda item: item["similarity"],
            reverse=True
        )

        # STEP 4: Return report
        self.detection_completed.emit({

            "matches": matches,

            "documents_extracted": len(
                extracted_documents
            ),

            "documents_without_text": documents_without_text,

            "document_pairs_checked": comparisons_checked,

            "errors": extraction_errors,

            "threshold": self.threshold,

            "cancelled": cancelled

        })
