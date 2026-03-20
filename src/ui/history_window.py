import os
import sys
from datetime import datetime
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor, QCursor
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QScrollArea, QPushButton, QFrame
)

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ui.base_window import BaseWindow


class HistoryEntry(QFrame):
    """A single transcription entry in the history list."""
    clicked = pyqtSignal(str)        # single click: copy + replay
    doubleClicked = pyqtSignal(str)  # double click: copy only

    def __init__(self, text, timestamp, index, parent=None):
        super().__init__(parent)
        self.text = text
        self.index = index
        self.setCursor(QCursor(Qt.PointingHandCursor))
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(245, 245, 245, 200);
                border-radius: 8px;
                padding: 8px;
                margin: 2px 0px;
            }
            QFrame:hover {
                background-color: rgba(220, 235, 255, 220);
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(2)

        # Header: index + timestamp
        header = QHBoxLayout()
        index_label = QLabel(f"#{index + 1}")
        index_label.setFont(QFont('Segoe UI', 9, QFont.Bold))
        index_label.setStyleSheet("color: #666;")

        time_label = QLabel(timestamp)
        time_label.setFont(QFont('Segoe UI', 8))
        time_label.setStyleSheet("color: #999;")

        header.addWidget(index_label)
        header.addStretch()
        header.addWidget(time_label)
        layout.addLayout(header)

        # Text preview (truncated to 3 lines)
        preview = text[:200] + ('...' if len(text) > 200 else '')
        text_label = QLabel(preview)
        text_label.setFont(QFont('Segoe UI', 10))
        text_label.setWordWrap(True)
        text_label.setStyleSheet("color: #333;")
        text_label.setMaximumHeight(60)
        layout.addWidget(text_label)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.text)
        elif event.button() == Qt.RightButton:
            self.doubleClicked.emit(self.text)
        super().mousePressEvent(event)


class HistoryWindow(BaseWindow):
    """Window showing transcription history with click-to-replay."""
    replaySignal = pyqtSignal(str)    # replay (typewrite) a transcription
    copySignal = pyqtSignal(str)      # copy only (no typewrite)

    def __init__(self):
        super().__init__('WhisperWriter History', 420, 500)
        self.entries = []  # list of (text, timestamp) tuples
        self.initHistoryUI()

    def initHistoryUI(self):
        # Hint label
        self.hint_label = QLabel('Left click = paste into active window  |  Right click = copy only')
        self.hint_label.setFont(QFont('Segoe UI', 8))
        self.hint_label.setStyleSheet("color: #888;")
        self.hint_label.setAlignment(Qt.AlignCenter)
        self.main_layout.addWidget(self.hint_label)

        # Scroll area for entries
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background: transparent;
            }
            QScrollBar:vertical {
                width: 6px;
                background: transparent;
            }
            QScrollBar::handle:vertical {
                background: rgba(150, 150, 150, 100);
                border-radius: 3px;
            }
        """)

        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(4, 4, 4, 4)
        self.scroll_layout.setSpacing(4)
        self.scroll_layout.addStretch()

        self.scroll_area.setWidget(self.scroll_content)
        self.main_layout.addWidget(self.scroll_area)

        # Empty state
        self.empty_label = QLabel('No transcriptions yet.\nStart recording with F9.')
        self.empty_label.setFont(QFont('Segoe UI', 11))
        self.empty_label.setStyleSheet("color: #aaa;")
        self.empty_label.setAlignment(Qt.AlignCenter)
        self.scroll_layout.insertWidget(0, self.empty_label)

        # Clear button
        clear_btn = QPushButton('Clear History')
        clear_btn.setFont(QFont('Segoe UI', 9))
        clear_btn.setFixedHeight(30)
        clear_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(220, 220, 220, 180);
                border: none;
                border-radius: 6px;
                color: #666;
            }
            QPushButton:hover {
                background-color: rgba(255, 180, 180, 200);
                color: #900;
            }
        """)
        clear_btn.clicked.connect(self.clear_history)
        self.main_layout.addWidget(clear_btn)

    def add_entry(self, text):
        """Add a new transcription to the history."""
        timestamp = datetime.now().strftime('%H:%M:%S')
        self.entries.append((text, timestamp))

        # Remove empty state label
        if self.empty_label.isVisible():
            self.empty_label.hide()

        # Create entry widget (insert before the stretch)
        index = len(self.entries) - 1
        entry_widget = HistoryEntry(text, timestamp, index)
        entry_widget.clicked.connect(self._on_entry_clicked)
        entry_widget.doubleClicked.connect(self._on_entry_double_clicked)

        # Insert at top (most recent first)
        self.scroll_layout.insertWidget(0, entry_widget)

    def _on_entry_clicked(self, text):
        """Single click: copy to clipboard and replay."""
        QApplication.clipboard().setText(text.strip())
        self.replaySignal.emit(text)
        self.hide()  # Hide window so text goes to the right place

    def _on_entry_double_clicked(self, text):
        """Double click: copy to clipboard only."""
        QApplication.clipboard().setText(text.strip())
        # Brief visual feedback via tray notification would be nice,
        # but just clipboard copy is enough

    def clear_history(self):
        """Remove all entries."""
        self.entries.clear()
        # Remove all entry widgets
        while self.scroll_layout.count() > 1:  # keep the stretch
            item = self.scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.empty_label.show()
        self.scroll_layout.insertWidget(0, self.empty_label)

    def show(self):
        """Position window near system tray (bottom right) and show."""
        screen = QApplication.primaryScreen()
        screen_geometry = screen.availableGeometry()
        x = screen_geometry.right() - self.width() - 20
        y = screen_geometry.bottom() - self.height() - 20
        self.move(x, y)
        super().show()
        self.raise_()
        self.activateWindow()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = HistoryWindow()
    # Demo entries
    window.add_entry("This is a test transcription to see how it looks in the history window.")
    window.add_entry("Another transcription, this one is a bit longer to test word wrapping and see how the preview truncation works when there's a lot of text being displayed.")
    window.add_entry("Short one.")
    window.show()
    sys.exit(app.exec_())
