import pygame
import os
import pyperclip

from engine.lang import BaseSyntaxHighlighter, get_syntax_highlighter_for_filename
from utils import FONT_SIZE

from .buffer_component import BufferViewportComponent
from .buffer_mode import BufferMode


class EditorViewportComponent(BufferViewportComponent):
    def __init__(self, app):
        super().__init__(app)
        self.filename = "unnamed.txt"
        self.file_type = "text file"
        self.is_unsaved = False
        self.cut_shortcut_count = 0
        self.syntax_highlighter = BaseSyntaxHighlighter()
        self.token_lines = self.syntax_highlighter.parse_code(self.base_lines)

        last_opened_file = app.get_config_value("editor", "last_opened_file")
        if last_opened_file and os.path.isfile(last_opened_file):
            self.open_file(last_opened_file)

    def generate_tokens(self):
        return self.syntax_highlighter.parse_code(self.base_lines)

    def propagate_event(self, event):
        if event.type == pygame.VIDEORESIZE:
            self.size = (self.application.get_width(), self.application.get_height() - FONT_SIZE[1] * self.text_scale)
        return super().propagate_event(event)
    
    def open_file(self, filename):
        self.buffer_id = f"editor_{filename}"
        self.caret_position = self.application.get_config_value("last_caret_position", self.buffer_id, default=[0, 0])
        self.current_y_line_offset, \
            self.previous_y_line_offset, \
            self.last_x_caret_position = self.application.get_config_value("last_scroll_offset", self.buffer_id, default=[0, 0, 0])
        self.syntax_highlighter, self.file_type = get_syntax_highlighter_for_filename(filename)
        self.filename = filename

        if not os.path.isfile(filename):
            # Open it as a new file
            self.base_lines = [""]
            self.token_lines = self.syntax_highlighter.parse_code(self.base_lines)
            self.application.remove_config_value("editor", "last_opened_file")
            return

        self.application.store_config_value("editor", "last_opened_file", self.filename)
        self.load_file()

    def load_file(self):
        with open(self.filename, "r") as file:
            self.base_lines = file.read().split("\n")
            self.token_lines = self.syntax_highlighter.parse_code(self.base_lines)

    def save_file(self):
        with open(self.filename, "w") as file:
            file.write('\n'.join(self.base_lines))
        self.is_unsaved = False

        # Re-open the file, because we might have saved a new file.
        # By doing do we'll get proper syntax highlighting and stuff
        self.open_file(self.filename)

    @classmethod
    def __get_whitespaces_count(self, line):
        whitespaces_count = 0
        for i in line:
            if i == ' ':
                whitespaces_count += 1
            else:
                break
        return whitespaces_count

    def handle_key_input(self, key, unicode, modifier):
        self.caret_position[1] = max(min(self.caret_position[1], len(self.base_lines) - 1), 0)
        self.caret_position[0] = max(min(self.caret_position[0], len(self.base_lines[self.caret_position[1]])), 0)
        is_text_updated = False
        skip_letter_insert = False
        self.caret_blink_animation = 0
        self.caret_blink_animation_flag = True
        
        # Save the file if the 's' letter is pressed and in command mode OR if a modifier is pressed
        if key == pygame.K_s:
            if self.get_mode() == BufferMode.COMMAND or (modifier & pygame.KMOD_CTRL or modifier & pygame.KMOD_LMETA):
                self.save_file()
                self.get_status_bar().display_text(f"Saved file as {self.filename}")
                skip_letter_insert = True
        # Paste from clipboard if the 'v' letter is pressed and a modifier is pressed
        # or if just 'p' is pressed in COMMAND mode
        if (key == pygame.K_v and (modifier & pygame.KMOD_CTRL or modifier & pygame.KMOD_LMETA)) or (key == pygame.K_p and self.get_mode() == BufferMode.COMMAND):
            is_text_updated = True
            skip_letter_insert = True
            text = pyperclip.paste()
            self.insert_at_current_caret(text)
            self.get_status_bar().display_text("Pasted text")
        
        # If 'o' letter is pressed and in command mode, insert new empty line below
        if key == pygame.K_o and self.get_mode() == BufferMode.COMMAND:
            # Add the same amount of whitespaces to the new line
            whitespaces = EditorViewportComponent.__get_whitespaces_count(self.base_lines[self.caret_position[1]])
            skip_letter_insert = True
            is_text_updated = True
            self.caret_position[1] += 1
            self.base_lines.insert(self.caret_position[1], "")
            self.base_lines[self.caret_position[1]] += " " * whitespaces
            self.caret_position[0] = len(self.base_lines[self.caret_position[1]])
            self.set_mode(BufferMode.INSERT)
        
        # If double 'd' letter is pressed and in command mode, cut current line and put it in clipboard.
        # Or if a combination ctrl + x is pressed
        if (key == pygame.K_d and self.get_mode() == BufferMode.COMMAND) or \
            (key == pygame.K_x and (modifier & pygame.KMOD_CTRL or modifier & pygame.KMOD_LMETA)):
            if key == pygame.K_x or self.cut_shortcut_count >= 1:
                skip_letter_insert = True
                is_text_updated = True
                cut_text = self.base_lines.pop(self.caret_position[1]) + "\n"
                self.get_status_bar().display_text(f"Cut line at {self.caret_position[1]}")
                pyperclip.copy(cut_text)
                self.caret_position[1] = min(self.caret_position[1], len(self.base_lines) - 1)
                self.caret_position[0] = 0
                self.cut_shortcut_count = 0
            else:
                self.cut_shortcut_count += 1
        
        if key == pygame.K_RETURN and self.get_mode() == BufferMode.INSERT:
            # Insert a new line below the caret if in insert mode
            is_text_updated = True

            # Add the same amount of whitespaces as on the previous line
            whitespaces = EditorViewportComponent.__get_whitespaces_count(self.base_lines[self.caret_position[1]])

            # Extract part of the line that we'd need to place on a new line.
            # Also remove it from the line we were on
            line_part = self.base_lines[self.caret_position[1]][self.caret_position[0]:]
            self.base_lines[self.caret_position[1]] = self.base_lines[self.caret_position[1]][:self.caret_position[0]]

            # Add a new line with the splitted part
            self.base_lines.insert(self.caret_position[1] + 1, whitespaces * " " + line_part)

            self.caret_position[0] = whitespaces
            self.caret_position[1] += 1

        return super().handle_key_input(key, unicode, modifier, skip_letter_insert, is_text_updated)
