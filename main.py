import pygame
import sys
import time
import os
import json
import builtins
import logging
import pyperclip

from importlib import reload
from component import VStackComponent
from engine.command import CommandExecutor
from engine.shell import EditorViewportComponent, Statusbar, BufferMode
from utils import FontDriver, FontType

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


class LoggerHandler(logging.Handler):
    def __init__(self, application):
        super().__init__()
        self.application = application
        self.original_print = print
        self.log_history = []
        
        builtins.print = self.__print_wrapper
            
    def get_log_history(self):
        return self.log_history

    def emit(self, record):
        msg = self.format(record)
        self.log_history.append(msg[:80] + ("..." if len(msg) > 80 else ""))
        self.log_history = self.log_history[-20:]

    def __print_wrapper(self, text='', *args, **kwargs):
        # TODO: implement kwargs
        text = str(text)
        log_history_text = ' '.join([text] + [str(i) for i in args])
        if len(log_history_text) > 80:
            log_history_text = log_history_text[:80] + "..."
        self.log_history.append(log_history_text)
        self.log_history = self.log_history[-20:]
        self.original_print(text, *args, **kwargs)


class EditorApplication:
    def __init__(self, caption: str = "thee-editor", config_path: str = "config.json"):
        self.logger_handler = LoggerHandler(self)

        self.logger = logging.getLogger()
        self.logger.setLevel(logging.DEBUG)
        self.logger.addHandler(self.logger_handler)

        self.logger.info("Initialing the app")

        self.config = {}
        self.config_last_save = time.time()
        self.config_path = config_path
        self.load_config()
        
        size = self.get_config_value("main", "window_dimensions", default=[900, 560])
        self.window = pygame.display.set_mode(size, pygame.RESIZABLE | pygame.SRCALPHA)
        self.timer = pygame.time.Clock()
        self.font_driver = FontDriver(FontType(self.get_config_value("main", "font_type", default=FontType.BITMAP.value)))
        self.running = True
        self.is_restarting = False
        self.caption = caption
        self.components = []
        self.key_down_timeout = 0
        self.key_down = [None, None, None]
        self.fps = 30

        self.status_bar = Statusbar(self)
        self.add_component(self.status_bar)

        self.command_executor = CommandExecutor(self)
        self.add_component(self.command_executor)

        self.buffers_stack = VStackComponent(self, (0, 0))
        self.add_component(self.buffers_stack)

        self.buffers_stack.add_child_component(EditorViewportComponent(self))

        # TODO: implement proper reload
        # self.hotreload = HotreloadWatchdog(main, component, editor_component, font, syntax_highlighter)

    def get_font_driver(self):
        return self.font_driver

    def get_focused_buffer_viewport(self):
        return self.buffers_stack.get_focused_component()

    def get_command_executor(self):
        return self.command_executor

    def get_text_scale(self) -> int:
        return self.get_config_value("main", "text_scale", default=1)

    def close(self):
        for i in self.components:
            i.cleanup()
        self.logger.info("Closing...")
        self.running = False
        self.save_config()

    def restart(self):
        for i in self.components:
            i.cleanup()
        self.logger.info("Restarting...")
        self.running = False
        self.is_restarting = True
        self.save_config()

    def reload(self):
        self.logger.info("Reloading in progress...")
        if self.hotreload.try_to_reload():
            for i in self.components:
                i.reload()
        self.logger.info("Successfully reloaded!")

    def save_config(self):
        with open(self.config_path, "w") as file:
            json.dump(self.config, file)

    def load_config(self):
        if os.path.isfile(self.config_path):
            with open(self.config_path, "r") as file:
                self.config = json.load(file)
            self.logger.info(f"Loaded {len(self.config)} entries from config")
    
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

    def update(self, dt):
        self.font_driver.change_font_type(FontType(self.get_config_value("main", "font_type", default=FontType.BITMAP.value)))

        self.buffers_stack.update_dimensions(
            (self.get_width(), self.get_height() - self.status_bar.get_height()),
            (0, 0)
        )

        self.key_down_timeout -= dt
        if self.key_down_timeout <= 0 and self.key_down[0]:
            self.key_down_timeout = 0.02
            for i in self.components:
                i.key_pressed_event(*self.key_down)

        for i in self.components:
            i.update(dt)

    def update_frame(self):
        font_size = self.get_font_driver().get_font_size()

        self.window.fill((0, 0, 0))
        for i in self.components:
            i.draw_frame(self.window)

        if self.get_config_value("main", "debug", default=False):
            text_scale = self.get_config_value("main", "text_scale", default=1)
            # debug_text = f"FPS: {round(self.timer.get_fps(), 1)}\n" + \
            #              f"W: {self.get_width()}; H: {self.get_height()}\n" + \
            #              "\n" + \
            #              f"Opened file: '{self.buffer_component.filename}'; Is Saved: {not self.buffer_component.is_unsaved}\n" + \
            #              f"Mode: {self.buffer_component.mode.value}"
            debug_text = f"FPS: {round(self.timer.get_fps(), 1)}\n" + \
                         f"W: {self.get_width()}; H: {self.get_height()}\n"
            # Draw debug text
            self.font_driver.draw_text(
                self.window,
                debug_text,
                (255, 255, 255),
                (120, 20, 20),
                40, 40,
                pixel_size=(text_scale, text_scale)
            )

            # Draw debug logs
            log_messages = self.logger_handler.get_log_history()
            logs_y_offset = self.get_height() - font_size[1] * text_scale * (4 + len(log_messages))
            self.font_driver.draw_text(
                self.window,
                "LOGS:",
                (255, 255, 255),
                (120, 20, 20),
                40, logs_y_offset,
                pixel_size=(text_scale, text_scale)
            )
            logs_y_offset += font_size[1] * text_scale
            self.font_driver.draw_text(
                self.window,
                '\n'.join(log_messages),
                (255, 255, 255),
                (120, 20, 20),
                40, logs_y_offset,
                pixel_size=(text_scale, text_scale)
            )

    def process_events(self):
        font_size = self.get_font_driver().get_font_size()
        mouse_position = pygame.mouse.get_pos()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            if event.type == pygame.VIDEORESIZE:
                text_scale = self.get_config_value("main", "text_scale", default=1)
                char_w = font_size[0] * text_scale
                char_h = font_size[1] * text_scale
                self.window = pygame.display.set_mode((event.w // char_w * char_w, event.h // char_h * char_h), pygame.RESIZABLE | pygame.SRCALPHA)

            for i in self.components:
                relative_mpos = [mouse_position[0] - i.position[0],
                                 mouse_position[1] - i.position[1]]
                print(i.__class__.__name__, relative_mpos)

                if event.type == pygame.KEYDOWN:
                    i.key_down_event(*self.key_down)
                    self.key_down_timeout = 0.2
                    self.key_down = [event.key, "    " if event.key == pygame.K_TAB else event.unicode, pygame.key.get_mods()]
                if event.type == pygame.KEYUP:
                    i.key_up_event(*self.key_down)
                    self.key_down_timeout = 0
                    self.key_down = [None, None, None]
                if event.type == pygame.MOUSEWHEEL:
                    i.mouse_wheel_event(event.x, event.y)
                else:
                    if event.type == pygame.MOUSEBUTTONDOWN and relative_mpos[0] >= 0 and relative_mpos[1] >= 0:
                        i.mouse_down_event(event.button, *relative_mpos)
                    if event.type == pygame.MOUSEBUTTONUP and relative_mpos[0] >= 0 and relative_mpos[1] >= 0:
                        i.mouse_up_event(event.button, *relative_mpos)
                    if event.type == pygame.MOUSEMOTION and relative_mpos[0] >= 0 and relative_mpos[1] >= 0:
                        i.mouse_motion_event(*relative_mpos)
                i.propagate_event(event)
    
    def run_loop(self):
        while self.running:
            self.process_events()
            self.update(1 / self.fps)
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
    # Call the method once, so the pyperclip module initializes
    pyperclip.paste()

    application = EditorApplication()
    application.run_loop()

    if application.is_restarting:
        os.execv(sys.executable, ['python'] + sys.argv)
    else:
        sys.exit(0)
