import pygame
import sys
import time
import os
import json

from importlib import reload
from component import *
from editor import *
from font import draw_text

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
    def __init__(self, caption: str = "theeditor", config_path: str = "config.json"):
        self.config = {}
        self.config_last_save = time.time()
        self.config_path = config_path
        self.load_config()
        
        size = self.get_config_value("main", "window_dimensions", default=[900, 560])
        self.window = pygame.display.set_mode(size, pygame.RESIZABLE)
        self.timer = pygame.time.Clock()
        self.running = True
        self.is_restarting = False
        self.caption = caption
        self.components = []
        self.fps = 60

        self.editor = Editor(self)
        self.add_component(self.editor)

        import main, component, editor, font, syntax_highlighter
        self.hotreload = HotreloadWatchdog(main, component, editor, font, syntax_highlighter)
        
    def close(self):
        self.running = False
        self.save_config()

    def restart(self):
        self.running = False
        self.is_restarting = True
        self.save_config()

    def reload(self):
        if self.hotreload.try_to_reload():
            for i in self.components:
                i.reload()

    def save_config(self):
        with open(self.config_path, "w") as file:
            json.dump(self.config, file)

    def load_config(self):
        if os.path.isfile(self.config_path):
            with open(self.config_path, "r") as file:
                self.config = json.load(file)
    
    def store_config_value(self, key, param, value):
        if key not in self.config:
            self.config[key] = {}
        self.config[key][param] = value
    
    def get_config_value(self, key, param, default=None):
        if value := self.config.get(key):
            if found_value := value.get(param):
                return found_value
        return default

    def remove_config_value(self, key, param):
        if key in self.config:
            if param in self.config[key]:
                del self.config[key][param]

    def get_width(self):
        return self.window.get_width()

    def get_height(self):
        return self.window.get_height()
    
    def add_component(self, component):
        self.components.append(component)

    def update_frame(self):
        self.window.fill((0, 0, 0))
        for i in self.components:
            i.draw_frame()
            i.update(1 / self.fps)

        if self.get_config_value("main", "debug", default=False):
            text_size = self.get_config_value("editor", "text_size", default=1)
            debug_text = f"FPS: {round(self.timer.get_fps(), 1)}\n" + \
                         f"W: {self.window.get_width()}; H: {self.window.get_height()}\n" + \
                         "\n" + \
                         f"Opened file: '{self.editor.filename}'\n" + \
                         f"Mode: {self.editor.mode.value}"
            # Draw debug text
            draw_text(
                self.window,
                debug_text,
                (255, 255, 255),
                (120, 20, 20),
                40, 40,
                pixel_size=(text_size, text_size)
            )

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

            self.store_config_value("main", "window_dimensions", [self.window.get_width(), self.window.get_height()])
            
            # Save config every second
            if self.config_last_save < time.time():
                self.config_last_save = time.time() + 1
                self.save_config()

            pygame.display.flip()
            pygame.display.set_caption(self.caption)
            self.timer.tick(self.fps)
        pygame.quit()


if __name__ == "__main__":
    application = EditorApplication()
    application.run_loop()

    if application.is_restarting:
        os.execv(sys.executable, ['python'] + sys.argv)
    else:
        sys.exit(0)



