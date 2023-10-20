import time

from PyQt5 import QtGui
from PyQt5.QtWidgets import QWidget, QApplication, QLabel, QVBoxLayout
from PyQt5.QtGui import QPixmap
import sys
from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt, QThread
import numpy as np
import subprocess
from global_def import *
from raw_socket_utils import *
FFMPEG_BIN = 'ffmpeg'


class VideoThreadFFMpeg(QThread):
    change_pixmap_signal = pyqtSignal(np.ndarray)
    ffmpeg_change_pixmap_signal = pyqtSignal(np.ndarray)
    send_rgb_frame_signal = pyqtSignal(bytes, int)
    #video_finished_signal = pyqtSignal(np.ndarray)
    def __init__(self, video_src, display_width, display_height, video_type=None, parent=None):
        super().__init__(parent)
        self.video_src = video_src
        self.display_width = display_width
        self.display_height = display_height
        self.frame_count = 0

    def run(self):
        scale_factor = "scale=" + str(self.display_width) + ":" + str(self.display_height)
        command = [FFMPEG_BIN,
                   '-hide_banner',
                   '-stream_loop', '-1',
                   '-loglevel', 'error',
                   '-hwaccel', 'auto',
                   '-re',
                   '-i', self.video_src,
                   '-f', 'image2pipe',
                   '-pix_fmt', 'rgb24',
                   '-vcodec', 'rawvideo', '-vf', scale_factor, '-']
        pipe = subprocess.Popen(command, stdout=subprocess.PIPE, bufsize=10 ** 8)
        while True:
            try:
                self.raw_image = pipe.stdout.read(self.display_width * self.display_height * 3)
                
                if not self.raw_image:
                    # No data read from the pipe, redirect to /dev/null
                    #with open(os.devnull, 'wb') as devnull:
                    #    devnull.write(self.raw_image)
                    log.debug("No data read from the pipe.")
                    #continue  # Skip further processing

                # log.debug("type(self.raw_image) = %s", type(self.raw_image))
                # send frame with raw socket
                self.send_rgb_frame_signal.emit(self.raw_image, self.frame_count)
                # send_rgb_frame_with_raw_socket(self.raw_image, self.frame_count)
                # transform the byte read into a numpy array
                image = np.frombuffer(self.raw_image, dtype='uint8')
                image = image.reshape((self.display_height, self.display_width, 3))
                # throw away the data in the pipe's buffer.
                pipe.stdout.flush()
                self.frame_count += 1
                if self.frame_count > 0xffff:
                    self.frame_count = 0

                self.ffmpeg_change_pixmap_signal.emit(image)
                
                #if video_finished_condition:
                #self.video_finished_signal.emit() 
            except Exception as e:
                log.debug(e)
                # self.video_finished_signal.emit()

            # time.sleep(0.033)
