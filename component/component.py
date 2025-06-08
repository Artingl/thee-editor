import pygame
from typing import Tuple


class Component:
    def __init__(self, app, size: Tuple[int], x: int = 0, y: int = 0):
        self.application = app
        self.surface = pygame.Surface(size)
        self.size = size
        self.children = []
        self.x = x
        self.y = y

    def propagate_event(self, event):
        for i in self.children:
            i.propagate_event(event)

    def update(self, dt):
        for i in self.children:
            i.update(dt)

    def reload(self):
        for i in self.children:
            i.reload()

    def add_child_component(self, component):
        component.application = self.application
        self.children.append(component)

    def remove_child_component(self, component):
        self.children.remove(component)

    def get_width(self):
        return self.surface.get_width()

    def get_height(self):
        return self.surface.get_height()

    def draw_frame(self):
        for i in self.children:
            i.draw_frame()
        
        self.get_application().window.blit(self.surface, (self.x, self.y))
        self.surface.fill((0, 0, 0))
    
    def get_application(self):
        return self.application
