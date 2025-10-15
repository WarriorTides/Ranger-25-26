import time
import socket

UDP_IP = "127.0.0.1"  
UDP_PORT = 5005

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def send(cmd):
    sock.sendto(cmd.encode(), (UDP_IP, UDP_PORT))
    print(f"Sent: {cmd}")


for i in range(5):
    send("c")
    time.sleep(1)
    send("o")
    time.sleep(1)
