from pathlib import Path

from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QSlider, QListWidget, QFileDialog
)


class MusicPlayer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.files = []
        self.index = -1
        self.dragging = False

        self.player = QMediaPlayer(self)
        self.player.setVolume(70)

        root = QVBoxLayout(self)
        root.setContentsMargins(8, 4, 8, 4)

        top = QHBoxLayout()
        self.add_btn = QPushButton("＋ Music")
        self.toggle_btn = QPushButton("Library ▾")
        top.addWidget(self.add_btn)
        top.addWidget(self.toggle_btn)
        root.addLayout(top)

        self.library = QListWidget()
        self.library.setMaximumHeight(150)
        self.library.hide()
        root.addWidget(self.library)

        controls = QHBoxLayout()
        self.previous_btn = QPushButton("⏮")
        self.play_btn = QPushButton("▶")
        self.next_btn = QPushButton("⏭")
        self.title = QLabel("No track selected")
        self.title.setMinimumWidth(120)

        controls.addWidget(self.previous_btn)
        controls.addWidget(self.play_btn)
        controls.addWidget(self.next_btn)
        controls.addWidget(self.title, 1)
        root.addLayout(controls)

        timeline = QHBoxLayout()
        self.position = QSlider(Qt.Horizontal)
        self.position.setRange(0, 0)
        self.time_label = QLabel("0:00 / 0:00")
        self.volume = QSlider(Qt.Horizontal)
        self.volume.setRange(0, 100)
        self.volume.setValue(70)
        self.volume.setMaximumWidth(100)

        timeline.addWidget(self.position, 1)
        timeline.addWidget(self.time_label)
        timeline.addWidget(QLabel("🔊"))
        timeline.addWidget(self.volume)
        root.addLayout(timeline)

        self.add_btn.clicked.connect(self.add_files)
        self.toggle_btn.clicked.connect(self.toggle_library)
        self.previous_btn.clicked.connect(self.previous)
        self.play_btn.clicked.connect(self.toggle_play)
        self.next_btn.clicked.connect(self.next)
        self.library.itemDoubleClicked.connect(
            lambda item: self.play_index(self.library.row(item))
        )
        self.volume.valueChanged.connect(self.player.setVolume)
        self.position.sliderPressed.connect(self.start_seek)
        self.position.sliderReleased.connect(self.finish_seek)
        self.player.positionChanged.connect(self.update_position)
        self.player.durationChanged.connect(self.update_duration)
        self.player.stateChanged.connect(self.update_state)
        self.player.mediaStatusChanged.connect(self.media_status)

    def add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select Music", "",
            "Audio (*.wav *.mp3 *.flac *.m4a *.aac);;All Files (*)"
        )
        for path in paths:
            if path not in self.files:
                self.files.append(path)
                self.library.addItem(Path(path).name)
        if self.index == -1 and self.files:
            self.play_index(0)

    def toggle_library(self):
        visible = not self.library.isVisible()
        self.library.setVisible(visible)
        self.toggle_btn.setText(
            "Library ▴" if visible else "Library ▾"
        )

    def play_index(self, index):
        if not 0 <= index < len(self.files):
            return
        self.index = index
        path = self.files[index]
        self.player.setMedia(
            QMediaContent(QUrl.fromLocalFile(path))
        )
        self.title.setText(Path(path).name)
        self.library.setCurrentRow(index)
        self.player.play()

    def toggle_play(self):
        if self.player.state() == QMediaPlayer.PlayingState:
            self.player.pause()
        elif self.index >= 0:
            self.player.play()
        elif self.files:
            self.play_index(0)

    def previous(self):
        if self.files:
            self.play_index((self.index - 1) % len(self.files))

    def next(self):
        if self.files:
            self.play_index((self.index + 1) % len(self.files))

    def start_seek(self):
        self.dragging = True

    def finish_seek(self):
        self.player.setPosition(self.position.value())
        self.dragging = False

    def update_position(self, value):
        if not self.dragging:
            self.position.setValue(value)
        self.update_time()

    def update_duration(self, value):
        self.position.setRange(0, max(0, value))
        self.update_time()

    def update_time(self):
        def fmt(ms):
            seconds = max(0, ms // 1000)
            return f"{seconds // 60}:{seconds % 60:02d}"
        self.time_label.setText(
            f"{fmt(self.player.position())} / "
            f"{fmt(self.player.duration())}"
        )

    def update_state(self, state):
        self.play_btn.setText(
            "⏸" if state == QMediaPlayer.PlayingState else "▶"
        )

    def media_status(self, status):
        if status == QMediaPlayer.EndOfMedia:
            self.next()

    def closeEvent(self, event):
        self.player.stop()
        self.player.setMedia(QMediaContent())
        self.files.clear()
        super().closeEvent(event)
