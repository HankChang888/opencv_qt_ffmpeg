import cv2
from PyQt5.QtCore import QThread, pyqtSignal, QDateTime, QObject
from PyQt5.QtWidgets import QMainWindow, QGridLayout, QFrame, QLabel, QWidget
# from videothread import *
from videothread_ffmpeg import *
from videothread_gst import *

#video_src = "color_bar_test.mp4" #720P
#video_src = "countdown.mp4"
#video_src = "countdown_480p.mp4"
video_src = "dance.mp4" #480P
#video_src = "/home/venom/Videos/character.mp4"
#video_src = "/home/venom/Videos/BlackChat.mp4"
#video_src = "/home/venom/Videos/RED.mp4"
class MainUi(QMainWindow):
	def __init__(self):
		super().__init__()
		# self.center()
		self.setWindowTitle("Qt static label demo")
		self.window = QWidget(self)
		self.setCentralWidget(self.window)

		self.send_raw_over_count = 0
		self.send_raw_under_count = 0

		self.setFixedSize(1280, 960)

		self.pre_time = None
		self.now_time = None
		self.del_time = None
		self.total_del_time = 0
		self.avg_del_time = None

		self.send_raw_start_time = None
		self.send_raw_end_time = None
		self.send_raw_delta_time = None
		self.send_raw_total_time = 0
		self.send_raw_avg_time = None
		self.frame_count = 0
		self.frame_total = 0

		self.image_label = QLabel(self.window)
		self.image_display_width = 640 #640 #1280
		self.image_display_height = 480 #480 #720
		self.image_label.resize(self.image_display_width, self.image_display_height)
		# self.image_label.setText("TEST")
		grid_layout = QVBoxLayout()
		grid_layout.addWidget(self.image_label)
		self.window.setLayout(grid_layout)

		# self.thread = VideoThread(video_src)
		# connect its signal to the update_image slot
		# self.thread.change_pixmap_signal.connect(self.update_image)

		#self.thread = VideoThreadFFMpeg(video_src, self.image_display_width, self.image_display_height)
		#self.thread.change_pixmap_signal.connect(self.update_ffmpeg_image)

		self.thread = VideoThreadGStreamer(video_src, self.image_display_width, self.image_display_height)
		self.thread.change_pixmap_signal.connect(self.update_ffmpeg_image)


		#self.thread.video_finished_signal.connect(self.restart_video)
		if raw_socket_lib.set_raw_socket_init(ctypes.c_char_p(default_network_if.encode('utf-8'))) == -1:
			print("raw socket init failed")
		else:
			print("raw socket init succeeded")

		#self.thread.send_rgb_frame_signal.connect(self.send_raw_image)

		# start the thread
		self.thread.setPriority(QThread.HighestPriority)
		self.thread.start()

	@pyqtSlot(np.ndarray)
	def restart_video(self):
		self.thread.start()

	@pyqtSlot(np.ndarray)
	def update_image(self, cv_img):
		"""Updates the image_label with a new opencv image"""
		qt_img = self.convert_cv_qt(cv_img)
		self.image_label.setPixmap(qt_img)
		if self.pre_time is None:
			self.pre_time = time.time()
		self.now_time = time.time()
		self.del_time = self.now_time - self.pre_time
		self.pre_time = self.now_time
		self.total_del_time += self.del_time
		self.frame_count += 1
		self.avg_del_time = self.total_del_time/self.frame_count
		print("cv del_time = ", self.del_time, ", avg_del_time = ", self.avg_del_time)

	@pyqtSlot(np.ndarray)
	def update_ffmpeg_image(self, cv_img):
		"""Updates the image_label with a new opencv image"""

		qt_img = self.convert_ffmpeg_qt(cv_img)
		self.image_label.setPixmap(qt_img)
		# print("convert_ffmpeg_qt")
		if self.pre_time is None:
			self.pre_time = time.time()
		self.now_time = time.time()
		self.del_time = self.now_time - self.pre_time
		self.pre_time = self.now_time
		self.total_del_time += self.del_time
		self.frame_count += 1
		self.avg_del_time = self.total_del_time / self.frame_count
		# print("ffmpeg del_time = ", self.del_time, ", avg_del_time = ", self.avg_del_time)

	def convert_cv_qt(self, cv_img):
		"""Convert from an opencv image to QPixmap"""
		# print("convert_cv_qt")

		rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
		h, w, ch = rgb_image.shape
		bytes_per_line = ch * w
		convert_to_Qt_format = QtGui.QImage(rgb_image.data, w, h, bytes_per_line, QtGui.QImage.Format_RGB888)
		p = convert_to_Qt_format.scaled(self.image_display_width, self.image_display_height, Qt.KeepAspectRatio)
		return QPixmap.fromImage(p)

	def convert_ffmpeg_qt(self, ffmpeg_img):
		"""Convert from an opencv image to QPixmap"""
		# rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
		h, w, ch = ffmpeg_img.shape
		bytes_per_line = ch * w
		convert_to_Qt_format = QtGui.QImage(ffmpeg_img.data, w, h, bytes_per_line, QtGui.QImage.Format_RGB888)
		p = convert_to_Qt_format.scaled(self.image_display_width, self.image_display_height, Qt.KeepAspectRatio)
		return QPixmap.fromImage(p)
    
	def send_raw_image(self, rgb_frame, frame_id):
		self.send_raw_start_time = time.time()
		send_rgb_frame_with_raw_socket(rgb_frame, frame_id)
		self.send_raw_end_time = time.time()
		self.send_raw_delta_time = self.send_raw_end_time - self.send_raw_start_time
		self.send_raw_total_time += self.send_raw_delta_time
		self.frame_total +=1

		if self.send_raw_delta_time <= 0.033:
			self.send_raw_under_count += 1
		else:
			self.send_raw_over_count += 1
			log.debug("FID:%s exceeding:%s delta time:%s fps:%s", frame_id , self.send_raw_over_count, self.send_raw_delta_time, 1/self.send_raw_delta_time)
			
		if frame_id == 0:
			self.send_raw_max_time = self.send_raw_delta_time
			self.send_raw_min_time = self.send_raw_delta_time
		else:
			self.send_raw_max_time = max(self.send_raw_max_time, self.send_raw_delta_time)
			self.send_raw_min_time = min(self.send_raw_min_time, self.send_raw_delta_time)
		
		self.send_raw_avg_time = self.send_raw_total_time/(self.frame_total)

		#log.debug("FID:%s", frame_id)
		#log.debug("send raw delta time: %s", self.send_raw_delta_time)
		#log.debug("Maximum delta time: %s", self.send_raw_max_time)
		#log.debug("Minimum delta time: %s", self.send_raw_min_time)
		#log.debug("send raw tatal time: %s", self.send_raw_total_time)
		#log.debug("send raw avg delta: %s", self.send_raw_avg_time)
