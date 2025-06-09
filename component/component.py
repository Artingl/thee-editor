import pygame
from typing import List


class Component:
    def __init__(self, app, position=(0, 0), is_headless=False):
        self.application = app
        self.position = position
        self.is_headless = is_headless
        if not is_headless:
            self.surface = pygame.Surface((1, 1))
        self.is_focused = False
        self.children: List[Component] = []

    def propagate_event(self, event):
        for i in self.children:
            i.propagate_event(event)

    def update(self, dt):
        for i in self.children:
            i.update(dt)

    def reload(self):
        for i in self.children:
            i.reload()

    def key_up_event(self, key, unicode, modifier):
        for i in self.children:
            i.key_up_event(key, unicode, modifier)

    def key_down_event(self, key, unicode, modifier):
        for i in self.children:
            i.key_down_event(key, unicode, modifier)

    def key_pressed_event(self, key, unicode, modifier):
        for i in self.children:
            i.key_pressed_event(key, unicode, modifier)

    def mouse_wheel_event(self, x, y):
        for i in self.children:
            i.mouse_wheel_event(x, y)
    
    def draw(self):
        if self.is_headless:
            return
        for i in self.children:
            i.draw_frame(self.surface)

    def cleanup(self):
        for i in self.children:
            i.cleanup()

    def add_child_component(self, component):
        component.application = self.application
        self.children.append(component)

    def remove_child_component(self, component):
        self.children.remove(component)

    def get_width(self):
        if self.is_headless:
            return 0
        return self.surface.get_width()

    def get_height(self):
        if self.is_headless:
            return 0
        return self.surface.get_height()

    def update_dimensions(self, size, position):
        if self.is_headless:
            return
        if size != (self.surface.get_width(), self.surface.get_height()):
            self.surface = pygame.Surface(size)
            self.current_size = size
        self.position = position

    def draw_frame(self, surface):
        if self.is_headless:
            return
        self.draw()
        surface.blit(self.surface, self.position)
        self.surface.fill((0, 0, 0))
    
    def get_application(self):
        return self.application
