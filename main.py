import pygame
import sys
import time
import os

from importlib import reload
from component import *
from editor import *
from syntax_highlighter import *

pygame.init()


class HotreloadWatchdog:
    def __init__(self, *hotreload_modules):
        self.modules = hotreload_modules
        self.file_updates = [(i, os.stat(i.__file__).st_mtime) for i in self.modules]
        self.last_reload = 0
    
    def try_to_reload(self):
        # Only hot-reload once every 0.2 second
        if self.last_reload < time.time():
            self.last_reload = time.time() + 0.2
            reloaded = 0

            for idx, i in enumerate(self.file_updates):
                module, st_mtime = i
                if os.stat(module.__file__).st_mtime != st_mtime:
                    self.file_updates[idx] = module, os.stat(module.__file__).st_mtime
                    reload(module)
                    print(f"Module {module.__name__} reloaded!") 
                    reloaded += 1
            
            if reloaded > 0:
                print(f"Total reloaded modules: {reloaded}")
                return True

        return False


class EditorApplication:
    def __init__(self, caption: str = "Unnamed"):
        self.window = pygame.display.set_mode((800, 600), pygame.RESIZABLE)
        self.timer = pygame.time.Clock()
        self.running = True
        self.caption = caption
        self.components = []
        self.fps = 120

        self.editor = Editor("syntax_highlighter.py", PySyntaxHighlighter)
        self.add_component(self.editor)

        import main, component, editor, font, syntax_highlighter
        self.hotreload = HotreloadWatchdog(main, component, editor, font, syntax_highlighter)

    def add_component(self, component):
        self.components.append(component)
        component.application = self

    def update_frame(self):
        self.window.fill((0, 0, 0))

        for i in self.components:
            i.draw_frame()
            i.update(1 / self.fps)

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
            
            if self.hotreload.try_to_reload():
                for i in self.components:
                    i.reload()

            pygame.display.flip()
            pygame.display.set_caption(f"{self.caption} - FPS: {round(self.timer.get_fps(), 1)}")
            self.timer.tick(self.fps)
        pygame.quit()


if __name__ == "__main__":
    application = EditorApplication("theeditor")
    application.run_loop()
    sys.exit(0)
