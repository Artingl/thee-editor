import pygame
import shlex
import os

from utils import *
from component import Component
from ..shell.editor_component import EditorViewportComponent
from ..shell.terminal_component import TerminalViewportComponent
from ..shell.buffer_mode import BufferMode


class Command:
    def __init__(self, executor):
        self.executor = executor
        self.application = executor.application
        self.status_bar = self.application.status_bar
        self.buffer_viewport = None
    
    def usage(self) -> str:
        return {"description": "No description", "usage": ["No usage info is defined"]}
    
    def execute(self, cmd, args): ...


class OpenCommand(Command):
    def usage(self):
        return {
            "description": "Opens file", 
            "usage": [
                'To open a file: open FILENAME',
                'To forcefully open a file (without saving current): open FILENAME !'
            ]
        }

    def execute(self, cmd, args):
        buffer_viewport = self.buffer_viewport
        if not isinstance(self.buffer_viewport, EditorViewportComponent):
            buffer_viewport = EditorViewportComponent(self.application)
            self.application.buffers_stack.add_child_component(buffer_viewport)
        if len(args) == 0:
            self.status_bar.display_text("Provide file name 'open FILENAME'", background=(255, 0, 0))
            return

        if not os.path.isfile(args[0]):
            self.status_bar.display_text(f"File '{args[0]}' doesn't exist", background=(255, 0, 0))
            return
        if buffer_viewport.is_unsaved and (len(args) == 1 or args[1] != "!"):
            self.status_bar.display_text(f"Current file is unsaved. Save it or type 'open FILENAME !'", background=(255, 0, 0))
            return

        buffer_viewport.open_file(args[0])


class SaveCommand(Command):
    def execute(self, cmd, args):
        if not isinstance(self.buffer_viewport, EditorViewportComponent):
            self.status_bar.display_text("Command must be called from with editor viewport being focused", background=(255, 0, 0))
            return
        if args:
            self.buffer_viewport.filename = args[0]
        self.buffer_viewport.save_file()
        self.status_bar.display_text(f"Saved file as '{self.buffer_viewport.filename}'")


class CloseRestartCommand(Command):
    def execute(self, cmd, args):
        if isinstance(self.buffer_viewport, EditorViewportComponent):
            if self.buffer_viewport.is_unsaved and (len(args) == 0 or args[0] != "!"):
                self.status_bar.display_text(f"Current file is unsaved. Save it or type '{cmd} !'", background=(255, 0, 0))
                return
        if cmd == 'quit':
            self.application.close()
        elif cmd == 'exit' or cmd == 'close':
            # Firstly try to close all buffer panes in vstack, and then exit
            if len(self.application.buffers_stack.children) > 1:
                self.application.buffers_stack.remove_focused()
            else:
                self.application.close()
        else:
            self.application.restart()


class NewCommand(Command):
    def execute(self, cmd, args):
        buffer_viewport = self.buffer_viewport
        if not isinstance(self.buffer_viewport, EditorViewportComponent):
            buffer_viewport = EditorViewportComponent(self.application)
            self.application.buffers_stack.add_child_component(buffer_viewport)
        filename = "unnamed.txt"
        if args:
            filename = args[0]
        buffer_viewport.open_file(filename)


class ShellCommand(Command):
    def execute(self, cmd, args):
        self.application.buffers_stack.add_child_component(TerminalViewportComponent(self.application, args))
        self.status_bar.display_text(f"Terminal spawned for command: {' '.join(args)}")


class ReloadCommand(Command):
    def execute(self, cmd, args):
        self.application.reload()
        self.status_bar.display_text("Successfully reloaded")


class EvalCommand(Command):
    def execute(self, cmd, args):
        if args:
            eval(' '.join(args))


class ConfigCommand(Command):
    DATA_TYPES = {
        'int': int,
        'bool': lambda x: x.lower() == 'true',
        'float': float,
        'str': str,
    }

    def execute(self, cmd, args):
        example = "config key.param = value type[int/bool/float/str]"
        if len(args) < 4 or args[3] not in ConfigCommand.DATA_TYPES or args[1] != '=':
            self.status_bar.display_text(f"Command accepts exactly 4 arguments: '{example}'", background=(255, 0, 0))
            return
        config_key_param = args[0].split(".")
        if len(config_key_param) != 2:
            self.status_bar.display_text(f"Key/param value must be separated with a dot: '{example}'", background=(255, 0, 0))
            return

        previous_value = self.application.get_config_value(config_key_param[0], config_key_param[1])
        new_value = ConfigCommand.DATA_TYPES[args[3]](args[2])

        self.application.store_config_value(config_key_param[0], config_key_param[1], new_value)
        self.status_bar.display_text(f"Updated value for {args[0]}; previous: '{previous_value}', new: '{new_value}'")


class SplitCommand(Command):
    def execute(self, cmd, args):
        from engine.shell import EditorViewportComponent
        self.application.buffers_stack.add_child_component(EditorViewportComponent(self.application))
       

class HelpCommand(Command):
    def usage(self):
        return {
            "description": "Prints this message",
            "usage": ["To display help message: help/info"]
        }

    def execute(self, cmd, args):
        commands_list = self.executor.commands
        info_string = ""
        for aliases, command in commands_list.items():
            usage = command.usage()
            info_string += "Usage of " + ', '.join(aliases) + "\n"
            info_string += f"  Description: {usage['description']}\n\n"
            info_string += "  " + "\n  ".join(usage["usage"]) + "\n"
        print(info_string)


class CommandExecutor(Component):
    def __init__(self, application):
        super().__init__(application, is_headless=True)
        self.application = application
        self.status_bar = self.application.status_bar
        self.last_successful_search_pattern = None

        self.mode = BufferMode.COMMAND
        self.command_insert_history = []
        self.command_insert_history_index = 0
        self.command_insert_value = ""
        self.command_insert_value_saved = ""

        self.commands = {
            ('open',): OpenCommand(self),
            ('save',): SaveCommand(self),
            ('exit', 'quit', 'restart', 'close'): CloseRestartCommand(self),
            ('reload',): ReloadCommand(self),
            ('new',): NewCommand(self),
            ('shell',): ShellCommand(self),
            ('config',): ConfigCommand(self),
            ('eval',): EvalCommand(self),
            ('split',): SplitCommand(self),
            ('help', 'info'): HelpCommand(self),
        }
    
    def repeat_last_search(self):
        if not self.last_successful_search_pattern:
            return
        buffer_viewport = self.application.get_focused_buffer_viewport()
        command = self.last_successful_search_pattern
        if not buffer_viewport.find_first_pattern(command):
            self.last_successful_search_pattern = None
            self.status_bar.display_text(f"Unable to find '{command}'", background=(255, 0, 0))
        else:
            self.last_successful_search_pattern = command

    def get_mode(self):
        return self.mode
    
    def set_mode(self, mode):
        self.mode = mode

    def key_down_event(self, key, unicode, modifier):
        self.key_pressed_event(key, unicode, modifier)

    def key_pressed_event(self, key, unicode, modifier):
        # Focus shortcuts
        if (key == pygame.K_n and self.get_mode() == BufferMode.COMMAND) or \
            (key == pygame.K_DOWN and (modifier & pygame.KMOD_CTRL or modifier & pygame.KMOD_LMETA)):
            self.application.buffers_stack.focus_next()
        if (key == pygame.K_p and self.get_mode() == BufferMode.COMMAND) or \
            (key == pygame.K_UP and (modifier & pygame.KMOD_CTRL or modifier & pygame.KMOD_LMETA)):
            self.application.buffers_stack.focus_previous()
        
        # Height change shortcuts
        # TODO: This is janky solution (the focus_extend, focus_shrink methods implementation as well).
        #       Remake it someday.
        if (key == pygame.K_UP and self.get_mode() == BufferMode.COMMAND and (modifier & pygame.KMOD_SHIFT)):
            self.application.buffers_stack.focus_extend()
        if (key == pygame.K_DOWN and self.get_mode() == BufferMode.COMMAND and (modifier & pygame.KMOD_SHIFT)):
            self.application.buffers_stack.focus_shrink()

        # Close shortcuts
        if (key == pygame.K_x and self.get_mode() == BufferMode.COMMAND):
            self.application.buffers_stack.remove_focused()

        if key == pygame.K_ESCAPE:
            self.mode = BufferMode.COMMAND
            self.command_insert_value = ""
            return
        # Change to the command insert mode if colon is pressed and in command mode
        elif self.mode == BufferMode.COMMAND and unicode == ':':
            self.mode = BufferMode.COMMAND_INSERT
            self.command_insert_history_index = 0
            self.command_insert_value_saved = ""
            self.command_insert_value = ""
            return
        # Execute command if in inset command mode and pressed return
        elif self.mode == BufferMode.COMMAND_INSERT and key == pygame.K_RETURN:
            self.mode = BufferMode.COMMAND
            self.execute(self.command_insert_value)
            self.command_insert_history.append(self.command_insert_value)
            self.command_insert_history_index = 0
            self.command_insert_value_saved = ""
            self.command_insert_value = ""
            return
        # Change to the insert mode if 'i' letter or 'insert' key is pressed and in command mode
        elif self.mode == BufferMode.COMMAND and (key == pygame.K_i or key == pygame.K_INSERT):
            self.mode = BufferMode.INSERT
            # Skip this key press, so we won't accidentally type it into the buffer
            return

        # If 'r' letter is pressed and in command mode, repeat the last successful text search in the buffer
        if key == pygame.K_r and self.get_mode() == BufferMode.COMMAND:
            self.repeat_last_search()

        # Remove the last character from the command insert value when backspace is pressed
        if key == pygame.K_BACKSPACE and self.get_mode() == BufferMode.COMMAND_INSERT:
            self.command_insert_value = self.command_insert_value[:-1]
        
        if unicode.isalpha() or is_allowed_nonalpha_chars(unicode) and len(unicode) >= 1:
            if self.get_mode() == BufferMode.COMMAND_INSERT:
                self.command_insert_value += unicode
        
        if self.get_mode() == BufferMode.COMMAND_INSERT:
            # Scroll through commands history using arrows for command_insert mode
            if key == pygame.K_UP and self.command_insert_history_index + 1 <= len(self.command_insert_history):
                if self.command_insert_history_index == 0:
                    self.command_insert_value_saved = self.command_insert_value
                self.command_insert_history_index += 1
                self.command_insert_value = self.command_insert_history[-self.command_insert_history_index]
            elif key == pygame.K_DOWN and self.command_insert_history_index - 1 >= 0:
                if self.command_insert_history_index - 1 == 0:
                    self.command_insert_value = self.command_insert_value_saved
                self.command_insert_history_index -= 1
                if self.command_insert_history_index > 0:
                    self.command_insert_value = self.command_insert_history[-self.command_insert_history_index]

    def execute(self, text):
        if not text:
            self.status_bar.display_text(f"Invalid command", background=(255, 0, 0))
            return
    
        buffer_viewport = self.application.get_focused_buffer_viewport()
        command, *args = shlex.split(text, posix=True)

        # If the command is just a number, go to that line number
        if command.isdigit():
            command = int(command)
            if command <= 0 or command > len(buffer_viewport.base_lines):
                self.status_bar.display_text(f"Invalid line! Available range: 1...{len(buffer_viewport.base_lines)}", background=(255, 0, 0))
            else:
                buffer_viewport.set_caret_line(command)
        else:
            for commands_list, instance in self.commands.items():
                if command in commands_list:
                    instance.buffer_viewport = buffer_viewport
                    instance.execute(command, args)
                    return
            # If unable to find the command with such name, try to use the command as a search pattern in the buffer text
            if not buffer_viewport.find_first_pattern(text):
                self.last_successful_search_pattern = None
                self.status_bar.display_text(f"Unable to find '{text}'", background=(255, 0, 0))
            else:
                self.last_successful_search_pattern = text
        
            # self.status_bar.display_text(f"Invalid command!", background=(255, 0, 0))

