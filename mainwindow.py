import cv2
from PyQt5.QtCore import QThread, pyqtSignal, QDateTime, QObject, pyqtSlot
from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QLabel, QWidget, QHBoxLayout, QPushButton
from PyQt5.QtGui import QPixmap, QImage
from videothread_gst import VideoThreadGStreamer
import numpy as np
import time

# Set video source
video_src = "dance.mp4"  # 480P

class MainUi(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Qt Video Player")
        self.setFixedSize(1280, 960)

        # Initialize main window
        self.window = QWidget(self)
        self.setCentralWidget(self.window)

        # Set up image display
        self.image_label = QLabel(self.window)
        self.image_display_width = 640
        self.image_display_height = 480
        self.image_label.resize(self.image_display_width, self.image_display_height)

        # Set up main layout
        main_layout = QVBoxLayout(self.window)
        main_layout.addWidget(self.image_label)

        # Create buttons and add them to the layout
        button_layout = QHBoxLayout()
        self.play_button = QPushButton("PLAY")
        self.pause_button = QPushButton("PAUSE")
        self.stop_button = QPushButton("STOP")
        self.restart_button = QPushButton("RE-PLAY")

        button_layout.addWidget(self.play_button)
        button_layout.addWidget(self.pause_button)
        button_layout.addWidget(self.stop_button)
        button_layout.addWidget(self.restart_button)

        main_layout.addLayout(button_layout)

        # Create video playback thread
        self.thread = VideoThreadGStreamer(video_src, self.image_display_width, self.image_display_height)
        self.thread.change_pixmap_signal.connect(self.update_ffmpeg_image)

        # Connect buttons to their respective functions
        self.play_button.clicked.connect(self.play_video)
        self.pause_button.clicked.connect(self.pause_video)
        self.stop_button.clicked.connect(self.stop_video)
        self.restart_button.clicked.connect(self.restart_video)

    def play_video(self):
        """Play video"""
        if not self.thread.isRunning():
            self.thread.force_stop = False  # Reset stop status
            self.thread.start()
        else:
            self.thread.resume()

    def pause_video(self):
        """Pause video"""
        self.thread.pause()

    def stop_video(self):
        """Stop video"""
        self.thread.stop()
        self.image_label.clear()  # Clear the image display

    def restart_video(self):
        """Restart video"""
        self.stop_video()
        self.play_video()

    @pyqtSlot(np.ndarray)
    def update_ffmpeg_image(self, cv_img):
        """Update image display"""
        qt_img = self.convert_ffmpeg_qt(cv_img)
        self.image_label.setPixmap(qt_img)

    def convert_ffmpeg_qt(self, ffmpeg_img):
        """Convert OpenCV image to QPixmap"""
        h, w, ch = ffmpeg_img.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QImage(ffmpeg_img.data, w, h, bytes_per_line, QImage.Format_RGB888)
        p = convert_to_Qt_format.scaled(self.image_display_width, self.image_display_height)
        return QPixmap.fromImage(p)
