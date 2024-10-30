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
from threading import Lock

send_lock = Lock()

FFMPEG_BIN = 'ffmpeg'


class VideoThreadFFMpeg(QThread):
    change_pixmap_signal = pyqtSignal(np.ndarray)
    #ffmpeg_change_pixmap_signal = pyqtSignal(np.ndarray)
    send_rgb_frame_signal = pyqtSignal(bytes, int)

    def __init__(self, video_src, display_width, display_height, video_type=None, parent=None):
        super().__init__(parent)
        self.video_src = video_src
        self.display_width = display_width
        self.display_height = display_height
        self.frame_count = 0
        self.raw_image = 0
    def run(self):
        width = str(self.display_width)
        height = str(self.display_height)
        scale_factor = 'scale=' + str(width) + ':' + str(height)
        pipe_sink = '-'
        
        command = [
            'ffmpeg',
            '-hide_banner',
            '-loglevel', 'info',
            '-hwaccel', 'auto',
            #'-hwaccel', 'v4l2m2m',
            '-stream_loop', '-1',
            '-re',
            '-i', self.video_src,
            #'-vf', f'{scale_factor},showinfo',
            '-vf',f'{scale_factor}',
            '-pix_fmt', 'rgb24',
            '-f', 'rawvideo',
            '-r', "30/1",
            '-stats',
            pipe_sink
        ] 
        command_str = ' '.join(command)
        log.debug("FFmpeg command line: %s", command_str)
        pipe = subprocess.Popen(command, stdout=subprocess.PIPE, bufsize=10 ** 9)
        while True:
            try:
                #start_time = time.time()
                self.raw_image = pipe.stdout.read(self.display_width * self.display_height * 3)
                #end_time = time.time()
                # send frame with raw socket
                #self.send_rgb_frame_signal.emit(self.raw_image, self.frame_count)
                with send_lock:
                    send_rgb_frame_with_raw_socket(self.raw_image, self.frame_count)

                image = np.frombuffer(self.raw_image, dtype='uint8')
                image = image.reshape((self.display_height, self.display_width, 3))
                
                # throw away the data in the pipe's buffer.
                pipe.stdout.flush()
                self.frame_count += 1
                if self.frame_count > 0xffff:
                    self.frame_count = 0

                self.change_pixmap_signal.emit(image)
                
                #if video_finished_condition:
                #self.video_finished_signal.emit() 
            except Exception as e:
                log.debug(e)
                # self.video_finished_signal.emit()

            # time.sleep(0.033)
