import socket
import threading
import time
import ctypes
import binascii
import array
from global_def import *

# Import ctypes and load the C library
raw_socket_lib = ctypes.CDLL('./raw_socket.so')
raw_socket_lib.send_raw_socket_packet.argtypes = [ctypes.POINTER(ctypes.c_ubyte), ctypes.c_int]
raw_socket_lib.send_raw_socket_packet.restype = ctypes.c_int
raw_socket_lib.set_raw_socket_init.argtypes = [ctypes.c_char_p]
raw_socket_lib.set_raw_socket_init.restype = ctypes.c_int

def send_raw_socket_packet( data, network_if=default_network_if, src=default_src, dst=default_dst, proto=default_proto):

	combined_data = dst + src + proto + data
	packet_sz = len(combined_data)
	packet_data_buffer = (ctypes.c_ubyte * packet_sz).from_buffer(bytearray(combined_data))

	if raw_socket_lib.send_raw_socket_packet(packet_data_buffer, packet_sz) == -1:
		print("Sending failed")

	#s.close()


def send_rgb_frame_with_raw_socket(rgb_frame, frame_id):
	# log.debug("len(rgb_frame) : %d", len(rgb_frame))
	if frame_id > 0xffff:
		log.debug("frame_id out of 0xffff")
		return False
	i = 0
	frame_id_bytes = int(frame_id).to_bytes(2, 'big')
	log.debug("frame_id : %d %s", frame_id, frame_id_bytes)
	sed_id = 0
	for i in range(0, len(rgb_frame), 1480):
		# log.debug("i : %d", i)
		frame_segment = rgb_frame[i:i+1480]
		seq_id_bytes = sed_id.to_bytes(2, 'big')
		data = frame_id_bytes + seq_id_bytes + frame_segment
		send_raw_socket_packet(data)
		sed_id += 1

	frame_segment = rgb_frame[i * 1480: len(rgb_frame) - 1]
	seq_id_bytes = sed_id.to_bytes(2, 'big')
	data = frame_id_bytes + seq_id_bytes + frame_segment
	send_raw_socket_packet(data)
	return True





