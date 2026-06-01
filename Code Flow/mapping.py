import pygame

pygame.init()
pygame.joystick.init()

joystick = pygame.joystick.Joystick(0)
joystick.init()
print(f"Controller: {joystick.get_name()}")
print("Press d-pad in any direction...")

running = True
while running:
    for event in pygame.event.get():
        if event.type in (pygame.JOYHATMOTION, pygame.JOYBUTTONDOWN, pygame.JOYAXISMOTION):
            print(event)
