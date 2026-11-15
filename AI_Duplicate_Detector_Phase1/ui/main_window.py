
import os
import html

from PySide6.QtCore import Qt, QSettings, Signal, QThread
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QGridLayout,
    QLabel, QPushButton, QFrame, QStackedWidget, QFileDialog,
    QListWidget, QMessageBox, QSpinBox, QCheckBox, QProgressBar,
    QTableWidget, QTableWidgetItem, QHeaderView, QTabWidget,
    QDialog, QTextEdit, QDialogButtonBox
)

from core.scanner import FileScannerWorker
from core.hash_detector import HashDetectorWorker
from core.fuzzy_detector import FuzzyDuplicateWorker
from core.semantic_detector import SemanticDuplicateWorker
from core.file_manager import move_exact_duplicates_to_recycle_bin


# =====================================================
# APPLICATION STYLE
# =====================================================

STYLE = """
QMainWindow, QWidget {
    background-color: #0b1220;
    color: #e5e7eb;
    font-family: Segoe UI;
    font-size: 13px;
}
QWidget#Sidebar {
    background-color: #0a1020;
    border-right: 1px solid #1e293b;
}
QLabel#Brand { color: white; font-size: 19px; font-weight: bold; }
QLabel#PageTitle { color: white; font-size: 26px; font-weight: bold; }
QLabel#Section { color: white; font-size: 17px; font-weight: bold; }
QLabel#HeroTitle { color: white; font-size: 26px; font-weight: bold; }
QLabel#MetricValue { color: white; font-size: 27px; font-weight: bold; }
QLabel#Muted { color: #94a3b8; }
QFrame#Panel, QFrame#Metric, QFrame#Hero {
    background-color: #111c2e;
    border: 1px solid #26364d;
    border-radius: 13px;
}
QPushButton {
    background-color: #2563eb;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 10px 14px;
    font-weight: bold;
}
QPushButton:hover { background-color: #1d4ed8; }
QPushButton:disabled { background-color: #263449; color: #8290a5; }
QPushButton#Nav {
    background-color: transparent;
    color: #aab7ca;
    text-align: left;
    border: none;
}
QPushButton#Nav:hover { background-color: #172338; }
QPushButton#Nav[active="true"] { background-color: #1d3a68; color: white; }
QPushButton#Secondary { background-color: #172338; border: 1px solid #334155; }
QListWidget, QSpinBox, QTableWidget, QTextEdit {
    background-color: #0c1627;
    color: white;
    border: 1px solid #334155;
    border-radius: 7px;
    padding: 7px;
}
QHeaderView::section {
    background-color: #172338;
    color: #dbeafe;
    padding: 8px;
    border: none;
    font-weight: bold;
}
QCheckBox { color: #e5e7eb; spacing: 9px; }
QProgressBar {
    background-color: #0c1627;
    border: 1px solid #334155;
    border-radius: 6px;
    height: 12px;
    text-align: center;
}
QProgressBar::chunk { background-color: #2563eb; border-radius: 5px; }
QTabWidget::pane { border: 1px solid #26364d; border-radius: 8px; }
QTabBar::tab {
    background-color: #111c2e;
    color: #94a3b8;
    padding: 10px 16px;
    border: 1px solid #26364d;
}
QTabBar::tab:selected { background-color: #1d3a68; color: white; }
"""


def create_panel():
    panel = QFrame()
    panel.setObjectName("Panel")
    return panel


# =====================================================
# BACKGROUND FILE-MANAGEMENT WORKER
# =====================================================

class FileManagerWorker(QThread):
    """Perform safe duplicate-file management in a background thread."""

    operation_completed = Signal(object)
    operation_failed = Signal(str)

    def __init__(self, keep_path, remove_paths, expected_sha256):
        super().__init__()

        self.keep_path = keep_path
        self.remove_paths = remove_paths
        self.expected_sha256 = expected_sha256

    def run(self):
        try:
            result = move_exact_duplicates_to_recycle_bin(
                keep_path=self.keep_path,
                remove_paths=self.remove_paths,
                expected_sha256=self.expected_sha256
            )

            self.operation_completed.emit(result)

        except Exception as error:
            self.operation_failed.emit(str(error))


# =====================================================
# DASHBOARD
# =====================================================

class DashboardPage(QWidget):

    def __init__(self, go_to_scan):
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setSpacing(18)

        hero = QFrame()
        hero.setObjectName("Hero")
        hero_layout = QHBoxLayout(hero)
        text_layout = QVBoxLayout()

        eyebrow = QLabel("LOCAL DOCUMENT INTELLIGENCE")
        eyebrow.setObjectName("Muted")

        title = QLabel("Your files, less cluttered.")
        title.setObjectName("HeroTitle")

        description = QLabel(
            "Find identical copies, repeated passages, and documents "
            "with similar meanings."
        )
        description.setObjectName("Muted")
        description.setWordWrap(True)

        text_layout.addWidget(eyebrow)
        text_layout.addWidget(title)
        text_layout.addWidget(description)
        hero_layout.addLayout(text_layout, 1)

        scan_button = QPushButton("Choose folders")
        scan_button.clicked.connect(go_to_scan)
        hero_layout.addWidget(scan_button)
        layout.addWidget(hero)

        heading = QLabel("Workspace Overview")
        heading.setObjectName("Section")
        layout.addWidget(heading)

        grid = QGridLayout()
        grid.setSpacing(12)

        for index, (value, name) in enumerate([
            ("0", "FILES INDEXED"),
            ("0", "DUPLICATE GROUPS"),
            ("—", "SPACE REVIEWABLE")
        ]):
            card = QFrame()
            card.setObjectName("Metric")
            card_layout = QVBoxLayout(card)

            value_label = QLabel(value)
            value_label.setObjectName("MetricValue")

            name_label = QLabel(name)
            name_label.setObjectName("Muted")

            card_layout.addWidget(value_label)
            card_layout.addWidget(name_label)
            grid.addWidget(card, 0, index)

        layout.addLayout(grid)

        heading = QLabel("Detection Technology")
        heading.setObjectName("Section")
        layout.addWidget(heading)

        feature_layout = QHBoxLayout()

        features = [
            ("Exact Detection", "SHA-256 hashing", "PHASE 4"),
            ("Partial Detection", "RapidFuzz text matching", "PHASE 5"),
            ("Semantic Detection", "Sentence Transformers AI", "PHASE 6")
        ]

        for name, detail_text, phase in features:
            card = create_panel()
            card_layout = QVBoxLayout(card)

            feature_title = QLabel(name)
            feature_title.setObjectName("Section")

            detail = QLabel(detail_text)
            detail.setObjectName("Muted")
            detail.setWordWrap(True)

            phase_label = QLabel(phase)
            phase_label.setObjectName("Muted")

            card_layout.addWidget(feature_title)
            card_layout.addWidget(detail)
            card_layout.addStretch()
            card_layout.addWidget(phase_label)

            feature_layout.addWidget(card)

        layout.addLayout(feature_layout)

        privacy = QLabel(
            "Privacy first: document analysis runs locally on your computer."
        )
        privacy.setObjectName("Muted")
        layout.addWidget(privacy)
        layout.addStretch()


# =====================================================
# SCAN PAGE
# =====================================================

class ScanPage(QWidget):

    analysis_ready = Signal(dict)

    def __init__(self):
        super().__init__()

        self.folders = []
        self.records = []

        self.worker = None
        self.hash_worker = None
        self.fuzzy_worker = None
        self.semantic_worker = None

        self.exact_report = None
        self.partial_report = None

        self.settings = QSettings(
            "AI Duplicate Detector",
            "Desktop"
        )

        self.build_ui()

    def build_ui(self):

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel("File Scanner")
        title.setObjectName("Section")

        description = QLabel(
            "Discover PDF, DOCX, TXT and Markdown files, then detect "
            "exact, partial and semantic duplicates."
        )
        description.setObjectName("Muted")
        description.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(description)

        folder_heading = QLabel("Selected folders")
        folder_heading.setObjectName("Section")

        self.count_label = QLabel("0 folders selected")
        self.count_label.setObjectName("Muted")

        self.folder_list = QListWidget()
        self.folder_list.setMaximumHeight(115)

        folder_buttons = QHBoxLayout()

        self.add_button = QPushButton("Add folder")
        self.add_button.clicked.connect(self.add_folder)

        self.remove_button = QPushButton("Remove selected")
        self.remove_button.setObjectName("Secondary")
        self.remove_button.clicked.connect(self.remove_folder)

        self.clear_button = QPushButton("Clear all")
        self.clear_button.setObjectName("Secondary")
        self.clear_button.clicked.connect(self.clear_folders)

        folder_buttons.addWidget(self.add_button)
        folder_buttons.addWidget(self.remove_button)
        folder_buttons.addWidget(self.clear_button)
        folder_buttons.addStretch()

        layout.addWidget(folder_heading)
        layout.addWidget(self.count_label)
        layout.addWidget(self.folder_list)
        layout.addLayout(folder_buttons)

        controls = QHBoxLayout()

        self.scan_button = QPushButton("Start Scan")
        self.scan_button.clicked.connect(self.start_scan)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.setObjectName("Secondary")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_scan)

        controls.addWidget(self.scan_button)
        controls.addWidget(self.cancel_button)
        controls.addStretch()

        layout.addLayout(controls)

        self.status_label = QLabel("Ready to scan.")
        self.status_label.setObjectName("Muted")

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)

        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_bar)

        result_heading = QLabel("Discovered files")
        result_heading.setObjectName("Section")

        self.results_table = QTableWidget(0, 5)

        self.results_table.setHorizontalHeaderLabels([
            "File Name",
            "Type",
            "Size",
            "Modified",
            "Location"
        ])

        self.configure_table(self.results_table)

        layout.addWidget(result_heading)
        layout.addWidget(self.results_table, 1)

        note = QLabel(
            "All analysis runs locally. No files are modified or deleted "
            "during scanning."
        )
        note.setObjectName("Muted")
        layout.addWidget(note)

    @staticmethod
    def configure_table(table):

        table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )

        table.verticalHeader().setVisible(False)

        table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )

        table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )

        table.setAlternatingRowColors(True)

    # FOLDER SELECTION

    def add_folder(self):

        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Folder"
        )

        if not folder:
            return

        folder = os.path.abspath(folder)
        normalized = os.path.normcase(folder)

        existing = [
            os.path.normcase(os.path.abspath(path))
            for path in self.folders
        ]

        if normalized in existing:
            QMessageBox.information(
                self,
                "Already added",
                "This folder is already selected."
            )
            return

        self.folders.append(folder)
        self.folder_list.addItem(folder)
        self.update_count()

    def remove_folder(self):

        row = self.folder_list.currentRow()

        if row < 0:
            QMessageBox.information(
                self,
                "Select Folder",
                "Please select a folder first."
            )
            return

        self.folder_list.takeItem(row)
        self.folders.pop(row)
        self.update_count()

    def clear_folders(self):

        self.folders.clear()
        self.folder_list.clear()
        self.update_count()

    def update_count(self):

        count = len(self.folders)

        self.count_label.setText(
            f"{count} folder{'s' if count != 1 else ''} selected"
        )

    # SETTINGS AND THREAD STATE

    def setting_enabled(self, key, default=True):

        value = self.settings.value(key, default)

        if isinstance(value, bool):
            return value

        return str(value).lower() in (
            "true", "1", "yes", "on"
        )

    @staticmethod
    def worker_is_running(worker):

        return (
            worker is not None
            and worker.isRunning()
        )

    def any_worker_running(self):

        return any(
            self.worker_is_running(worker)
            for worker in (
                self.worker,
                self.hash_worker,
                self.fuzzy_worker,
                self.semantic_worker
            )
        )

    def set_controls_enabled(self, enabled):

        self.scan_button.setEnabled(enabled)
        self.add_button.setEnabled(enabled)
        self.remove_button.setEnabled(enabled)
        self.clear_button.setEnabled(enabled)

        self.cancel_button.setEnabled(not enabled)

    # START SCAN

    def start_scan(self):

        if self.any_worker_running():
            return

        if not self.folders:
            QMessageBox.warning(
                self,
                "No folders selected",
                "Please add at least one folder."
            )
            return

        extension_settings = {
            "pdf": ".pdf",
            "docx": ".docx",
            "txt": ".txt",
            "md": ".md"
        }

        selected_extensions = {
            extension
            for key, extension in extension_settings.items()
            if self.setting_enabled(key)
        }

        if not selected_extensions:
            QMessageBox.warning(
                self,
                "No document formats",
                "Enable at least one document format in Settings."
            )
            return

        self.records = []
        self.exact_report = None
        self.partial_report = None

        self.results_table.setRowCount(0)

        self.progress_bar.setRange(0, 0)
        self.status_label.setText("Scanning selected folders...")

        self.set_controls_enabled(False)

        self.worker = FileScannerWorker(
            folders=self.folders.copy(),
            extensions=selected_extensions,
            skip_hidden=self.setting_enabled("hidden", True)
        )

        self.worker.progress_changed.connect(
            self.update_scan_progress
        )

        self.worker.scan_completed.connect(
            self.scan_finished
        )

        self.worker.finished.connect(
            self.scanner_worker_finished
        )

        self.worker.start()

    def update_scan_progress(
        self,
        files_found,
        directories,
        current_path
    ):

        self.status_label.setText(
            f"Scanning | Files found: {files_found} | "
            f"Directories: {directories}"
        )

        self.progress_bar.setToolTip(current_path)

    # CANCELLATION

    def cancel_scan(self):

        active_worker = next(
            (
                worker
                for worker in (
                    self.worker,
                    self.hash_worker,
                    self.fuzzy_worker,
                    self.semantic_worker
                )
                if self.worker_is_running(worker)
            ),
            None
        )

        if active_worker is None:
            return

        active_worker.requestInterruption()

        self.cancel_button.setEnabled(False)

        self.status_label.setText(
            "Stopping current operation..."
        )

    # FILE DISPLAY

    @staticmethod
    def format_size(size):

        value = float(size)

        for unit in ["B", "KB", "MB", "GB", "TB"]:

            if value < 1024:
                return f"{value:.2f} {unit}"

            value /= 1024

        return f"{value:.2f} PB"

    def display_scanned_files(self):

        self.results_table.setSortingEnabled(False)

        self.results_table.setRowCount(
            len(self.records)
        )

        for row, record in enumerate(self.records):

            values = [
                record.name,
                record.extension.upper(),
                self.format_size(record.size_bytes),
                record.modified_time,
                record.path
            ]

            for column, value in enumerate(values):

                item = QTableWidgetItem(str(value))

                if column == 4:
                    item.setToolTip(record.path)

                self.results_table.setItem(
                    row,
                    column,
                    item
                )

        self.results_table.setSortingEnabled(True)

    # SCAN COMPLETE -> HASH

    def scan_finished(self, report):

        self.records = report["files"]
        self.display_scanned_files()

        if report["cancelled"]:

            self.exact_report = {
                "duplicate_groups": [],
                "candidate_files": 0,
                "files_hashed": 0,
                "files_processed": 0,
                "errors": 0,
                "cancelled": True
            }

            self.partial_report = self.empty_partial_report(
                cancelled=True
            )

            self.finish_analysis(
                self.empty_semantic_report(cancelled=True)
            )

            return

        self.status_label.setText(
            f"Folder scan completed: {len(self.records)} files. "
            "Starting SHA-256 detection..."
        )

        self.start_hash_detection()

    def start_hash_detection(self):

        self.progress_bar.setRange(0, 0)

        self.hash_worker = HashDetectorWorker(
            self.records
        )

        self.hash_worker.progress_changed.connect(
            self.update_hash_progress
        )

        self.hash_worker.detection_completed.connect(
            self.hash_finished
        )

        self.hash_worker.finished.connect(
            self.hash_worker_finished
        )

        self.hash_worker.start()

    def update_hash_progress(
        self,
        processed,
        total,
        path
    ):

        if total <= 0:
            return

        self.progress_bar.setRange(0, total)
        self.progress_bar.setValue(processed)

        self.status_label.setText(
            f"SHA-256 hashing: {processed}/{total} files"
        )

        self.progress_bar.setToolTip(path)

    # HASH COMPLETE -> FUZZY

    def hash_finished(self, report):

        self.exact_report = report

        if report["cancelled"]:

            self.partial_report = self.empty_partial_report(
                cancelled=True
            )

            self.finish_analysis(
                self.empty_semantic_report(cancelled=True)
            )

            return

        self.status_label.setText(
            "SHA-256 completed. Starting RapidFuzz analysis..."
        )

        self.start_partial_detection()

    @staticmethod
    def normalized_path_pair(path_a, path_b):

        path_a = os.path.normcase(
            os.path.abspath(path_a)
        )

        path_b = os.path.normcase(
            os.path.abspath(path_b)
        )

        return tuple(sorted((path_a, path_b)))

    def get_exact_duplicate_pairs(self):

        excluded_pairs = set()

        if not self.exact_report:
            return excluded_pairs

        for group in self.exact_report["duplicate_groups"]:

            files = group["files"]

            for i in range(len(files)):

                for j in range(i + 1, len(files)):

                    excluded_pairs.add(
                        self.normalized_path_pair(
                            files[i].path,
                            files[j].path
                        )
                    )

        return excluded_pairs

    # RAPIDFUZZ PARTIAL DETECTION

    def start_partial_detection(self):

        threshold = int(
            self.settings.value("partial", 85)
        )

        self.progress_bar.setRange(0, 0)

        self.status_label.setText(
            "Extracting document text and comparing passages..."
        )

        self.fuzzy_worker = FuzzyDuplicateWorker(
            records=self.records,
            threshold=threshold,
            excluded_pairs=self.get_exact_duplicate_pairs()
        )

        self.fuzzy_worker.progress_changed.connect(
            self.update_fuzzy_progress
        )

        self.fuzzy_worker.detection_completed.connect(
            self.fuzzy_finished
        )

        self.fuzzy_worker.finished.connect(
            self.fuzzy_worker_finished
        )

        self.fuzzy_worker.start()

    def update_fuzzy_progress(
        self,
        processed,
        total,
        detail
    ):

        if total > 0:
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(processed)
        else:
            self.progress_bar.setRange(0, 0)

        self.status_label.setText(detail)

    # RAPIDFUZZ COMPLETE -> SEMANTIC AI

    def fuzzy_finished(self, report):

        self.partial_report = report

        if report.get("cancelled"):

            self.finish_analysis(
                self.empty_semantic_report(cancelled=True)
            )

            return

        self.status_label.setText(
            "RapidFuzz completed. Starting AI semantic detection..."
        )

        self.start_semantic_detection()

    # REPORT BUILDERS

    @staticmethod
    def empty_partial_report(
        cancelled=False,
        threshold=85
    ):

        return {
            "matches": [],
            "documents_extracted": 0,
            "documents_without_text": 0,
            "document_pairs_checked": 0,
            "errors": 0,
            "threshold": threshold,
            "cancelled": cancelled
        }

    @staticmethod
    def empty_semantic_report(
        cancelled=False,
        error=None,
        threshold=70
    ):

        return {
            "matches": [],
            "documents_extracted": 0,
            "documents_without_text": 0,
            "document_pairs_checked": 0,
            "errors": 0,
            "threshold": threshold,
            "cancelled": cancelled,
            "error": error,
            "model": "sentence-transformers/all-MiniLM-L6-v2"
        }

    # SEMANTIC AI DETECTION

    def start_semantic_detection(self):

        threshold = int(
            self.settings.value("semantic", 70)
        )

        self.progress_bar.setRange(0, 0)

        self.status_label.setText(
            "Loading AI model and generating semantic embeddings..."
        )

        self.semantic_worker = SemanticDuplicateWorker(
            records=self.records,
            threshold=threshold,
            excluded_pairs=self.get_exact_duplicate_pairs()
        )

        self.semantic_worker.progress_changed.connect(
            self.update_semantic_progress
        )

        self.semantic_worker.detection_completed.connect(
            self.semantic_finished
        )

        self.semantic_worker.finished.connect(
            self.semantic_worker_finished
        )

        self.semantic_worker.start()

    def update_semantic_progress(
        self,
        processed,
        total,
        detail
    ):

        if total > 0:
            self.progress_bar.setRange(0, total)
            self.progress_bar.setValue(processed)
        else:
            self.progress_bar.setRange(0, 0)

        self.status_label.setText(detail)

    def semantic_finished(self, report):

        if report.get("error"):

            self.status_label.setText(
                "Semantic detection failed: "
                + str(report["error"])
            )

        elif report.get("cancelled"):

            self.status_label.setText(
                "Semantic detection cancelled."
            )

        else:

            self.status_label.setText(
                f"Analysis completed. "
                f"Exact groups: {len(self.exact_report['duplicate_groups'])} | "
                f"Partial matches: {len(self.partial_report['matches'])} | "
                f"Semantic matches: {len(report['matches'])}"
            )

        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)

        self.finish_analysis(report)

    def finish_analysis(self, semantic_report):

        if self.exact_report is None:

            self.exact_report = {
                "duplicate_groups": [],
                "candidate_files": 0,
                "files_hashed": 0,
                "files_processed": 0,
                "errors": 0,
                "cancelled": True
            }

        if self.partial_report is None:

            self.partial_report = self.empty_partial_report(
                cancelled=True
            )

        self.analysis_ready.emit({
            "exact": self.exact_report,
            "partial": self.partial_report,
            "semantic": semantic_report
        })

    # THREAD CLEANUP

    def scanner_worker_finished(self):

        worker, self.worker = self.worker, None

        if worker is not None:
            worker.deleteLater()

        self.update_controls_if_idle()

    def hash_worker_finished(self):

        worker, self.hash_worker = self.hash_worker, None

        if worker is not None:
            worker.deleteLater()

        self.update_controls_if_idle()

    def fuzzy_worker_finished(self):

        worker, self.fuzzy_worker = self.fuzzy_worker, None

        if worker is not None:
            worker.deleteLater()

        self.update_controls_if_idle()

    def semantic_worker_finished(self):

        worker, self.semantic_worker = self.semantic_worker, None

        if worker is not None:
            worker.deleteLater()

        self.update_controls_if_idle()

    def update_controls_if_idle(self):

        if not self.any_worker_running():
            self.set_controls_enabled(True)


# =====================================================
# RESULTS PAGE
# =====================================================

class ResultsPage(QWidget):

    def __init__(self, go_to_scan):
        super().__init__()

        # Phase 8 state
        self.exact_report = None
        self.last_report = None
        self.exact_groups = {}
        self.file_manager_worker = None

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        title = QLabel("Duplicate Detection Results")
        title.setObjectName("Section")

        self.summary_label = QLabel("No analysis report yet.")
        self.summary_label.setObjectName("Muted")
        self.summary_label.setWordWrap(True)

        self.tabs = QTabWidget()

        # EXACT DUPLICATES TAB

        exact_page = QWidget()
        exact_layout = QVBoxLayout(exact_page)

        self.exact_table = QTableWidget(0, 5)

        self.exact_table.setHorizontalHeaderLabels([
            "Group",
            "File Name",
            "Size",
            "SHA-256",
            "File Path"
        ])

        self.configure_table(self.exact_table)

        self.exact_table.itemSelectionChanged.connect(
            self.update_exact_action_state
        )

        # Phase 8 management controls

        self.exact_action_label = QLabel(
            "Select a file from an exact duplicate group to keep."
        )
        self.exact_action_label.setObjectName("Muted")
        self.exact_action_label.setWordWrap(True)

        self.manage_exact_button = QPushButton(
            "Move Other Copies to Recycle Bin"
        )

        self.manage_exact_button.setEnabled(False)

        self.manage_exact_button.clicked.connect(
            self.manage_selected_exact_group
        )

        exact_controls = QHBoxLayout()
        exact_controls.addWidget(self.exact_action_label, 1)
        exact_controls.addWidget(self.manage_exact_button)

        self.exact_empty = QLabel("No exact duplicates found.")
        self.exact_empty.setObjectName("Muted")

        exact_layout.addWidget(self.exact_table)
        exact_layout.addLayout(exact_controls)
        exact_layout.addWidget(self.exact_empty)

        self.tabs.addTab(
            exact_page,
            "Exact Duplicates"
        )

        # PARTIAL DUPLICATES TAB

        partial_page = QWidget()
        partial_layout = QVBoxLayout(partial_page)

        partial_description = QLabel(
            "Textually similar passages detected by RapidFuzz. "
            "Double-click an evidence row to inspect full passages."
        )

        partial_description.setObjectName("Muted")
        partial_description.setWordWrap(True)

        self.partial_table = QTableWidget(0, 6)

        self.partial_table.setHorizontalHeaderLabels([
            "File A",
            "File B",
            "Similarity",
            "Classification",
            "Passages",
            "Matching Evidence"
        ])

        self.configure_table(self.partial_table)

        self.partial_empty = QLabel("No partial duplicates found.")
        self.partial_empty.setObjectName("Muted")
        self.partial_empty.setWordWrap(True)

        self.partial_table.cellDoubleClicked.connect(
            lambda row, column:
            self.show_evidence(self.partial_table, row)
        )

        partial_layout.addWidget(partial_description)
        partial_layout.addWidget(self.partial_table)
        partial_layout.addWidget(self.partial_empty)

        self.tabs.addTab(
            partial_page,
            "Partial Duplicates"
        )

        # SEMANTIC AI TAB

        semantic_page = QWidget()
        semantic_layout = QVBoxLayout(semantic_page)

        semantic_description = QLabel(
            "Meaning-based passage matches from Sentence Transformers. "
            "Scores are cosine similarities, not percentages of a document "
            "duplicated. Double-click an evidence row to inspect full passages."
        )

        semantic_description.setObjectName("Muted")
        semantic_description.setWordWrap(True)

        self.semantic_table = QTableWidget(0, 6)

        self.semantic_table.setHorizontalHeaderLabels([
            "File A",
            "File B",
            "AI Similarity",
            "Classification",
            "Passages",
            "Matching Evidence"
        ])

        self.configure_table(self.semantic_table)

        self.semantic_empty = QLabel("No semantic matches found.")
        self.semantic_empty.setObjectName("Muted")
        self.semantic_empty.setWordWrap(True)

        self.semantic_table.cellDoubleClicked.connect(
            lambda row, column:
            self.show_evidence(self.semantic_table, row)
        )

        semantic_layout.addWidget(semantic_description)
        semantic_layout.addWidget(self.semantic_table)
        semantic_layout.addWidget(self.semantic_empty)

        self.tabs.addTab(
            semantic_page,
            "Semantic AI"
        )

        # FOOTER

        scan_button = QPushButton("Scan another folder")
        scan_button.clicked.connect(go_to_scan)

        layout.addWidget(title)
        layout.addWidget(self.summary_label)
        layout.addWidget(self.tabs, 1)
        layout.addWidget(scan_button)

    @staticmethod
    def configure_table(table):

        table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )

        table.verticalHeader().setVisible(False)

        table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )

        table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )

        table.setAlternatingRowColors(True)

    @staticmethod
    def format_size(size):

        value = float(size)

        for unit in ["B", "KB", "MB", "GB", "TB"]:

            if value < 1024:
                return f"{value:.2f} {unit}"

            value /= 1024

        return f"{value:.2f} PB"

    # =================================================
    # PHASE 8: SAFE EXACT DUPLICATE MANAGEMENT
    # =================================================

    def update_exact_action_state(self):
        """Enable management only when a duplicate file is selected."""

        selected = self.exact_table.currentRow() >= 0

        self.manage_exact_button.setEnabled(
            selected and self.file_manager_worker is None
        )

    def manage_selected_exact_group(self):
        """Keep the selected file and move other group copies to Recycle Bin."""

        row = self.exact_table.currentRow()

        if row < 0:
            return

        item = self.exact_table.item(row, 0)

        if item is None:
            return

        selection = item.data(Qt.ItemDataRole.UserRole)

        if not selection:
            return

        group_number = selection["group_number"]
        keep_path = selection["path"]

        group = self.exact_groups.get(group_number)

        if not group:
            QMessageBox.warning(
                self,
                "Group unavailable",
                "This duplicate group is no longer available. "
                "Please scan again."
            )
            return

        remove_paths = [
            record.path
            for record in group["files"]
            if os.path.normcase(os.path.abspath(record.path))
            != os.path.normcase(os.path.abspath(keep_path))
        ]

        if not remove_paths:
            return

        file_list = "\n".join(
            f"• {path}" for path in remove_paths
        )

        answer = QMessageBox.question(
            self,
            "Confirm duplicate management",
            f"FILE TO KEEP:\n{keep_path}\n\n"
            f"FILES TO MOVE TO RECYCLE BIN:\n{file_list}\n\n"
            "The application will verify the SHA-256 hashes again.\n"
            "The selected copies will be moved to the Windows "
            "Recycle Bin, not permanently deleted.\n\n"
            "Do you want to continue?",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if answer != QMessageBox.StandardButton.Yes:
            return

        self.exact_action_label.setText(
            "Verifying files and moving selected copies..."
        )

        self.manage_exact_button.setEnabled(False)

        self.file_manager_worker = FileManagerWorker(
            keep_path=keep_path,
            remove_paths=remove_paths,
            expected_sha256=group["digest"]
        )

        self.file_manager_worker.operation_completed.connect(
            self.handle_file_manager_result
        )

        self.file_manager_worker.operation_failed.connect(
            self.handle_file_manager_error
        )

        self.file_manager_worker.finished.connect(
            self.file_manager_worker_finished
        )

        self.file_manager_worker.start()

    def handle_file_manager_result(self, result):
        """Refresh duplicate results after file management."""

        moved_paths = {
            os.path.normcase(os.path.abspath(path))
            for path in result.moved_paths
        }

        updated_groups = []

        for group in self.exact_report.get("duplicate_groups", []):

            remaining_files = [
                record
                for record in group["files"]
                if os.path.normcase(
                    os.path.abspath(record.path)
                ) not in moved_paths
            ]

            if len(remaining_files) >= 2:
                updated_groups.append({
                    **group,
                    "files": remaining_files
                })

        self.exact_report["duplicate_groups"] = updated_groups

        if self.last_report is not None:
            self.last_report["exact"] = self.exact_report
            self.display_report(self.last_report)

        recovered = self.format_size(result.recovered_bytes)

        self.exact_action_label.setText(
            f"Storage recovered: {recovered}"
        )

        details = (
            f"{getattr(result, 'message', 'File operation completed.')}\n\n"
            f"Files moved: {len(result.moved_paths)}\n"
            f"Storage recovered: {recovered}\n"
            f"File retained: {getattr(result, 'kept_path', 'Selected file')}"
        )

        if result.failed_paths:
            details += (
                "\n\nFiles that could not be moved:\n"
                + "\n".join(result.failed_paths)
            )

        QMessageBox.information(
            self,
            "File management result",
            details
        )

    def handle_file_manager_error(self, error):

        self.exact_action_label.setText(
            "File operation stopped. Review the error."
        )

        QMessageBox.warning(
            self,
            "File management failed",
            error
        )

    def file_manager_worker_finished(self):

        worker = self.file_manager_worker
        self.file_manager_worker = None

        if worker is not None:
            worker.deleteLater()

        self.update_exact_action_state()

    # DISPLAY COMBINED REPORT

    def display_report(self, report):

        self.last_report = report
        self.exact_report = report["exact"]

        exact = report["exact"]
        partial = report["partial"]
        semantic = report["semantic"]

        groups = exact["duplicate_groups"]

        exact_files = sum(
            len(group["files"])
            for group in groups
        )

        statuses = []

        if exact.get("cancelled"):
            statuses.append("Hashing cancelled")

        if partial.get("cancelled"):
            statuses.append("Partial analysis cancelled")

        if semantic.get("cancelled"):
            statuses.append("Semantic analysis cancelled")

        if semantic.get("error"):
            statuses.append("Semantic model error")

        if not statuses:
            statuses.append("Analysis completed")

        self.summary_label.setText(
            f"{' | '.join(statuses)} | "
            f"Exact groups: {len(groups)} | "
            f"Exact duplicate files: {exact_files} | "
            f"Partial matches: {len(partial.get('matches', []))} | "
            f"Semantic matches: {len(semantic.get('matches', []))} | "
            f"Semantic threshold: {semantic.get('threshold', 70)}%"
        )

        self.display_exact(exact)

        self.display_matches(
            self.partial_table,
            self.partial_empty,
            partial,
            "Partial"
        )

        self.display_matches(
            self.semantic_table,
            self.semantic_empty,
            semantic,
            "Semantic"
        )

    # EXACT RESULTS

    def display_exact(self, report):

        groups = report.get("duplicate_groups", [])

        self.exact_report = report

        self.exact_groups = {
            number: group
            for number, group in enumerate(groups, start=1)
        }

        total_files = sum(
            len(group["files"])
            for group in groups
        )

        self.exact_table.setSortingEnabled(False)
        self.exact_table.setRowCount(total_files)

        row = 0

        for group_number, group in enumerate(
            groups,
            start=1
        ):

            digest = group["digest"]

            for record in group["files"]:

                values = [
                    f"Group {group_number}",
                    record.name,
                    self.format_size(record.size_bytes),
                    digest[:16] + "...",
                    record.path
                ]

                for column, value in enumerate(values):

                    item = QTableWidgetItem(str(value))

                    if column == 0:
                        item.setData(
                            Qt.ItemDataRole.UserRole,
                            {
                                "group_number": group_number,
                                "path": record.path
                            }
                        )

                    if column == 3:
                        item.setToolTip(digest)

                    elif column == 4:
                        item.setToolTip(record.path)

                    self.exact_table.setItem(
                        row,
                        column,
                        item
                    )

                row += 1

        self.exact_table.setSortingEnabled(True)

        self.exact_empty.setVisible(
            not bool(groups)
        )

        self.update_exact_action_state()

    # PARTIAL AND SEMANTIC RESULTS

    def display_matches(
        self,
        table,
        empty_label,
        report,
        detection_type
    ):

        matches = report.get("matches", [])

        table.setSortingEnabled(False)
        table.setRowCount(len(matches))

        for row, match in enumerate(matches):

            record_a = match["file_a"]
            record_b = match["file_b"]
            passages = match.get("passages", [])
            similarity = float(match.get("similarity", 0))

            if similarity >= 90:
                classification = "High"
            elif similarity >= 75:
                classification = "Moderate"
            else:
                classification = "Low"

            preview = ""

            if passages:
                first_passage = passages[0]

                text_a = str(first_passage.get("text_a", ""))
                text_b = str(first_passage.get("text_b", ""))

                preview = (
                    text_a[:65].replace("\n", " ")
                    + " ... "
                    + text_b[:65].replace("\n", " ")
                )

            values = [
                record_a.name,
                record_b.name,
                f"{similarity:.1f}%",
                classification,
                str(len(passages)),
                preview
            ]

            evidence_data = {
                "file_a": record_a.path,
                "file_b": record_b.path,
                "detection_type": detection_type,
                "similarity": similarity,
                "classification": classification,
                "passages": passages
            }

            for column, value in enumerate(values):

                item = QTableWidgetItem(str(value))

                if column == 0:
                    item.setToolTip(record_a.path)

                elif column == 1:
                    item.setToolTip(record_b.path)

                elif column == 5:
                    item.setData(
                        Qt.ItemDataRole.UserRole,
                        evidence_data
                    )

                    item.setToolTip(
                        "Double-click to open the side-by-side evidence viewer."
                    )

                table.setItem(row, column, item)

        table.setSortingEnabled(True)

        if report.get("error"):

            empty_label.setText(
                f"{detection_type} analysis error: {report['error']}"
            )

        elif report.get("cancelled"):

            empty_label.setText(
                f"{detection_type} detection was cancelled. "
                "The displayed matches may be partial results."
            )

        elif matches:

            empty_label.setText("")

        elif report.get("documents_without_text", 0) > 0:

            empty_label.setText(
                f"No {detection_type.lower()} matches found. "
                f"{report['documents_without_text']} documents "
                "had no usable text."
            )

        else:

            empty_label.setText(
                f"No {detection_type.lower()} matches found "
                "at the current threshold."
            )

        empty_label.setVisible(not bool(matches))

    # SIDE-BY-SIDE MATCHING EVIDENCE VIEWER

    @staticmethod
    def make_evidence_html(text, match_number, score):

        safe_text = html.escape(
            str(text or "No passage text available.")
        )

        safe_score = html.escape(
            f"{float(score):.1f}%"
        )

        return f"""
        <html>
        <body style="
            background-color:#0c1627;
            color:#e5e7eb;
            font-family:Segoe UI;
            font-size:13px;
        ">
            <div style="
                background-color:#17452f;
                border:1px solid #3b8260;
                border-radius:7px;
                padding:10px;
                margin-bottom:10px;
            ">
                <b style="color:#bbf7d0;">
                    MATCH {match_number}
                </b>
                <span style="color:#bbf7d0;">
                    &nbsp; | &nbsp; Similarity: {safe_score}
                </span>
            </div>
            <div style="white-space:pre-wrap; line-height:1.5;">
                <span style="
                    background-color:#365d36;
                    color:#ffffff;
                    padding:2px;
                ">{safe_text}</span>
            </div>
        </body>
        </html>
        """

    def show_evidence(self, table, row):

        if row < 0:
            return

        evidence_item = table.item(row, 5)

        if evidence_item is None:
            return

        evidence = evidence_item.data(
            Qt.ItemDataRole.UserRole
        )

        if not evidence:
            return

        detection_type = evidence.get(
            "detection_type",
            "Duplicate"
        )

        similarity = float(
            evidence.get("similarity", 0)
        )

        classification = evidence.get(
            "classification",
            "Unclassified"
        )

        passages = evidence.get("passages", [])

        dialog = QDialog(self)
        dialog.setWindowTitle(
            f"{detection_type} - Detailed Evidence"
        )

        dialog.resize(1150, 760)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(12)

        heading = QLabel(
            f"{detection_type} comparison | "
            f"Similarity: {similarity:.1f}% | "
            f"Classification: {classification}"
        )

        heading.setObjectName("Section")
        heading.setWordWrap(True)

        layout.addWidget(heading)

        explanation = QLabel(
            "The highlighted blocks are the passages selected by the "
            "detection algorithm. Similarity scores are indicators for "
            "review; they do not prove plagiarism or establish who copied whom."
        )

        explanation.setObjectName("Muted")
        explanation.setWordWrap(True)

        layout.addWidget(explanation)

        paths_layout = QGridLayout()

        file_a_title = QLabel("FILE A")
        file_b_title = QLabel("FILE B")

        file_a_title.setObjectName("Section")
        file_b_title.setObjectName("Section")

        file_a_path = QLabel(
            str(evidence.get("file_a", "Unknown path"))
        )

        file_b_path = QLabel(
            str(evidence.get("file_b", "Unknown path"))
        )

        file_a_path.setObjectName("Muted")
        file_b_path.setObjectName("Muted")

        file_a_path.setWordWrap(True)
        file_b_path.setWordWrap(True)

        paths_layout.addWidget(file_a_title, 0, 0)
        paths_layout.addWidget(file_b_title, 0, 1)
        paths_layout.addWidget(file_a_path, 1, 0)
        paths_layout.addWidget(file_b_path, 1, 1)

        layout.addLayout(paths_layout)

        comparison_layout = QHBoxLayout()
        comparison_layout.setSpacing(10)

        file_a_area = QTextEdit()
        file_b_area = QTextEdit()

        file_a_area.setReadOnly(True)
        file_b_area.setReadOnly(True)

        file_a_area.setMinimumHeight(400)
        file_b_area.setMinimumHeight(400)

        file_a_area.setAcceptRichText(True)
        file_b_area.setAcceptRichText(True)

        file_a_area.setStyleSheet(
            "QTextEdit { background-color:#0c1627; color:#e5e7eb; "
            "border:1px solid #3b8260; border-radius:7px; padding:8px; }"
        )

        file_b_area.setStyleSheet(
            "QTextEdit { background-color:#0c1627; color:#e5e7eb; "
            "border:1px solid #3b8260; border-radius:7px; padding:8px; }"
        )

        if passages:

            parts_a = []
            parts_b = []

            for number, passage in enumerate(
                passages,
                start=1
            ):

                passage_score = float(
                    passage.get("score", similarity)
                )

                text_a = passage.get("text_a", "")
                text_b = passage.get("text_b", "")

                parts_a.append(
                    self.make_evidence_html(
                        text_a,
                        number,
                        passage_score
                    )
                )

                parts_b.append(
                    self.make_evidence_html(
                        text_b,
                        number,
                        passage_score
                    )
                )

            file_a_area.setHtml(
                "<br><hr><br>".join(parts_a)
            )

            file_b_area.setHtml(
                "<br><hr><br>".join(parts_b)
            )

        else:

            file_a_area.setPlainText(
                "No matched passage evidence was included in this result."
            )

            file_b_area.setPlainText(
                "No matched passage evidence was included in this result."
            )

        comparison_layout.addWidget(file_a_area, 1)
        comparison_layout.addWidget(file_b_area, 1)

        layout.addLayout(comparison_layout, 1)

        if detection_type.lower() == "partial":

            method_description = (
                "Detection method: RapidFuzz text similarity. It compares "
                "passage wording and can identify passages with similar text."
            )

        elif detection_type.lower() == "semantic":

            method_description = (
                "Detection method: Sentence Transformers semantic similarity. "
                "It compares vector representations of passages to find "
                "similar meaning, even when wording differs."
            )

        else:

            method_description = (
                "Detection method: exact file comparison using SHA-256 hashes."
            )

        method_label = QLabel(method_description)
        method_label.setObjectName("Muted")
        method_label.setWordWrap(True)

        layout.addWidget(method_label)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close
        )

        buttons.rejected.connect(dialog.accept)
        buttons.accepted.connect(dialog.accept)

        layout.addWidget(buttons)

        dialog.exec()


# =====================================================
# SETTINGS PAGE
# =====================================================

class SettingsPage(QWidget):

    def __init__(self):
        super().__init__()

        self.settings = QSettings(
            "AI Duplicate Detector",
            "Desktop"
        )

        layout = QVBoxLayout(self)

        title = QLabel("Application Settings")
        title.setObjectName("Section")

        description = QLabel(
            "Configure matching sensitivity and document formats."
        )
        description.setObjectName("Muted")

        partial_label = QLabel(
            "Partial similarity threshold"
        )

        self.partial_spin = QSpinBox()
        self.partial_spin.setRange(50, 100)
        self.partial_spin.setSuffix("%")

        semantic_label = QLabel(
            "Semantic similarity threshold"
        )

        self.semantic_spin = QSpinBox()
        self.semantic_spin.setRange(50, 100)
        self.semantic_spin.setSuffix("%")

        self.semantic_spin.setToolTip(
            "Starting threshold for semantic passage cosine similarity. "
            "Tune it using labelled test documents."
        )

        formats_title = QLabel(
            "Supported document formats"
        )
        formats_title.setObjectName("Section")

        self.pdf_check = QCheckBox("PDF")
        self.docx_check = QCheckBox("DOCX")
        self.txt_check = QCheckBox("TXT")
        self.md_check = QCheckBox("MD")

        self.cache_check = QCheckBox(
            "Reuse cached results"
        )

        self.hidden_check = QCheckBox(
            "Skip hidden and system folders"
        )

        save_button = QPushButton("Save settings")
        save_button.clicked.connect(self.save_settings)

        reset_button = QPushButton("Reset defaults")
        reset_button.setObjectName("Secondary")
        reset_button.clicked.connect(self.reset_settings)

        button_layout = QHBoxLayout()
        button_layout.addWidget(reset_button)
        button_layout.addWidget(save_button)

        layout.addWidget(title)
        layout.addWidget(description)

        layout.addWidget(partial_label)
        layout.addWidget(self.partial_spin)

        layout.addWidget(semantic_label)
        layout.addWidget(self.semantic_spin)

        layout.addWidget(formats_title)
        layout.addWidget(self.pdf_check)
        layout.addWidget(self.docx_check)
        layout.addWidget(self.txt_check)
        layout.addWidget(self.md_check)

        layout.addWidget(self.cache_check)
        layout.addWidget(self.hidden_check)

        layout.addLayout(button_layout)
        layout.addStretch()

        self.load_settings()

    @staticmethod
    def setting_bool(value):

        if isinstance(value, bool):
            return value

        return str(value).lower() in (
            "true", "1", "yes", "on"
        )

    def load_settings(self):

        self.partial_spin.setValue(
            int(self.settings.value("partial", 85))
        )

        self.semantic_spin.setValue(
            int(self.settings.value("semantic", 70))
        )

        self.pdf_check.setChecked(
            self.setting_bool(
                self.settings.value("pdf", True)
            )
        )

        self.docx_check.setChecked(
            self.setting_bool(
                self.settings.value("docx", True)
            )
        )

        self.txt_check.setChecked(
            self.setting_bool(
                self.settings.value("txt", True)
            )
        )

        self.md_check.setChecked(
            self.setting_bool(
                self.settings.value("md", True)
            )
        )

        self.cache_check.setChecked(
            self.setting_bool(
                self.settings.value("cache", True)
            )
        )

        self.hidden_check.setChecked(
            self.setting_bool(
                self.settings.value("hidden", True)
            )
        )

    def save_settings(self):

        formats = [
            self.pdf_check,
            self.docx_check,
            self.txt_check,
            self.md_check
        ]

        if not any(item.isChecked() for item in formats):

            QMessageBox.warning(
                self,
                "Choose a format",
                "Select at least one document format."
            )

            return

        values = {
            "partial": self.partial_spin.value(),
            "semantic": self.semantic_spin.value(),
            "pdf": self.pdf_check.isChecked(),
            "docx": self.docx_check.isChecked(),
            "txt": self.txt_check.isChecked(),
            "md": self.md_check.isChecked(),
            "cache": self.cache_check.isChecked(),
            "hidden": self.hidden_check.isChecked()
        }

        for key, value in values.items():
            self.settings.setValue(key, value)

        self.settings.sync()

        QMessageBox.information(
            self,
            "Saved",
            "Your settings have been saved successfully."
        )

    def reset_settings(self):

        self.partial_spin.setValue(85)
        self.semantic_spin.setValue(70)

        self.pdf_check.setChecked(True)
        self.docx_check.setChecked(True)
        self.txt_check.setChecked(True)
        self.md_check.setChecked(True)

        self.cache_check.setChecked(True)
        self.hidden_check.setChecked(True)


# =====================================================
# MAIN WINDOW
# =====================================================

class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle(
            "AI-Based Intelligent Duplicate File Detection System"
        )

        self.resize(1200, 780)
        self.setMinimumSize(950, 650)

        self.nav_buttons = {}

        self.pages_info = {
            "dashboard": (
                "Dashboard",
                "Your duplicate detection workspace"
            ),
            "scan": (
                "Scan Folders",
                "Select folders for document analysis"
            ),
            "results": (
                "Results",
                "Review exact, partial and semantic duplicate evidence"
            ),
            "settings": (
                "Settings",
                "Configure application preferences"
            )
        }

        self.build_ui()
        self.setStyleSheet(STYLE)
        self.navigate("dashboard")

    def build_ui(self):

        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # SIDEBAR

        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(220)

        sidebar_layout = QVBoxLayout(sidebar)

        sidebar_layout.setContentsMargins(
            15, 22, 15, 18
        )

        brand = QLabel("◈ AI FILE GUARD")
        brand.setObjectName("Brand")

        sidebar_layout.addWidget(brand)
        sidebar_layout.addSpacing(30)

        navigation = [
            ("dashboard", "Dashboard"),
            ("scan", "Scan Folders"),
            ("results", "Duplicate Results"),
            ("settings", "Settings")
        ]

        for key, text in navigation:

            button = QPushButton(text)
            button.setObjectName("Nav")

            button.clicked.connect(
                lambda checked=False, page=key:
                self.navigate(page)
            )

            self.nav_buttons[key] = button
            sidebar_layout.addWidget(button)

        sidebar_layout.addStretch()

        privacy = QLabel("LOCAL-FIRST WORKSPACE")
        privacy.setObjectName("Muted")

        sidebar_layout.addWidget(privacy)

        # MAIN CONTENT

        content = QWidget()
        content_layout = QVBoxLayout(content)

        content_layout.setContentsMargins(
            28, 24, 28, 24
        )

        header = QVBoxLayout()

        self.page_title = QLabel()
        self.page_title.setObjectName("PageTitle")

        self.page_description = QLabel()
        self.page_description.setObjectName("Muted")

        header.addWidget(self.page_title)
        header.addWidget(self.page_description)

        content_layout.addLayout(header)

        # PAGES

        self.stack = QStackedWidget()

        self.dashboard = DashboardPage(
            lambda: self.navigate("scan")
        )

        self.scan_page = ScanPage()

        self.results_page = ResultsPage(
            lambda: self.navigate("scan")
        )

        self.settings_page = SettingsPage()

        self.pages = {
            "dashboard": self.dashboard,
            "scan": self.scan_page,
            "results": self.results_page,
            "settings": self.settings_page
        }

        for page in self.pages.values():
            self.stack.addWidget(page)

        self.scan_page.analysis_ready.connect(
            self.handle_analysis_ready
        )

        content_layout.addWidget(self.stack)

        main_layout.addWidget(sidebar)
        main_layout.addWidget(content)

    # NAVIGATION

    def navigate(self, page_name):

        self.stack.setCurrentWidget(
            self.pages[page_name]
        )

        title, description = self.pages_info[page_name]

        self.page_title.setText(title)
        self.page_description.setText(description)

        for key, button in self.nav_buttons.items():

            button.setProperty(
                "active",
                key == page_name
            )

            button.style().unpolish(button)
            button.style().polish(button)

    # COMPLETE ANALYSIS RESULTS

    def handle_analysis_ready(self, report):

        self.results_page.display_report(report)

        self.navigate("results")
