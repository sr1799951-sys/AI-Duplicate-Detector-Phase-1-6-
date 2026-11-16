from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QFrame,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QPushButton,
    QSizePolicy,
    QScrollArea,
)


class StatisticsPage(QWidget):
    """
    Light-themed statistics dashboard.

    Keeps the existing StatisticsManager interface:
      - statistics_manager.get_summary()
      - statistics_manager.data["scan_history"]

    The page only displays statistics. It does not alter scan history or
    file-management behaviour.
    """

    def __init__(self, statistics_manager):
        super().__init__()

        self.statistics_manager = statistics_manager
        self.cards = {}

        self.setObjectName("StatisticsPage")
        self.setStyleSheet("""
        QWidget#StatisticsContent {
    background-color: #f4f7fb;
}
            QWidget#StatisticsPage {
                background-color: #f4f7fb;
                color: #172033;
                font-family: "Segoe UI";
            }

            QLabel#mainTitle {
                color: #172033;
                font-size: 28px;
                font-weight: 700;
            }

            QLabel#subtitle {
                color: #64748b;
                font-size: 13px;
            }

            QLabel#sectionTitle {
                color: #172033;
                font-size: 18px;
                font-weight: 700;
            }

            QLabel#mutedText {
                color: #64748b;
                font-size: 12px;
            }

            QFrame#statCard {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 13px;
            }

            QFrame#statCard:hover {
                background-color: #ffffff;
                border: 1px solid #93c5fd;
            }

            QLabel#cardTitle {
                color: #64748b;
                font-size: 11px;
                font-weight: 700;
            }

            QLabel#cardValue {
                color: #172033;
                font-size: 25px;
                font-weight: 700;
            }

            QLabel#cardAccent {
                font-size: 10px;
                font-weight: 700;
            }

            QFrame#historyPanel {
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 13px;
            }

            QPushButton#refreshButton {
                background-color: #2563eb;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 10px 17px;
                font-size: 12px;
                font-weight: 700;
            }

            QPushButton#refreshButton:hover {
                background-color: #1d4ed8;
            }

            QPushButton#refreshButton:pressed {
                background-color: #1e40af;
            }

            QTableWidget {
                background-color: #ffffff;
                alternate-background-color: #f8fafc;
                color: #334155;
                border: 1px solid #e2e8f0;
                border-radius: 8px;
                gridline-color: #edf2f7;
                selection-background-color: #dbeafe;
                selection-color: #1e3a8a;
                padding: 4px;
            }

            QTableWidget::item {
                padding: 9px 7px;
                border-bottom: 1px solid #edf2f7;
            }

            QTableWidget::item:selected {
                background-color: #dbeafe;
                color: #1e3a8a;
            }

            QHeaderView::section {
                background-color: #eff4fa;
                color: #475569;
                padding: 11px 8px;
                border: none;
                border-bottom: 1px solid #dbe3ee;
                font-size: 10px;
                font-weight: 700;
            }

            QScrollBar:vertical {
                background: #f1f5f9;
                width: 10px;
                margin: 2px;
                border-radius: 5px;
            }

            QScrollBar::handle:vertical {
                background: #cbd5e1;
                border-radius: 5px;
                min-height: 28px;
            }

            QScrollBar::handle:vertical:hover {
                background: #94a3b8;
            }

            QScrollBar:horizontal {
                background: #f1f5f9;
                height: 10px;
                margin: 2px;
                border-radius: 5px;
            }

            QScrollBar::handle:horizontal {
                background: #cbd5e1;
                border-radius: 5px;
                min-width: 28px;
            }

            QScrollBar::handle:horizontal:hover {
                background: #94a3b8;
            }

            QScrollBar::add-line,
            QScrollBar::sub-line {
                width: 0px;
                height: 0px;
            }
        """)

        self.build_ui()
        self.refresh()

    def build_ui(self):
        # Main page layout
        page_layout = QVBoxLayout(self)
        page_layout.setContentsMargins(0, 0, 0, 0)
        page_layout.setSpacing(0)

        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        # Content inside scroll area
        content = QWidget()
        content.setObjectName("StatisticsContent")

        # Main dashboard layout
        root = QVBoxLayout(content)
        root.setContentsMargins(24, 22, 24, 22)
        root.setSpacing(18)

        scroll.setWidget(content)
        page_layout.addWidget(scroll)

        # Page heading and refresh action
        header = QHBoxLayout()
        header.setSpacing(12)

        heading = QVBoxLayout()
        heading.setSpacing(5)

        title = QLabel("Statistics Dashboard")
        title.setObjectName("mainTitle")

        subtitle = QLabel(
            "Monitor scan activity, duplicate findings, and recovered storage."
        )
        subtitle.setObjectName("subtitle")
        subtitle.setWordWrap(True)

        heading.addWidget(title)
        heading.addWidget(subtitle)

        header.addLayout(heading)
        header.addStretch()

        refresh_button = QPushButton("↻  Refresh")
        refresh_button.setObjectName("refreshButton")
        refresh_button.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_button.setToolTip("Reload statistics and scan history")
        refresh_button.clicked.connect(self.refresh)

        header.addWidget(refresh_button)
        root.addLayout(header)

        # Eight statistic cards
        cards_grid = QGridLayout()
        cards_grid.setHorizontalSpacing(14)
        cards_grid.setVerticalSpacing(14)

        card_data = [
            ("TOTAL SCAN RUNS", "total_scans", False, "#2563eb"),
            ("FILES SCANNED", "total_files_scanned", False, "#0891b2"),
            ("EXACT DUPLICATE GROUPS", "exact_groups", False, "#7c3aed"),
            ("EXACT DUPLICATE FILES", "exact_duplicate_files", False, "#d97706"),
            ("PARTIAL TEXT MATCHES", "partial_matches", False, "#0284c7"),
            ("SEMANTIC AI MATCHES", "semantic_matches", False, "#9333ea"),
            ("POTENTIAL STORAGE", "potential_recoverable_bytes", True, "#059669"),
            ("STORAGE RECOVERED", "storage_recovered_bytes", True, "#16a34a"),
        ]

        for index, (card_title, key, is_size, accent) in enumerate(card_data):
            self.add_card(
                cards_grid,
                index // 4,
                index % 4,
                card_title,
                key,
                is_size,
                accent,
            )

        root.addLayout(cards_grid)

        # Scan history panel
        history_panel = QFrame()
        history_panel.setObjectName("historyPanel")
        history_panel.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )

        history_layout = QVBoxLayout(history_panel)
        history_layout.setContentsMargins(17, 16, 17, 16)
        history_layout.setSpacing(12)

        history_header = QHBoxLayout()

        history_title = QLabel("Scan History")
        history_title.setObjectName("sectionTitle")

        self.history_count = QLabel("0 records")
        self.history_count.setObjectName("mutedText")

        history_header.addWidget(history_title)
        history_header.addStretch()
        history_header.addWidget(self.history_count)

        history_layout.addLayout(history_header)

        self.history_table = QTableWidget()
        self.history_table.setColumnCount(7)
        self.history_table.setHorizontalHeaderLabels([
            "DATE & TIME",
            "FILES SCANNED",
            "EXACT GROUPS",
            "PARTIAL MATCHES",
            "SEMANTIC MATCHES",
            "POTENTIAL STORAGE",
            "STATUS",
        ])

        self.configure_table()
        history_layout.addWidget(self.history_table, 1)

        root.addWidget(history_panel, 1)

    def add_card(
        self,
        layout,
        row,
        column,
        title,
        key,
        is_size,
        accent,
    ):
        card = QFrame()
        card.setObjectName("statCard")
        card.setMinimumHeight(132)
        card.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed,
        )

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 13, 16, 13)
        card_layout.setSpacing(8)

        accent_bar = QFrame()
        accent_bar.setFixedHeight(4)
        accent_bar.setStyleSheet(
            f"background-color: {accent}; border: none; border-radius: 2px;"
        )

        title_label = QLabel(title)
        title_label.setObjectName("cardTitle")
        title_label.setWordWrap(True)
        title_label.setMinimumHeight(28)

        value_label = QLabel("0")
        value_label.setObjectName("cardValue")
        value_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )

        accent_label = QLabel("PROJECT STATISTIC")
        accent_label.setObjectName("cardAccent")
        accent_label.setStyleSheet(
            f"color: {accent}; font-size: 10px; font-weight: 700;"
        )

        card_layout.addWidget(accent_bar)
        card_layout.addWidget(title_label)
        card_layout.addWidget(value_label)
        card_layout.addStretch()
        card_layout.addWidget(accent_label)

        layout.addWidget(card, row, column)

        self.cards[key] = {
            "label": value_label,
            "is_size": is_size,
        }

    def configure_table(self):
        table = self.history_table
        header = table.horizontalHeader()

        header.setSectionResizeMode(
            QHeaderView.ResizeMode.Interactive
        )
        header.setStretchLastSection(True)
        header.setMinimumSectionSize(90)

        table.verticalHeader().setVisible(False)
        table.verticalHeader().setDefaultSectionSize(44)

        table.setMinimumHeight(280)
        table.setAlternatingRowColors(True)
        table.setWordWrap(False)
        table.setShowGrid(False)

        table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )
        table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        table.setSelectionMode(
            QTableWidget.SelectionMode.SingleSelection
        )

        table.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )
        table.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAsNeeded
        )

        widths = [190, 125, 120, 145, 155, 180, 120]
        for column, width in enumerate(widths):
            table.setColumnWidth(column, width)

    @staticmethod
    def format_size(size_bytes):
        size_bytes = max(0, int(size_bytes or 0))
        units = ["B", "KB", "MB", "GB", "TB"]
        size = float(size_bytes)

        for unit in units:
            if size < 1024 or unit == "TB":
                return f"{size:.2f} {unit}"
            size /= 1024

        return f"{size:.2f} TB"

    def refresh(self):
        """Reload the summary cards and history from StatisticsManager."""
        summary = self.statistics_manager.get_summary()

        history = self.statistics_manager.data.get(
            "scan_history", []
        )

        # Potential storage is the latest scan's estimate, not the sum of
        # estimates across scans (which would count the same files repeatedly).
        latest_potential = (
            history[-1].get("potential_recoverable_bytes", 0)
            if history else 0
        )
        summary["potential_recoverable_bytes"] = latest_potential

        for key, card in self.cards.items():
            value = summary.get(key, 0)

            if card["is_size"]:
                display_value = self.format_size(value)
            else:
                display_value = f"{int(value or 0):,}"

            card["label"].setText(display_value)

        self.populate_history(history)

    def populate_history(self, history):
        table = self.history_table
        newest_first = list(reversed(history or []))

        self.history_count.setText(
            f"{len(newest_first)} record{'s' if len(newest_first) != 1 else ''}"
        )

        table.clearSpans()
        table.setRowCount(0)

        if not newest_first:
            table.setRowCount(1)

            item = QTableWidgetItem(
                "No scan history yet. Run your first scan!"
            )
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setForeground(Qt.GlobalColor.darkGray)

            table.setItem(0, 0, item)
            table.setSpan(0, 0, 1, 7)
            return

        table.setRowCount(len(newest_first))

        for row, entry in enumerate(newest_first):
            timestamp = entry.get("timestamp", "")

            try:
                timestamp = datetime.fromisoformat(
                    timestamp
                ).strftime("%d-%m-%Y %I:%M %p")
            except (ValueError, TypeError):
                timestamp = str(timestamp) if timestamp else "Unknown"

            status = (
                "Cancelled"
                if entry.get("cancelled", False)
                else "Completed"
            )

            values = [
                timestamp,
                f"{int(entry.get('files_scanned', 0) or 0):,}",
                str(entry.get("exact_groups", 0)),
                str(entry.get("partial_matches", 0)),
                str(entry.get("semantic_matches", 0)),
                self.format_size(
                    entry.get("potential_recoverable_bytes", 0)
                ),
                status,
            ]

            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

                if column == 6:
                    if status == "Completed":
                        item.setForeground(Qt.GlobalColor.darkGreen)
                    else:
                        item.setForeground(Qt.GlobalColor.darkYellow)

                table.setItem(row, column, item)
