import pygame
import sys

from component import *
from editor import *

pygame.init()


class EditorApplication:
    def __init__(self, caption: str = "Unnamed"):
        self.window = pygame.display.set_mode((800, 600), pygame.RESIZABLE)
        self.timer = pygame.time.Clock()
        self.running = True
        self.caption = caption
        self.components = []

        self.editor = Editor()
        self.add_component(self.editor)

    def add_component(self, component):
        self.components.append(component)
        component.application = self

    def update_frame(self):
        self.window.fill((0, 0, 0))

        for i in self.components:
            i.draw_frame()
            i.update(1 / 60)

    def process_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            if event.type == pygame.VIDEORESIZE:
                self.window = pygame.display.set_mode((event.w, event.h), pygame.RESIZABLE)
            for i in self.components:
                i.propagate_event(event)
    
    def run_loop(self):
        while self.running:
            self.process_events()
            self.update_frame()

            pygame.display.flip()
            pygame.display.set_caption(f"{self.caption} - FPS: {round(self.timer.get_fps(), 1)}")
            self.timer.tick(60)
        pygame.quit()



if __name__ == "__main__":
    application = EditorApplication("theeditor")
    application.run_loop()
    sys.exit(0)
