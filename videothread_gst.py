import platform
from PyQt5.QtCore import pyqtSignal, QThread
import numpy as np
import gi
from raw_socket_utils import send_rgb_frame_with_raw_socket
from threading import Lock

gi.require_version('Gst', '1.0')
from gi.repository import Gst

# Initialize GStreamer
Gst.init(None)
send_lock = Lock()

class VideoThreadGStreamer(QThread):
    change_pixmap_signal = pyqtSignal(np.ndarray)
    send_rgb_frame_signal = pyqtSignal(bytes, int)

    def __init__(self, video_src, display_width, display_height, parent=None):
        super().__init__(parent)
        self.video_src = video_src
        self.display_width = display_width
        self.display_height = display_height
        self.frame_count = 0
        self.paused = False
        self.pipeline = None
        self.force_stop = False  # Controls complete stop status

    def build_pipeline(self):
        """Build the GStreamer pipeline"""
        width, height = str(self.display_width), str(self.display_height)
        arch = platform.machine()

        # Choose the appropriate pipeline configuration
        if 'x86' in arch:
            pipeline_str = (
                f'filesrc location={self.video_src} ! decodebin ! videoconvert ! videoscale ! '
                f'video/x-raw,format=RGB,width={width},height={height} ! appsink name=appsink_sink'
            )
        else:
            pipeline_str = (
                f'filesrc location={self.video_src} ! qtdemux name=d d.video_0 ! queue ! h264parse ! vpudec ! '
                f'imxvideoconvert_g2d ! videoscale ! video/x-raw,width={width},height={height} ! videoconvert ! '
                f'video/x-raw,format=RGB ! videorate ! video/x-raw,framerate=30/1 ! appsink name=appsink_sink'
            )

        # Create and return the GStreamer pipeline
        self.pipeline = Gst.parse_launch(pipeline_str)

        # Set appsink properties and connect signal
        appsink = self.pipeline.get_by_name('appsink_sink')
        appsink.set_property('emit-signals', True)
        appsink.set_property('sync', True)
        appsink.connect('new-sample', self.on_new_sample)

    def run(self):
        # Build the pipeline
        self.build_pipeline()
        self.pipeline.set_state(Gst.State.PLAYING)
        bus = self.pipeline.get_bus()

        while not self.force_stop:
            if self.paused:
                self.pipeline.set_state(Gst.State.PAUSED)
            else:
                self.pipeline.set_state(Gst.State.PLAYING)

            msg = bus.timed_pop_filtered(100 * Gst.MSECOND, Gst.MessageType.ERROR | Gst.MessageType.EOS)
            if msg:
                if msg.type == Gst.MessageType.ERROR:
                    err, debug = msg.parse_error()
                    print(f'Error: {err}, {debug}')
                    break
                elif msg.type == Gst.MessageType.EOS:
                    print('End of stream, restarting...')
                    break

        # Stop and clear the pipeline
        self.pipeline.set_state(Gst.State.NULL)
        self.pipeline = None

    def on_new_sample(self, sink):
        sample = sink.emit('pull-sample')
        buf = sample.get_buffer()
        caps = sample.get_caps()
        width = caps.get_structure(0).get_value('width')
        height = caps.get_structure(0).get_value('height')
        result, map_info = buf.map(Gst.MapFlags.READ)

        if result:
            frame_data = np.frombuffer(map_info.data, dtype=np.uint8).reshape((height, width, 3))
            with send_lock:
                send_rgb_frame_with_raw_socket(frame_data.tobytes(), self.frame_count)

            self.change_pixmap_signal.emit(frame_data)
            buf.unmap(map_info)

        self.frame_count = (self.frame_count + 1) % 0xffff
        return Gst.FlowReturn.OK

    def pause(self):
        """Pause video playback"""
        self.paused = True

    def resume(self):
        """Resume video playback"""
        self.paused = False

    def stop(self):
        """Stop video playback and completely release the pipeline"""
        self.paused = False
        self.force_stop = True
        self.quit()
        self.wait()
        self.pipeline = None

    def restart(self):
        """Restart video playback"""
        if self.isRunning():
            self.stop()
        self.force_stop = False
        self.start()
