
import os
import numpy as np

from PySide6.QtCore import QThread, Signal

from core.text_extractor import (
    extract_document_text,
    split_into_passages
)


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

MIN_PASSAGE_CHARS = 50
MIN_PASSAGE_WORDS = 8


class SemanticDuplicateWorker(QThread):

    progress_changed = Signal(int, int, str)
    detection_completed = Signal(dict)

    def __init__(
        self,
        records,
        threshold=70,
        excluded_pairs=None
    ):
        super().__init__()

        self.records = records

        self.threshold = max(
            0,
            min(100, int(threshold))
        )

        self.excluded_pairs = excluded_pairs or set()

    # -------------------------------------------------
    # FILE PAIR NORMALIZATION
    # -------------------------------------------------

    @staticmethod
    def path_pair(path_a, path_b):

        path_a = os.path.normcase(
            os.path.abspath(path_a)
        )

        path_b = os.path.normcase(
            os.path.abspath(path_b)
        )

        return tuple(sorted((path_a, path_b)))

    # -------------------------------------------------
    # FILTER PASSAGES
    # -------------------------------------------------

    @staticmethod
    def prepare_passages(passages):

        valid = []

        for index, passage in enumerate(passages):

            clean_text = " ".join(
                passage.split()
            )

            word_count = len(
                clean_text.split()
            )

            if len(clean_text) < MIN_PASSAGE_CHARS:
                continue

            if word_count < MIN_PASSAGE_WORDS:
                continue

            valid.append({
                "original_index": index,
                "text": clean_text
            })

        return valid

    # -------------------------------------------------
    # COSINE SIMILARITY MATCHING
    # -------------------------------------------------

    def compare_document_embeddings(
        self,
        embeddings_a,
        embeddings_b,
        passages_a,
        passages_b
    ):

        # Embeddings are normalized, so their
        # dot product equals cosine similarity.
        similarity_matrix = np.matmul(
            embeddings_a,
            embeddings_b.T
        )

        candidates = {}

        threshold_value = self.threshold / 100.0

        # Compare each passage in A with its best B.
        for index_a in range(
            similarity_matrix.shape[0]
        ):

            if self.isInterruptionRequested():
                return []

            index_b = int(
                np.argmax(similarity_matrix[index_a])
            )

            score = float(
                similarity_matrix[index_a, index_b]
            )

            if score >= threshold_value:

                candidates[(index_a, index_b)] = score

        # Reverse comparison.
        for index_b in range(
            similarity_matrix.shape[1]
        ):

            if self.isInterruptionRequested():
                return []

            index_a = int(
                np.argmax(similarity_matrix[:, index_b])
            )

            score = float(
                similarity_matrix[index_a, index_b]
            )

            if score >= threshold_value:

                key = (index_a, index_b)

                candidates[key] = max(
                    candidates.get(key, 0),
                    score
                )

        # Select unique one-to-one passage matches.
        ordered = sorted(
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

        for score, index_a, index_b in ordered:

            if index_a in used_a:
                continue

            if index_b in used_b:
                continue

            used_a.add(index_a)
            used_b.add(index_b)

            original_a = passages_a[index_a]
            original_b = passages_b[index_b]

            matches.append({

                "text_a": original_a["text"],

                "text_b": original_b["text"],

                "score": round(
                    max(0.0, min(1.0, score)) * 100,
                    2
                )

            })

        return matches

    # -------------------------------------------------
    # CREATE REPORT
    # -------------------------------------------------

    def create_report(
        self,
        matches=None,
        extracted=0,
        without_text=0,
        pairs=0,
        errors=0,
        cancelled=False,
        error=None
    ):

        return {

            "matches": matches or [],

            "documents_extracted": extracted,

            "documents_without_text": without_text,

            "document_pairs_checked": pairs,

            "errors": errors,

            "threshold": self.threshold,

            "cancelled": cancelled,

            "error": error,

            "model": MODEL_NAME

        }

    # -------------------------------------------------
    # MAIN WORKER
    # -------------------------------------------------

    def run(self):

        documents = []

        all_passages = []

        extraction_errors = 0
        documents_without_text = 0

        total_documents = len(self.records)

        cancelled = False

        # =============================================
        # STEP 1: EXTRACT DOCUMENT TEXT
        # =============================================

        for index, record in enumerate(self.records):

            if self.isInterruptionRequested():

                cancelled = True
                break

            try:

                text = extract_document_text(
                    record.path
                )

                passages = split_into_passages(text)

                prepared = self.prepare_passages(
                    passages
                )

                if not prepared:

                    documents_without_text += 1

                else:

                    start = len(all_passages)

                    all_passages.extend(
                        item["text"]
                        for item in prepared
                    )

                    end = len(all_passages)

                    documents.append({

                        "record": record,

                        "passages": prepared,

                        "start": start,

                        "end": end

                    })

            except Exception:

                extraction_errors += 1

            self.progress_changed.emit(
                index + 1,
                max(total_documents, 1),
                f"Preparing semantic analysis: {record.name}"
            )

        if cancelled:

            self.detection_completed.emit(
                self.create_report(
                    extracted=len(documents),
                    without_text=documents_without_text,
                    errors=extraction_errors,
                    cancelled=True
                )
            )

            return

        # =============================================
        # STEP 2: CHECK WHETHER COMPARISON IS POSSIBLE
        # =============================================

        total_pairs = (
            len(documents)
            * (len(documents) - 1)
            // 2
        )

        if len(documents) < 2 or not all_passages:

            self.detection_completed.emit(
                self.create_report(
                    extracted=len(documents),
                    without_text=documents_without_text,
                    errors=extraction_errors
                )
            )

            return

        # =============================================
        # STEP 3: LOAD LOCAL AI MODEL
        # =============================================

        self.progress_changed.emit(
            0,
            1,
            "Loading AI model. First launch may download model files..."
        )

        try:

            from sentence_transformers import SentenceTransformer

            model = SentenceTransformer(
                MODEL_NAME,
                device="cpu"
            )

        except Exception as error:

            self.detection_completed.emit(
                self.create_report(
                    extracted=len(documents),
                    without_text=documents_without_text,
                    errors=extraction_errors,
                    error=f"Unable to load AI model: {error}"
                )
            )

            return

        if self.isInterruptionRequested():

            self.detection_completed.emit(
                self.create_report(
                    extracted=len(documents),
                    without_text=documents_without_text,
                    errors=extraction_errors,
                    cancelled=True
                )
            )

            return

        # =============================================
        # STEP 4: GENERATE PASSAGE EMBEDDINGS
        # =============================================

        try:

            self.progress_changed.emit(
                0,
                len(all_passages),
                f"Generating embeddings for {len(all_passages)} passages..."
            )

            embeddings = model.encode(
                all_passages,
                batch_size=32,
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=True
            )

        except Exception as error:

            self.detection_completed.emit(
                self.create_report(
                    extracted=len(documents),
                    without_text=documents_without_text,
                    errors=extraction_errors,
                    error=f"Embedding generation failed: {error}"
                )
            )

            return

        if self.isInterruptionRequested():

            self.detection_completed.emit(
                self.create_report(
                    extracted=len(documents),
                    without_text=documents_without_text,
                    errors=extraction_errors,
                    cancelled=True
                )
            )

            return

        # =============================================
        # STEP 5: COMPARE DOCUMENT PAIRS
        # =============================================

        matches = []

        comparisons_checked = 0

        for i in range(len(documents)):

            for j in range(i + 1, len(documents)):

                if self.isInterruptionRequested():

                    cancelled = True
                    break

                doc_a = documents[i]
                doc_b = documents[j]

                record_a = doc_a["record"]
                record_b = doc_b["record"]

                pair = self.path_pair(
                    record_a.path,
                    record_b.path
                )

                comparisons_checked += 1

                # Skip exact duplicate pairs.
                if pair in self.excluded_pairs:

                    continue

                embeddings_a = embeddings[
                    doc_a["start"]:doc_a["end"]
                ]

                embeddings_b = embeddings[
                    doc_b["start"]:doc_b["end"]
                ]

                passage_matches = self.compare_document_embeddings(
                    embeddings_a,
                    embeddings_b,
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
                    f"AI comparing: {record_a.name} and {record_b.name}"
                )

            if cancelled:
                break

        # =============================================
        # STEP 6: SORT RESULTS
        # =============================================

        matches.sort(
            key=lambda item: item["similarity"],
            reverse=True
        )

        # =============================================
        # STEP 7: RETURN REPORT
        # =============================================

        self.detection_completed.emit(
            self.create_report(
                matches=matches,
                extracted=len(documents),
                without_text=documents_without_text,
                pairs=comparisons_checked,
                errors=extraction_errors,
                cancelled=cancelled
            )
        )
