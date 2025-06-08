import pygame
import string
import pyperclip
import shlex
import os

from enum import Enum
from component import *
from syntax_highlighter import *
from font import draw_text, FONT_SIZE

# Call the method once, so the module initializes
pyperclip.paste()


def is_allowed_nonalpha_chars(chars):
    allowed_chars = string.punctuation + string.digits + " "
    return all(i in allowed_chars for i in chars)


def is_allowed_alpha_chars(chars):
    allowed_chars = string.ascii_letters + string.digits + "_"
    return chars[0].isalpha() and all(i in allowed_chars for i in chars)


class EditorMode(Enum):
    INSERT: str = 'insert'
    COMMAND: str = 'command'
    COMMAND_INSERT: str = 'command_insert'


class EditorStatusbar(Component):
    MODE_SIGNS = {
        EditorMode.COMMAND: 'C',
        EditorMode.INSERT: 'I',
        EditorMode.COMMAND_INSERT: 'CI',
    }

    def __init__(self, app, editor):
        super().__init__(
            app,
            (app.get_width(), FONT_SIZE[1] * editor.text_size),
            0, app.get_height() - FONT_SIZE[1] * editor.text_size
        )

        self.editor = editor
        self.status_bar_text = ""
        self.status_bar_text_color = (255, 255, 255)
        self.status_bar_text_background = (0, 0, 0)
        self.status_bar_text_timeout = 0

    def propagate_event(self, event):
        if event.type == pygame.VIDEORESIZE:
            self.surface = pygame.Surface((self.application.get_width(), FONT_SIZE[1] * self.editor.text_size))
            self.y = self.application.get_height() - FONT_SIZE[1] * self.editor.text_size
    
    def display_text(self, text, color=(255, 255, 255), background=(0, 0, 0)):
        self.status_bar_text = text
        self.status_bar_text_timeout = 4
        self.status_bar_text_color = color
        self.status_bar_text_background = background

    def update(self, dt):
        self.status_bar_text_timeout -= dt
        if self.status_bar_text_timeout <= 0:
            self.status_bar_text_timeout = 0
            self.status_bar_text = ""
        
        return super().update(dt)
    
    def draw_frame(self):
        status_bar_background_color = (0, 0, 0)
        status_bar_color = (255, 255, 255)
        status_bar_text = f"{self.editor.filename} ({self.editor.file_type}); {self.editor.caret_position[1] + 1} line at {self.editor.caret_position[0]}"

        if self.editor.mode == EditorMode.COMMAND_INSERT:
            status_bar_text = f":{self.editor.command_insert_value}"
            self.status_bar_text_timeout = 0
        elif self.status_bar_text_timeout > 0:
            status_bar_text = self.status_bar_text
            status_bar_color = self.status_bar_text_color
            status_bar_background_color = self.status_bar_text_background

        if self.editor.mode == EditorMode.INSERT:
            status_bar_background_color = (100, 100, 190)

        # Draw current editor mode with a separator
        draw_text(
            self.surface,
            EditorStatusbar.MODE_SIGNS[self.editor.mode],
            (255, 255, 255),
            (0, 0, 0),
            0, 0,
            pixel_size=(self.editor.text_size, self.editor.text_size)
        )
        pygame.draw.rect(
            self.surface,
            (255, 255, 255),
            ((self.editor.lines_indicator_x_offset - 4) * self.editor.text_size, 0,
            int(1.5 * self.editor.text_size), FONT_SIZE[1] * self.editor.text_size)
        )
        # Draw status bar
        draw_text(
            self.surface,
            status_bar_text,
            status_bar_color,
            status_bar_background_color,
            self.editor.lines_indicator_x_offset, 0,
            (self.editor.text_size, self.editor.text_size)
        )
        
        pygame.draw.rect(
            self.surface,
            (170, 170, 170),
            (0, 0, self.get_width(), 1)
        )

        return super().draw_frame()


class Command:
    def __init__(self, executor):
        self.executor = executor
        self.application = executor.editor.application
        self.editor = executor.editor
        self.status_bar = executor.editor.status_bar
    
    def execute(self, cmd, args): ...


class OpenCommand(Command):
    def execute(self, cmd, args):
        if len(args) == 0:
            self.status_bar.display_text("Provide file name 'open FILENAME'", background=(255, 0, 0))
            return

        if not os.path.isfile(args[0]):
            self.status_bar.display_text(f"File '{args[0]}' doesn't exist", background=(255, 0, 0))
            return
        if self.editor.is_unsaved and (len(args) == 1 or args[1] != "!"):
            self.status_bar.display_text(f"Current file is unsaved. Save it or type 'open FILENAME !'", background=(255, 0, 0))
            return

        self.editor.open_file(args[0])


class SaveCommand(Command):
    def execute(self, cmd, args):
        if args:
            self.editor.filename = args[0]
        self.editor.save_file()
        self.status_bar.display_text(f"Saved file as '{self.editor.filename}'")


class ExitQuitRestartCommand(Command):
    def execute(self, cmd, args):
        if self.editor.is_unsaved and (len(args) == 0 or args[0] != "!"):
            self.status_bar.display_text(f"Current file is unsaved. Save it or type '{cmd} !'", background=(255, 0, 0))
            return
        if cmd == 'exit' or cmd == 'quit':
            self.application.close()
        else:
            self.application.restart()


class NewCommand(Command):
    def execute(self, cmd, args):
        filename = "unnamed.txt"
        if args:
            filename = args[0]
        self.editor.open_file(filename)


class ShellCommand(Command):
    def execute(self, cmd, args):
        # TODO: implement a better way to execute shell commands
        os.system(' '.join(args))


class ReloadCommand(Command):
    def execute(self, cmd, args):
        self.application.reload()
        self.status_bar.display_text("Successfully reloaded")


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


class CommandExecutor:
    def __init__(self, editor):
        self.editor = editor
        self.status_bar = self.editor.status_bar
        self.last_successful_search_pattern = None

        self.commands = {
            ('open'): OpenCommand(self),
            ('save'): SaveCommand(self),
            ('exit', 'quit', 'restart'): ExitQuitRestartCommand(self),
            ('reload'): ReloadCommand(self),
            ('new'): NewCommand(self),
            ('shell'): ShellCommand(self),
            ('config'): ConfigCommand(self),
        }
    
    def repeat_last_search(self):
        if not self.last_successful_search_pattern:
            return
        command = self.last_successful_search_pattern
        if not self.editor.find_first_pattern(command):
            self.last_successful_search_pattern = None
            self.status_bar.display_text(f"Unable to find '{command}'", background=(255, 0, 0))
        else:
            self.last_successful_search_pattern = command

    def execute(self, text):
        command, *args = shlex.split(text, posix=False)

        # If the command is just a number, go to that line number
        if command.isdigit():
            command = int(command)
            if command <= 0 or command > len(self.editor.base_lines_of_text):
                self.status_bar.display_text(f"Invalid line! Available range: 1...{len(self.editor.base_lines_of_text)}", background=(255, 0, 0))
            else:
                self.editor.set_caret_line(command)
        else:
            for commands_list, instance in self.commands.items():
                if command in commands_list:
                    instance.execute(command, args)
                    return
            # If unable to find the command with such name, try to use the command as a search pattern in the editor text
            if not self.editor.find_first_pattern(text):
                self.last_successful_search_pattern = None
                self.status_bar.display_text(f"Unable to find '{text}'", background=(255, 0, 0))
            else:
                self.last_successful_search_pattern = text
        
            # self.status_bar.display_text(f"Invalid command!", background=(255, 0, 0))


class Editor(Component):
    def __init__(self, app):
        super().__init__(app, (app.get_width(), app.get_height() - FONT_SIZE[1]))
        self.filename = "unnamed.txt"
        self.file_type = "text file"
        self.base_lines_of_text = [""]
        self.token_lines = []
        self.text_size = self.application.get_config_value("editor", "text_size", default=1)
        self.scroll_offset = 5
        self.caret_width = 2
        self.caret_height = FONT_SIZE[1]
        self.syntax_highlighter = BaseSyntaxHighlighter(self)

        self.previous_lines_to_draw = None
        self.cache_lines_surface = pygame.Surface((self.surface.get_width(), self.surface.get_height()))
        # Amount of frames that needs to be forcefully drawn by the editor without caching
        self.forcefully_update_editor = 4

        self.caret_position = [0, 0]
        self.caret_blink_animation = 0
        self.caret_animation_speed = 6
        self.is_unsaved = False
        self.caret_blink_animation_flag = False
        self.editor_update_delay = 0
        self.editor_current_pressed_key = [None, None, None]
        self.editor_previous_pressed_key = [None, None, None]
        self.lines_indicator_x_offset = 0
        self.current_y_line_offset = 0
        self.previous_y_line_offset = 0
        self.last_x_caret_position = 0

        self.mode = EditorMode.COMMAND

        self.status_bar = EditorStatusbar(app, self)
        self.command_executor = CommandExecutor(self)
        self.add_child_component(self.status_bar)

        self.command_insert_value = ""
        self.token_lines = self.syntax_highlighter.parse_code(self.base_lines_of_text)

        last_opened_file = app.get_config_value("editor", "last_opened_file")
        if last_opened_file:
            self.open_file(last_opened_file)

    @classmethod
    def __get_whitespaces(self, line):
        whitespaces_count = 0
        for i in line:
            if i == ' ':
                whitespaces_count += 1
            else:
                break
        return whitespaces_count

    def get_text_color(self, x, y):
        return self.syntax_highlighter.get_color(self.caret_position[0] + x, self.caret_position[1] + y)

    def update_syntax_highlighter(self, filename):
        filename = filename.lower()
        if filename.endswith(".py"):
            self.file_type = "Python file"
            self.syntax_highlighter = PySyntaxHighlighter(self)
        elif filename.endswith(".json"):
            self.file_type = "JSON file"
            self.syntax_highlighter = JsonSyntaxHighlighter(self)
        elif filename.endswith(".c") \
            or filename.endswith(".cc") \
            or filename.endswith(".cpp") \
            or filename.endswith(".h") \
            or filename.endswith(".hpp"):
            if filename.endswith(".h") or filename.endswith(".hpp"):
                self.file_type = "C/C++ Header file"
            else:
                self.file_type = "C/C++ file"
            self.syntax_highlighter = CSyntaxHighlighter(self)
        else:
            self.file_type = "text file"
            self.syntax_highlighter = BaseSyntaxHighlighter(self)

    def open_file(self, filename):
        self.caret_position = self.application.get_config_value("last_caret_position", filename, default=[0, 0])
        self.current_y_line_offset, \
            self.previous_y_line_offset, \
            self.last_x_caret_position = self.application.get_config_value("last_scroll_offset", filename, default=[0, 0, 0])
        self.filename = filename
        self.update_syntax_highlighter(filename)

        if not os.path.isfile(filename):
            # Open it as a new file
            self.base_lines_of_text = [""]
            self.token_lines = self.syntax_highlighter.parse_code(self.base_lines_of_text)
            self.application.remove_config_value("editor", "last_opened_file")
            return

        self.application.store_config_value("editor", "last_opened_file", self.filename)
        self.load_file()

    def load_file(self):
        with open(self.filename, "r") as file:
            self.base_lines_of_text = file.read().split("\n")
            self.token_lines = self.syntax_highlighter.parse_code(self.base_lines_of_text)

    def save_file(self):
        with open(self.filename, "w") as file:
            file.write('\n'.join(self.base_lines_of_text))
        self.is_unsaved = False

        # Re-open the file, because we might have saved a new file.
        # By doing do we'll get proper syntax highlighting and stuff
        self.open_file(self.filename)

    def reload(self):
        self.forcefully_update_editor = 4
        self.token_lines = self.syntax_highlighter.parse_code(self.base_lines_of_text)
        
        return super().reload()

    def update(self, dt):
        self.caret_blink_animation += dt * self.caret_animation_speed
        self.editor_update_delay -= dt
        if self.caret_blink_animation > 2:
            self.caret_blink_animation_flag = not self.caret_blink_animation_flag
            self.caret_blink_animation = 0
        
        if self.editor_update_delay <= 0:
            self.update_editor(*self.editor_current_pressed_key)
            self.editor_update_delay = 0.02

            # Save current text size
            self.application.store_config_value("editor", "text_size", self.text_size)

            # Save current caret position in config
            self.application.store_config_value("last_caret_position", self.filename, self.caret_position)

            # Also the scroll offset
            self.application.store_config_value(
                "last_scroll_offset", self.filename,
                [self.current_y_line_offset,
                self.previous_y_line_offset,
                self.last_x_caret_position]
            )
        
        return super().update(dt)

    def update_editor(self, key, unicode, key_modifier):
        if not key:
            return

        is_text_updated = False
        skip_letter_insert = False
        line_text = self.base_lines_of_text[self.caret_position[1]]
        self.caret_blink_animation = 0
        self.caret_blink_animation_flag = True

        if key == pygame.K_TAB:
            unicode = "    "
        
        # Return to the command mode if escape is pressed
        if key == pygame.K_ESCAPE:
            self.mode = EditorMode.COMMAND
            self.command_insert_value = ""
            return
        # Change to the command insert mode if colon is pressed and in command mode
        elif self.mode == EditorMode.COMMAND and unicode == ':':
            self.mode = EditorMode.COMMAND_INSERT
            self.command_insert_value = ""
            return
        # Execute command if in inset command mode and pressed return
        elif self.mode == EditorMode.COMMAND_INSERT and key == pygame.K_RETURN:
            self.mode = EditorMode.COMMAND
            self.command_executor.execute(self.command_insert_value)
            self.command_insert_value = ""
            return
        # Change to the insert mode if 'i' letter or 'insert' key is pressed and in command mode
        elif self.mode == EditorMode.COMMAND and (key == pygame.K_i or key == pygame.K_INSERT):
            self.mode = EditorMode.INSERT
            # Skip this key press, so we won't accidentally type it into the editor
            return

        if key == pygame.K_LEFT:
            self.caret_position[0] -= 1
            if self.caret_position[0] < 0:
                self.caret_position[1] = max(self.caret_position[1] - 1, 0)
                self.caret_position[0] = len(self.base_lines_of_text[self.caret_position[1]])
            self.last_x_caret_position = self.caret_position[0]
        elif key == pygame.K_RIGHT:
            self.caret_position[0] += 1
            if self.caret_position[0] > len(line_text):
                if self.caret_position[1] + 1 < len(self.base_lines_of_text):
                    self.caret_position[0] = 0
                    self.caret_position[1] += 1
                else:
                    self.caret_position[0] -= 1
            self.last_x_caret_position = self.caret_position[0]
        elif key == pygame.K_UP:
            self.caret_position[1] -= 1
            self.caret_position[1] = max(min(self.caret_position[1], len(self.base_lines_of_text) - 1), 0)
            self.caret_position[0] = min(self.last_x_caret_position, len(self.base_lines_of_text[self.caret_position[1]]))
        elif key == pygame.K_DOWN:
            self.caret_position[1] += 1
            self.caret_position[1] = max(min(self.caret_position[1], len(self.base_lines_of_text) - 1), 0)
            self.caret_position[0] = min(self.last_x_caret_position, len(self.base_lines_of_text[self.caret_position[1]]))
        
        # Check if a key combination was pressed
        if key == pygame.K_s:
            # Save the file if the 's' letter is pressed and in command mode OR if a modifier is pressed
            if self.mode == EditorMode.COMMAND or (key_modifier & pygame.KMOD_CTRL or key_modifier & pygame.KMOD_LMETA):
                self.save_file()
                self.status_bar.display_text(f"Saved file as {self.filename}")
                skip_letter_insert = True
        # Paste from clipboard if the 'v' letter is pressed and a modifier is pressed
        # or if just 'p' is pressed in COMMAND mode
        if (key == pygame.K_v and (key_modifier & pygame.KMOD_CTRL or key_modifier & pygame.KMOD_LMETA)) or (key == pygame.K_p and self.mode == EditorMode.COMMAND):
            is_text_updated = True
            skip_letter_insert = True
            text = pyperclip.paste()
            self.insert_at_current_caret(text)
            self.status_bar.display_text("Pasted text")
            
        # If 'r' letter is pressed and in command mode, repeat the last successful text search in the editor
        if key == pygame.K_r and self.mode == EditorMode.COMMAND:
            self.command_executor.repeat_last_search()
        # If 'o' letter is pressed and in command mode, insert new empty line below
        elif key == pygame.K_o and self.mode == EditorMode.COMMAND:
            skip_letter_insert = True
            is_text_updated = True
            self.caret_position[0] = 0
            self.caret_position[1] += 1
            self.base_lines_of_text.insert(self.caret_position[1], '')
            self.mode = EditorMode.INSERT
        # If double 'd' letter is pressed and in command mode, cut current line and put it in clipboard.
        # Or if a combination ctrl + x is pressed
        elif (key == pygame.K_d and self.editor_previous_pressed_key[0] == pygame.K_d and self.mode == EditorMode.COMMAND) or \
            (key == pygame.K_x and (key_modifier & pygame.KMOD_CTRL or key_modifier & pygame.KMOD_LMETA)):
            skip_letter_insert = True
            is_text_updated = True
            cut_text = "\n" + self.base_lines_of_text.pop(self.caret_position[1])
            self.status_bar.display_text("Cut text")
            pyperclip.copy(cut_text)
            self.caret_position[1] = max(self.caret_position[1] - 1, 0)
            self.caret_position[0] = len(self.base_lines_of_text[self.caret_position[1]])
        
        # Key combinations for increasing/decreasing scale of the text
        if key == pygame.K_EQUALS and (key_modifier & pygame.KMOD_CTRL or key_modifier & pygame.KMOD_LMETA):
            if FONT_SIZE[1] * (self.text_size + 3) < self.surface.get_height() * 0.2:
                self.text_size += 1
            return
        elif key == pygame.K_MINUS and (key_modifier & pygame.KMOD_CTRL or key_modifier & pygame.KMOD_LMETA):
            self.text_size -= 1
            self.text_size = max(self.text_size, 1)
            return
        
        if key == pygame.K_RETURN:
            if self.mode == EditorMode.INSERT:
                # Insert a new line below the caret if in insert mode
                is_text_updated = True

                # Add the same amount of whitespaces as on the previous line
                whitespaces = Editor.__get_whitespaces(self.base_lines_of_text[self.caret_position[1]])

                # Extract part of the line that we'd need to place on a new line.
                # Also remove it from the line we were on
                line_part = self.base_lines_of_text[self.caret_position[1]][self.caret_position[0]:]
                self.base_lines_of_text[self.caret_position[1]] = self.base_lines_of_text[self.caret_position[1]][:self.caret_position[0]]

                # Add a new line with the splitted part
                self.base_lines_of_text.insert(self.caret_position[1] + 1, whitespaces * " " + line_part)

                self.caret_position[0] = whitespaces
                self.caret_position[1] += 1
            else:
                # Just step further to the next line if in command mode (the same as pressing down arrow)
                self.caret_position[1] += 1
                self.caret_position[1] = max(min(self.caret_position[1], len(self.base_lines_of_text) - 1), 0)
                self.caret_position[0] = min(self.last_x_caret_position, len(self.base_lines_of_text[self.caret_position[1]]))
        elif key == pygame.K_DELETE:
            if self.mode == EditorMode.INSERT:
                # Remove the character after the caret if in insert mode
                is_text_updated = True

                # If the caret is in the end of the line and we have a line below, connect it with the previous one
                if self.caret_position[0] == len(line_text) and self.caret_position[1] < len(self.base_lines_of_text) - 1:
                    self.base_lines_of_text[self.caret_position[1]] += self.base_lines_of_text.pop(self.caret_position[1] + 1)
                # If the caret is not in the end of the line, just remove a letter
                else:
                    self.base_lines_of_text[self.caret_position[1]] = line_text[:self.caret_position[0]] + line_text[self.caret_position[0] + 1:]
            elif self.mode == EditorMode.COMMAND:
                # Just step further in the line if in command mode (the same as pressing right arrow)
                self.caret_position[0] += 1
                self.caret_position[0] = max(min(self.caret_position[0], len(self.base_lines_of_text[self.caret_position[1]])), 0)
                self.last_x_caret_position = self.caret_position[0]
        elif key == pygame.K_BACKSPACE:
            if self.mode == EditorMode.INSERT:
                # Remove the character before the caret if in insert mode
                is_text_updated = True
                
                # If the caret is not in the beginning of the line, just remove a letter
                if self.caret_position[0] > 0:
                    self.caret_position[0] -= 1
                    self.base_lines_of_text[self.caret_position[1]] = line_text[:self.caret_position[0]] + line_text[self.caret_position[0] + 1:]
                # Connect two lines otherwise
                elif self.caret_position[1] > 0:
                    self.caret_position[0] = len(self.base_lines_of_text[self.caret_position[1] - 1])
                    self.base_lines_of_text[self.caret_position[1] - 1] += self.base_lines_of_text[self.caret_position[1]]
                    self.base_lines_of_text.pop(self.caret_position[1])
                    self.caret_position[1] -= 1
            elif self.mode == EditorMode.COMMAND_INSERT:
                # Remove the last character from the command insert value
                self.command_insert_value = self.command_insert_value[:-1]
            elif self.mode == EditorMode.COMMAND:
                # Just step further in the line if in command mode (the same as pressing left arrow)
                self.caret_position[0] -= 1
                self.caret_position[0] = max(min(self.caret_position[0], len(self.base_lines_of_text[self.caret_position[1]])), 0)
                self.last_x_caret_position = self.caret_position[0]
        elif unicode.isalpha() or is_allowed_nonalpha_chars(unicode) and len(unicode) >= 1:
            if not skip_letter_insert:
                if self.mode == EditorMode.INSERT:
                    is_text_updated = True
                    line_text = self.insert_at_current_caret(unicode)
                elif self.mode == EditorMode.COMMAND_INSERT:
                    self.command_insert_value += unicode
        
        # If text was updated, parse it again
        if is_text_updated:
            self.is_unsaved = True
            self.token_lines = self.syntax_highlighter.parse_code(self.base_lines_of_text)
    
    def find_first_pattern(self, pattern):
        """Searches for first appearance in the code after current caret position"""
        for idx, line in enumerate(self.base_lines_of_text[self.caret_position[1]:]):
            if (position := line.find(pattern)) != -1 and [position, idx + self.caret_position[1]] != self.caret_position:
                self.caret_position[0] = position
                self.caret_position[1] += idx
                self.center_caret_on_screen()
                return True

        # If couldn't find after caret, try to find from the beginning of the text
        for idx, line in enumerate(self.base_lines_of_text):
            if (position := line.find(pattern)) != -1 and [position, idx] != self.caret_position:
                self.caret_position[0] = position
                self.caret_position[1] = idx
                self.center_caret_on_screen()
                return True

        return False

    def insert_at_current_caret(self, text):
        line_text = self.base_lines_of_text[self.caret_position[1]]
        for char in text:
            if char == "\n":
                self.caret_position[0] = 0
                self.caret_position[1] += 1
                self.base_lines_of_text.append("")
                continue

            # Type the text into the editor lines
            self.base_lines_of_text[self.caret_position[1]] = line_text = line_text[:self.caret_position[0]] + char + line_text[self.caret_position[0]:]
            self.caret_position[0] += 1
        return line_text
    
    def set_caret_line(self, line):
        line -= 1
        if 0 <= line < len(self.base_lines_of_text):
            self.caret_position[1] = line
            self.caret_position[0] = len(self.base_lines_of_text[self.caret_position[1]])
            self.center_caret_on_screen()
    
    def center_caret_on_screen(self):
        self.current_y_line_offset = max(self.caret_position[1] - self.get_amount_of_lines_surf_height() // 2, 0)

    def propagate_event(self, event):
        if event.type == pygame.KEYDOWN:
            if self.editor_current_pressed_key[0] is not None:
                self.editor_previous_pressed_key = self.editor_current_pressed_key
            self.editor_current_pressed_key = [event.key, event.unicode, event.mod]
            self.update_editor(*self.editor_current_pressed_key)
            self.editor_update_delay = 0.3
        if event.type == pygame.KEYUP:
            self.editor_previous_pressed_key = self.editor_current_pressed_key
            self.editor_current_pressed_key = [None, None, None]
        if event.type == pygame.VIDEORESIZE:
            self.surface = pygame.Surface((event.w, event.h - FONT_SIZE[1] * self.text_size))
            self.cache_lines_surface = pygame.Surface((event.w, event.h - FONT_SIZE[1] * self.text_size))
            self.forcefully_update_editor = 4

        return super().propagate_event(event)

    def get_amount_of_lines_surf_height(self):
        return round(self.surface.get_height() / (FONT_SIZE[1] * self.text_size))

    def draw_frame(self):
        # Calculate amount of lines that can fit the height of the editor surface
        amount_of_lines_surf_height = self.get_amount_of_lines_surf_height() - 1

        # Calculate the offset of lines that should be displayed on the screen based on current caret Y
        y_line_offset = self.caret_position[1] - amount_of_lines_surf_height

        # Scroll upwards if self.scroll_offset amount of lines is left before we reach the top of the screen
        if self.current_y_line_offset > 0 \
                and y_line_offset < self.current_y_line_offset - (amount_of_lines_surf_height - self.scroll_offset):
            self.current_y_line_offset -= 1
        # Scroll upwards if self.scroll_offset amount of lines is left before we reach the bottom of the screen
        # And if we'd not go over the total amount of lines
        elif y_line_offset + self.scroll_offset > self.current_y_line_offset \
                and y_line_offset > self.previous_y_line_offset \
                and self.current_y_line_offset + amount_of_lines_surf_height + 1 < len(self.base_lines_of_text):
            self.current_y_line_offset += 1
        elif y_line_offset > self.current_y_line_offset:
            self.current_y_line_offset = max(y_line_offset, 0)
        self.previous_y_line_offset = y_line_offset

        # Get list of lines of texts relative to current caret position
        lines_to_draw = self.token_lines[self.current_y_line_offset:self.current_y_line_offset + amount_of_lines_surf_height + 1]

        # Draw the lines of text
        new_lines_indicator_width = 1

        # Draw line numbers indicator on the left
        for line_number, tokens in enumerate(lines_to_draw):
            y_offset = line_number * FONT_SIZE[1] * self.text_size
            line_number += self.current_y_line_offset
            line_indicator_color = (170, 170, 170)

            if line_number == self.caret_position[1]:
                line_indicator_color = (255, 255, 255)

            # Draw the line indicator
            line_indicator_len = ((self.lines_indicator_x_offset - 4) * self.text_size) // FONT_SIZE[0] * self.text_size
            line_indicator_text = str(line_number + 1)
            line_indicator_text = " " * (line_indicator_len - len(line_indicator_text)) + line_indicator_text
            line_indicator_width, _ = draw_text(
                self.surface,
                line_indicator_text,
                line_indicator_color,
                (0, 0, 0),
                0, y_offset,
                pixel_size=(self.text_size, self.text_size)
            )
            pygame.draw.rect(
                self.surface,
                line_indicator_color,
                ((self.lines_indicator_x_offset - 4) * self.text_size, y_offset,
                int(1.5 * self.text_size), FONT_SIZE[1] * self.text_size)
            )

            # Dynamically update the lines indicator offset based on the width of the line number string
            line_indicator_width += 5
            if line_indicator_width > new_lines_indicator_width:
                new_lines_indicator_width = line_indicator_width
                if self.lines_indicator_x_offset == 0:
                    self.lines_indicator_x_offset = new_lines_indicator_width

        # Only redraw the lines if they has updated
        if self.previous_lines_to_draw != lines_to_draw or self.forcefully_update_editor > 0:
            self.forcefully_update_editor -= 1
            self.forcefully_update_editor = max(self.forcefully_update_editor, 0)
            self.cache_lines_surface.fill((0, 0, 0))
            self.previous_lines_to_draw = lines_to_draw
            for line_number, tokens in enumerate(lines_to_draw):
                x_offset = 0
                y_offset = line_number * FONT_SIZE[1] * self.text_size

                for token in tokens:
                    line = token
                    color = (255, 255, 255)
                    background = (0, 0, 0)
                    if token.__class__ != str:
                        line = token.value
                        color = token.color
                        background = token.background
                    # Draw the line
                    offset, _ = draw_text(
                        self.cache_lines_surface,
                        line,
                        color, background,
                        x_offset, y_offset,
                        pixel_size=(self.text_size, self.text_size),
                    )
                    x_offset += offset * self.text_size
            
            self.lines_indicator_x_offset = new_lines_indicator_width

        # Draw the lines
        self.surface.blit(self.cache_lines_surface, (self.lines_indicator_x_offset * self.text_size, 0))

        # Draw the caret at its current position
        if self.caret_blink_animation_flag:
            pygame.draw.rect(
                self.surface,
                (255, 255, 255),
                (self.caret_position[0] * FONT_SIZE[0] * self.text_size + self.lines_indicator_x_offset * self.text_size,
                 self.caret_position[1] * FONT_SIZE[1] * self.text_size + FONT_SIZE[1] * self.text_size - self.caret_height * self.text_size - self.current_y_line_offset * FONT_SIZE[1] * self.text_size,
                self.caret_width * self.text_size, self.caret_height * self.text_size)
            )

        return super().draw_frame()

