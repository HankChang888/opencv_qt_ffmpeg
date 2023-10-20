import log_utils
import socket
log = log_utils.logging_init(__file__)

ETH_P_ALL = 3
default_network_if = 'eth0'
default_src = b'\x00\x22\x33\x44\x55\x66'
default_dst = b'\x11\x22\x33\x44\x55\x66'
default_proto = b'\x88\xb5'

raw_socket = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(ETH_P_ALL))
raw_socket.bind((default_network_if, 0))
