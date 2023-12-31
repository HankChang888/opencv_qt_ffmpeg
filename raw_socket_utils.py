import socket
import threading
import time
import ctypes
import binascii
import array
import numpy as np
from global_def import *

# Import ctypes and load the C library
raw_socket_lib = ctypes.CDLL('./raw_socket.so')
raw_socket_lib.send_raw_socket_packet.argtypes = [ctypes.POINTER(ctypes.c_ubyte), ctypes.c_int]
raw_socket_lib.send_raw_socket_packet.restype = ctypes.c_int
raw_socket_lib.set_raw_socket_init.argtypes = [ctypes.c_char_p]
raw_socket_lib.set_raw_socket_init.restype = ctypes.c_int
raw_socket_lib.send_rgb_frame_with_raw_socket.argtypes = [ctypes.POINTER(ctypes.c_ubyte), ctypes.c_int, ctypes.c_uint]
raw_socket_lib.send_rgb_frame_with_raw_socket.restype = ctypes.c_int

LP_c_ubyte = ctypes.POINTER(ctypes.c_ubyte)

def send_rgb_frame_with_raw_socket(rgb_frame, frame_id):
    
    if frame_id > 0xffff:
        print("frame_id out of 0xffff")
        return False
    
    rgb_frame_len = len(rgb_frame)
    rgb_frame_data = (ctypes.c_ubyte * rgb_frame_len).from_buffer(np.ascontiguousarray(rgb_frame))
    result = raw_socket_lib.send_rgb_frame_with_raw_socket(rgb_frame_data, rgb_frame_len, ctypes.c_uint(frame_id))
 
    
    return True

