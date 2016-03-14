"""A basic example of using hug.use.Socket to return data from raw sockets"""
import hug
import socket
import struct
import time


http_socket = hug.use.Socket(connect_to=('www.google.com', 80), proto='tcp', pool=4, timeout=10.0)
ntp_service = hug.use.Socket(connect_to=('127.0.0.1', 123), proto='udp', pool=4, timeout=10.0)


EPOCH_START = 2208988800
@hug.get()
def get_time():
    """Get time from a locally running NTP server"""

    time_request = '\x1b' + 47 * '\0'
    now = struct.unpack("!12I", ntp_service.request(time_request, timeout=5.0).data.read())[10]
    return time.ctime(now - EPOCH_START)


@hug.get()
def reverse_http_proxy(length: int=100):
    """Simple reverse http proxy function that returns data/html from another http server (via sockets)
    only drawback is the peername is static, and currently does not support being changed.
    Example: curl localhost:8000/reverse_http_proxy?length=400"""

    http_request = """
GET / HTTP/1.0\r\n\r\n
Host: www.google.com\r\n\r\n
\r\n\r\n
"""
    return http_socket.request(http_request, timeout=5.0).data.read()[0:length]
