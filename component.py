import pygame
from typing import Tuple


class Component:
    def __init__(self, size: Tuple[int], x: int = 0, y: int = 0):
        self.application = None
        self.surface = pygame.Surface(size)
        self.size = size
        self.x = x
        self.y = y

    def propagate_event(self, event): ...
    def update(self, dt): ...

    def draw_frame(self):
        self.get_application().window.blit(self.surface, (self.x, self.y))
        self.surface.fill((0, 0, 0))
    
    def get_application(self):
        return self.application
