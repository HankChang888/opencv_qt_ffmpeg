import platform
from PyQt5 import QtGui
from PyQt5.QtCore import pyqtSignal, QThread
import numpy as np
import gi
from raw_socket_utils import send_rgb_frame_with_raw_socket
from threading import Lock

gi.require_version('Gst', '1.0')
from gi.repository import Gst

send_lock = Lock()

# Initialize GStreamer
Gst.init(None)


class VideoThreadGStreamer(QThread):
    change_pixmap_signal = pyqtSignal(np.ndarray)
    send_rgb_frame_signal = pyqtSignal(bytes, int)

    def __init__(self, video_src, display_width, display_height, parent=None):
        super().__init__(parent)
        self.video_src = video_src
        self.display_width = display_width
        self.display_height = display_height
        self.frame_count = 0
        self.videosink = "glimagesink"  # Default videosink set to glimagesink for x86 architecture

    def run(self):
        width = str(self.display_width)
        height = str(self.display_height)
        arch = platform.machine()

        # Select appropriate videosink depending on the architecture
        if 'x86' in arch:
            # Use glimagesink for x86 architecture
            pipeline_str = (
                f'filesrc location={self.video_src} ! decodebin ! videoconvert ! videoscale ! tee name=t '
                f't. ! queue ! video/x-raw,format=RGB,width={width},height={height} ! appsink name=appsink_sink '  # Explicitly naming appsink
                f't. ! queue ! video/x-raw,width={width},height={height},framerate=30/1 ! {self.videosink} sync=True'
            )
        else:
            #    # For non-x86 architecture (e.g., ARM with I.MX platform), use hardware decoding
            pipeline_str = (
                f'filesrc location={self.video_src} ! qtdemux name=d d.video_0 ! queue ! h264parse ! vpudec ! '
                f'imxvideoconvert_g2d ! videoscale ! video/x-raw,width={width},height={height} ! videoconvert ! '
                f'video/x-raw,format=RGB ! videorate ! video/x-raw,framerate=30/1 ! appsink name=appsink_sink'
            )

        # Create GStreamer pipeline
        pipeline = Gst.parse_launch(pipeline_str)

        # Retrieve the appsink element and set properties
        appsink = pipeline.get_by_name('appsink_sink')  # Ensure we get the correct appsink element
        appsink.set_property('emit-signals', True)  # Enable signal emission for frame data capture
        appsink.set_property('sync', True)  # Prevent appsink from blocking the pipeline
        appsink.connect('new-sample', self.on_new_sample)  # Connect the new-sample signal handler

        pipeline.set_state(Gst.State.PLAYING)

        # GStreamer main loop to handle bus messages
        bus = pipeline.get_bus()
        while True:
            msg = bus.timed_pop_filtered(100 * Gst.MSECOND, Gst.MessageType.ERROR | Gst.MessageType.EOS)

            if msg is not None:
                if msg.type == Gst.MessageType.ERROR:
                    err, debug = msg.parse_error()
                    if err:
                        print(f'Error: {err}, {debug}')
                    break

                elif msg.type == Gst.MessageType.EOS:
                    print('End of stream, restarting...')
                    break
            else:
                continue

        # Stop the pipeline
        pipeline.set_state(Gst.State.NULL)

    def on_new_sample(self, sink):
        # Capture frame data from appsink
        sample = sink.emit('pull-sample')
        buf = sample.get_buffer()
        caps = sample.get_caps()
        width = caps.get_structure(0).get_value('width')
        height = caps.get_structure(0).get_value('height')
        # Extract frame data from the buffer
        result, map_info = buf.map(Gst.MapFlags.READ)
        if result:
            frame_data = np.frombuffer(map_info.data, dtype=np.uint8)
            frame_data = frame_data.reshape((height, width, 3))

            # Send frame data using raw socket
            with send_lock:
                send_rgb_frame_with_raw_socket(frame_data.tobytes(), self.frame_count)

            # Emit signal to update the UI
            self.change_pixmap_signal.emit(frame_data)
            buf.unmap(map_info)

        self.frame_count += 1
        if self.frame_count > 0xffff:
            self.frame_count = 0
        return Gst.FlowReturn.OK
