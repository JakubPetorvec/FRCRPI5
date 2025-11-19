import socket
import struct

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", 5800))

print("Listening on UDP 5800...")

while True:
    data, addr = sock.recvfrom(1024)

    if len(data) == 8:
        x, y = struct.unpack("ff", data)
        print(f"FROM {addr}: x={x:.2f}, y={y:.2f}")
    else:
        print("Unknown packet:", data)
