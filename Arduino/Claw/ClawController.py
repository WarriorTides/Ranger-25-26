import pygame
import socket
import time

UDP_IP = "192.168.86.51" 
UDP_PORT = 5005
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

pygame.init()
pygame.joystick.init()
joystick = pygame.joystick.Joystick(0)
joystick.init()

print(f"Controller ready. Sending UDP to {UDP_IP}:{UDP_PORT}")

TRIGGER_THRESHOLD = 0.5
l2_prev_state = False
claw_closed = False
claw_angle = 0  # FOR ONLY Claw 1

l3_prev_state = False
claw_closed_3 = False
claw_angle_3 = 0  # FOR ONLY Claw 2

while True:
    pygame.event.pump()


    l2 = joystick.get_axis(4)
    l2_pressed = l2 > TRIGGER_THRESHOLD

    if l2_pressed and not l2_prev_state:
        if claw_closed:
            sock.sendto(b"O", (UDP_IP, UDP_PORT))
            print("Sent: O  CLAW 1 OPEN")
            claw_closed = False
        else:
            sock.sendto(b"C", (UDP_IP, UDP_PORT))
            print("Sent: C  CLAW 1 CLOSED")
            claw_closed = True
    l2_prev_state = l2_pressed

    l3 = joystick.get_axis(5)
    l3_pressed = l3 > TRIGGER_THRESHOLD

    if l3_pressed and not l3_prev_state:
        if claw_closed_3:
            sock.sendto(b"o", (UDP_IP, UDP_PORT))
            print("Sent: o  CLAW 2 OPEN")
            claw_closed_3 = False  
        else:
            sock.sendto(b"c", (UDP_IP, UDP_PORT))
            print("Sent: c  CLAW 2 CLOSED")
            claw_closed_3 = True
    l3_prev_state = l3_pressed

    if joystick.get_button(9):  
        new_angle = min(180, claw_angle + 5)
        if new_angle != claw_angle:
            claw_angle = new_angle
            sock.sendto(b"U", (UDP_IP, UDP_PORT))
            print(f"Sent: U (angle now {claw_angle}) CLAW 1")

    if joystick.get_button(11): 
        new_angle = max(0, claw_angle - 5)
        if new_angle != claw_angle:
            claw_angle = new_angle
            sock.sendto(b"D", (UDP_IP, UDP_PORT))
            print(f"Sent: D (angle now {claw_angle}) CLAW 1")

    if joystick.get_button(10): 
        new_angle = min(180, claw_angle_3 + 5)
        if new_angle != claw_angle_3:
            claw_angle_3 = new_angle
            sock.sendto(b"u", (UDP_IP, UDP_PORT))
            print(f"Sent: u (angle now {claw_angle_3}) CLAW 2")

    if joystick.get_button(3): 
        new_angle = max(0, claw_angle_3 - 5)
        if new_angle != claw_angle_3:
            claw_angle_3 = new_angle
            sock.sendto(b"d", (UDP_IP, UDP_PORT))
            print(f"Sent: d (angle now {claw_angle_3}) CLAW 2")

    time.sleep(0.08)