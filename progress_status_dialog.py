# -*- coding: utf-8 -*-
from qgis.PyQt.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QProgressBar,
    QPlainTextEdit,
    QPushButton,
    QHBoxLayout,
    QFrame,
)
from qgis.PyQt.QtGui import QFont
from .qt_compat import AlignCenter, WindowModal, HLine


class ProgressStatusDialog(QDialog):
    """Unified progress/result window for import/export operations."""

    def __init__(self, title, parent=None, skipped_title="Skipped / Not Imported Files"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(560)
        self.setWindowModality(WindowModal)

        layout = QVBoxLayout(self)

        self.label_status = QLabel("Starting...")
        self.label_status.setAlignment(AlignCenter)
        self.label_status.setWordWrap(True)
        self.label_status.setStyleSheet(
            "background-color: #eef4ff; border: 1px solid #c6d8ff; "
            "border-radius: 6px; padding: 8px; color: #1f3a6d;"
        )
        layout.addWidget(self.label_status)

        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.label_counter = QLabel("0/0")
        self.label_counter.setAlignment(AlignCenter)
        layout.addWidget(self.label_counter)

        self.label_done = QLabel("")
        done_font = QFont()
        done_font.setBold(True)
        self.label_done.setFont(done_font)
        self.label_done.setAlignment(AlignCenter)
        self.label_done.setWordWrap(True)
        layout.addWidget(self.label_done)

        self.label_summary = QLabel("")
        self.label_summary.setAlignment(AlignCenter)
        self.label_summary.setWordWrap(True)
        self.label_summary.setStyleSheet(
            "background-color: #f5f9ff; border: 1px solid #cfdcf0; "
            "border-radius: 6px; padding: 8px; color: #2b3f63;"
        )
        self.label_summary.hide()
        layout.addWidget(self.label_summary)

        separator = QFrame()
        separator.setFrameShape(HLine)
        separator.setStyleSheet("color: #d6d6d6;")
        layout.addWidget(separator)

        self.label_skipped_title = QLabel(skipped_title)
        title_font = QFont()
        title_font.setBold(True)
        self.label_skipped_title.setFont(title_font)
        self.label_skipped_title.setStyleSheet("color: #b03030;")
        layout.addWidget(self.label_skipped_title)

        self.skipped_box = QPlainTextEdit()
        self.skipped_box.setReadOnly(False)  # allow copy/paste/select-all
        self.skipped_box.setPlainText("None")
        self.skipped_box.setMinimumHeight(180)
        self._skipped_items = []
        layout.addWidget(self.skipped_box)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        self.close_button = QPushButton("Close")
        self.close_button.clicked.connect(self.close)
        buttons.addWidget(self.close_button)
        layout.addLayout(buttons)

    def update_progress(self, done_count, total_count, action_text):
        total = max(total_count, 1)
        percent = int((done_count / total) * 100)
        self.progress_bar.setValue(percent)
        self.label_counter.setText(f"{done_count} / {total_count}")
        self.label_status.setText(f"{action_text}\nProgress: {percent}%")

    def finish(self, done_text, skipped_files):
        self.label_done.setText(f"✅ {done_text}")
        self.label_done.setStyleSheet("color: #1a6e2e;")
        if skipped_files:
            self.skipped_box.setPlainText("\n".join(skipped_files))
        else:
            self.skipped_box.setPlainText("None")

    def set_summary_text(self, summary_text):
        """Show a multi-line summary panel under progress area."""
        self.label_summary.setText(summary_text)
        self.label_summary.show()

    def append_skipped_file(self, filepath):
        """Append a skipped file in real-time and keep content copyable."""
        if not filepath:
            return
        self._skipped_items.append(filepath)
        self.skipped_box.setPlainText("\n".join(self._skipped_items))
