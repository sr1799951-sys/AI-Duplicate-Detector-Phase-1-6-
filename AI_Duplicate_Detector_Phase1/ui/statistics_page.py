
from datetime import datetime

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QPushButton,
)


class StatisticsPage(QWidget):

    def __init__(self, statistics_manager):
        super().__init__()

        self.statistics_manager = statistics_manager

        self.setStyleSheet("""
            QWidget {
                background-color: #0f172a;
                color: #e2e8f0;
                font-family: Segoe UI;
            }

            QFrame {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 10px;
            }

            QLabel#cardTitle {
                color: #94a3b8;
                font-size: 12px;
            }

            QLabel#cardValue {
                color: #f8fafc;
                font-size: 25px;
                font-weight: bold;
            }

            QPushButton {
                background-color: #2563eb;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 9px 16px;
            }

            QPushButton:hover {
                background-color: #1d4ed8;
            }

            QTableWidget {
                background-color: #1e293b;
                alternate-background-color: #263449;
                border: 1px solid #334155;
                gridline-color: #334155;
                border-radius: 8px;
            }

            QHeaderView::section {
                background-color: #334155;
                color: white;
                padding: 8px;
                border: none;
                font-weight: bold;
            }
        """)

        self.cards = {}

        self.build_ui()
        self.refresh()

    def build_ui(self):

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(18)

        title = QLabel("Statistics Dashboard")
        title.setStyleSheet(
            "font-size: 25px; font-weight: bold;"
        )

        subtitle = QLabel(
            "Real statistics from your duplicate detection scans."
        )
        subtitle.setStyleSheet("color: #94a3b8;")

        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)

        refresh_button = QPushButton("Refresh Statistics")
        refresh_button.clicked.connect(self.refresh)

        main_layout.addWidget(
            refresh_button,
            alignment=Qt.AlignmentFlag.AlignRight
        )

        cards_layout = QVBoxLayout()
        cards_layout.setSpacing(12)

        first_row = QHBoxLayout()
        second_row = QHBoxLayout()
        third_row = QHBoxLayout()

        self.add_card(first_row, "Total Scan Runs", "total_scans")
        self.add_card(
            first_row,
            "Files Scanned",
            "total_files_scanned"
        )
        self.add_card(
            first_row,
            "Exact Duplicate Groups",
            "exact_groups"
        )

        self.add_card(
            second_row,
            "Exact Duplicate Files",
            "exact_duplicate_files"
        )
        self.add_card(
            second_row,
            "Partial Text Matches",
            "partial_matches"
        )
        self.add_card(
            second_row,
            "Semantic AI Matches",
            "semantic_matches"
        )

        self.add_card(
            third_row,
            "Potential Storage (Latest Scan)",
            "potential_recoverable_bytes",
            is_size=True
        )
        self.add_card(
            third_row,
            "Storage Actually Recovered",
            "storage_recovered_bytes",
            is_size=True
        )

        cards_layout.addLayout(first_row)
        cards_layout.addLayout(second_row)
        cards_layout.addLayout(third_row)

        main_layout.addLayout(cards_layout)

        history_title = QLabel("Scan History")
        history_title.setStyleSheet(
            "font-size: 19px; font-weight: bold; margin-top: 8px;"
        )

        main_layout.addWidget(history_title)

        self.history_table = QTableWidget()

        self.history_table.setColumnCount(7)

        self.history_table.setHorizontalHeaderLabels([
            "Date and Time",
            "Files Scanned",
            "Exact Groups",
            "Partial Matches",
            "Semantic Matches",
            "Potential Storage",
            "Status"
        ])

        self.history_table.setAlternatingRowColors(True)
        self.history_table.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers
        )

        self.history_table.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )

        self.history_table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.Stretch
        )

        self.history_table.verticalHeader().setVisible(False)

        main_layout.addWidget(self.history_table)

    def add_card(
        self,
        layout,
        title,
        key,
        is_size=False
    ):

        card = QFrame()
        card.setMinimumHeight(105)

        card_layout = QVBoxLayout(card)

        title_label = QLabel(title)
        title_label.setObjectName("cardTitle")

        value_label = QLabel("0")
        value_label.setObjectName("cardValue")

        card_layout.addWidget(title_label)
        card_layout.addWidget(value_label)
        card_layout.addStretch()

        layout.addWidget(card)

        self.cards[key] = {
            "label": value_label,
            "is_size": is_size
        }

    @staticmethod
    def format_size(size_bytes):

        size_bytes = max(0, int(size_bytes))

        units = ["B", "KB", "MB", "GB", "TB"]

        size = float(size_bytes)

        for unit in units:

            if size < 1024 or unit == "TB":
                return f"{size:.2f} {unit}"

            size /= 1024

        return f"{size:.2f} TB"

    def refresh(self):

        summary = self.statistics_manager.get_summary()

        history = self.statistics_manager.data.get(
            "scan_history",
            []
        )

        # Potential storage is based on the latest scan,
        # not the sum of repeated scans.
        latest_potential = (
            history[-1].get("potential_recoverable_bytes", 0)
            if history else 0
        )

        summary["potential_recoverable_bytes"] = (
            latest_potential
        )

        for key, card in self.cards.items():

            value = summary.get(key, 0)

            if card["is_size"]:
                value = self.format_size(value)
            else:
                value = f"{value:,}"

            card["label"].setText(str(value))

        self.populate_history(history)

    def populate_history(self, history):

        newest_first = list(reversed(history))

        self.history_table.setRowCount(len(newest_first))

        if not newest_first:
            self.history_table.setRowCount(1)

            item = QTableWidgetItem(
                "No scan history yet. Run your first scan!"
            )

            item.setTextAlignment(
                Qt.AlignmentFlag.AlignCenter
            )

            self.history_table.setSpan(0, 0, 1, 7)
            self.history_table.setItem(0, 0, item)

            return

        self.history_table.clearSpans()

        for row, entry in enumerate(newest_first):

            timestamp = entry.get("timestamp", "")

            try:
                timestamp = datetime.fromisoformat(
                    timestamp
                ).strftime("%d-%m-%Y %I:%M %p")
            except (ValueError, TypeError):
                pass

            values = [
                timestamp,
                f"{entry.get('files_scanned', 0):,}",
                str(entry.get("exact_groups", 0)),
                str(entry.get("partial_matches", 0)),
                str(entry.get("semantic_matches", 0)),
                self.format_size(
                    entry.get("potential_recoverable_bytes", 0)
                ),
                "Cancelled" if entry.get("cancelled", False)
                else "Completed"
            ]

            for column, value in enumerate(values):

                item = QTableWidgetItem(value)

                item.setTextAlignment(
                    Qt.AlignmentFlag.AlignCenter
                )

                self.history_table.setItem(
                    row,
                    column,
                    item
                )
