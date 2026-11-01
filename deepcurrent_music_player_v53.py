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
        self.remote_tracks = []
        self.library_mode = "local"
        self.playback_mode = "local"
        self.remote_index = -1
        self.index = -1
        self.dragging = False

        self.player = QMediaPlayer(self)
        self.player.setVolume(70)

        root = QHBoxLayout(self)
        root.setContentsMargins(8, 4, 8, 4)
        root.setSpacing(6)

        self.add_btn = QPushButton("＋ Music")
        self.toggle_btn = QPushButton("Library")
        self.remote_btn = QPushButton("London Library")

        self.previous_btn = QPushButton("⏮")
        self.play_btn = QPushButton("▶")
        self.next_btn = QPushButton("⏭")

        self.title = QLabel("No track selected")
        self.title.setMinimumWidth(120)

        self.volume = QSlider(Qt.Horizontal)
        self.volume.setRange(0, 100)
        self.volume.setValue(70)
        self.volume.setFixedWidth(85)

        self.position = QSlider(Qt.Horizontal)
        self.position.setRange(0, 0)
        self.time_label = QLabel("0:00 / 0:00")

        self.library = QListWidget()
        self.library.hide()

        self.library_window = QWidget()
        self.library_window.setWindowTitle("DeepCurrent Music Library")
        self.library_window.resize(650, 420)

        floating_layout = QVBoxLayout(self.library_window)
        floating_layout.setContentsMargins(8, 8, 8, 8)
        floating_layout.addWidget(self.library)

        root.addWidget(self.add_btn)
        root.addWidget(self.toggle_btn)
        root.addWidget(self.remote_btn)
        root.addWidget(self.previous_btn)
        root.addWidget(self.play_btn)
        root.addWidget(self.next_btn)
        root.addWidget(self.title, 1)
        root.addWidget(QLabel("🔊"))
        root.addWidget(self.volume)

        self.remote_btn.clicked.connect(self.load_remote_library)
        self.add_btn.clicked.connect(self.add_files)
        self.toggle_btn.clicked.connect(self.toggle_library)
        self.previous_btn.clicked.connect(self.previous)
        self.play_btn.clicked.connect(self.toggle_play)
        self.next_btn.clicked.connect(self.next)
        self.library.itemDoubleClicked.connect(
            self.play_selected_track
        )
        self.volume.valueChanged.connect(self.player.setVolume)
        self.position.sliderPressed.connect(self.start_seek)
        self.position.sliderReleased.connect(self.finish_seek)
        self.player.positionChanged.connect(self.update_position)
        self.player.durationChanged.connect(self.update_duration)
        self.player.stateChanged.connect(self.update_state)
        self.player.mediaStatusChanged.connect(self.media_status)

    def load_remote_library(self):
        self.remote_btn.setText("Loading…")
        self.remote_btn.setEnabled(False)
        self.remote_library_requested()

    def remote_library_requested(self):
        self.remote_btn.setText("London Library")
        self.remote_btn.setEnabled(True)
        self.title.setText("Open Music Station to load library")

    def show_remote_tracks(self, tracks):
        self.remote_tracks = tracks
        self.library_mode = "remote"
        self.remote_index = -1
        self.library.clear()
        for track in tracks:
            self.library.addItem(
                f"{track.get('artist', '')} — {track.get('name', '')}"
            )
        self.library.show()
        self.library_window.show()
        self.library_window.raise_()
        self.remote_btn.setText("London Library")
        self.remote_btn.setEnabled(True)
        self.title.setText(f"{len(tracks)} London tracks")

    def add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select Music", "",
            "Audio (*.wav *.mp3 *.flac *.m4a *.aac);;All Files (*)"
        )

        if not paths:
            return

        if self.library_mode != "local":
            self.library.clear()
            self.library_mode = "local"
            for path in self.files:
                self.library.addItem(Path(path).name)

        for path in paths:
            if path not in self.files:
                self.files.append(path)
                self.library.addItem(Path(path).name)

        if self.index == -1 and self.files:
            self.play_index(0)

    def toggle_library(self):
        visible = not self.library.isVisible()
        if visible:
            self.library.show()
            self.library_window.show()
            self.library_window.raise_()
        else:
            self.library_window.hide()
        self.toggle_btn.setText(
            "Library ▴" if visible else "Library ▾"
        )

    def play_selected_track(self, item):
        index = self.library.row(item)

        if self.library_mode == "remote":
            self.play_remote_index(index)
        else:
            self.play_index(index)

    def play_remote_index(self, index):
        if not 0 <= index < len(self.remote_tracks):
            return

        self.remote_index = index
        self.library.setCurrentRow(index)
        self.remote_track_requested(self.remote_tracks[index])

    def remote_toggle_requested(self):
        print("Remote toggle not connected", flush=True)

    def remote_track_requested(self, track):
        self.title.setText("Remote playback not connected")

    def play_index(self, index):
        if not 0 <= index < len(self.files):
            return
        self.playback_mode = "local"
        if hasattr(self, "remote_stop_requested"):
            self.remote_stop_requested()
        self.index = index
        path = self.files[index]
        self.player.setMedia(
            QMediaContent(QUrl.fromLocalFile(path))
        )
        self.title.setText(Path(path).name)
        if self.library_mode == "local":
            self.library.setCurrentRow(index)
        self.player.play()

    def toggle_play(self):
        if getattr(self, "playback_mode", "local") == "remote":
            self.remote_toggle_requested()
            return

        if self.player.state() == QMediaPlayer.PlayingState:
            self.player.pause()
        elif self.index >= 0:
            self.player.play()
        elif self.files:
            self.play_index(0)

    def previous(self):
        if self.playback_mode == "remote":
            if self.remote_tracks:
                index = (
                    self.remote_index - 1
                ) % len(self.remote_tracks)
                self.play_remote_index(index)
            return

        if self.files:
            self.play_index((self.index - 1) % len(self.files))

    def next(self):
        if self.playback_mode == "remote":
            if self.remote_tracks:
                index = (
                    self.remote_index + 1
                ) % len(self.remote_tracks)
                self.play_remote_index(index)
            return

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
        if self.playback_mode == "remote":
            return
        self.play_btn.setText(
            "⏸" if state == QMediaPlayer.PlayingState else "▶"
        )

    def media_status(self, status):
        if (
            self.playback_mode == "local"
            and status == QMediaPlayer.EndOfMedia
        ):
            self.next()

    def closeEvent(self, event):
        self.player.stop()
        self.player.setMedia(QMediaContent())
        self.files.clear()
        super().closeEvent(event)
