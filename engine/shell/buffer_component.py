import pygame
import string
import pyperclip
import os

from engine.lang import BaseSyntaxHighlighter, get_syntax_highlighter_for_filename
from utils.font_renderer import draw_text
from utils.font import FONT_SIZE
from component import Component
from engine.command import CommandExecutor

from .status_bar import Statusbar
from .buffer_mode import BufferMode

def is_allowed_nonalpha_chars(chars):
    allowed_chars = string.punctuation + string.digits + " "
    return all(i in allowed_chars for i in chars)


def is_allowed_alpha_chars(chars):
    allowed_chars = string.ascii_letters + string.digits + "_"
    return chars[0].isalpha() and all(i in allowed_chars for i in chars)



class BufferViewportComponent(Component):
    def __init__(self, app, size):
        super().__init__(app, size)
        self.filename = "unnamed.txt"
        self.file_type = "text file"
        self.base_lines = [""]
        self.token_lines = []
        self.text_size = self.application.get_config_value("editor", "text_size", default=1)
        self.scroll_offset = 5
        self.caret_width = 2
        self.caret_height = FONT_SIZE[1]
        self.syntax_highlighter = BaseSyntaxHighlighter()

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
        self.lines_indicator_x_offset = 0
        self.current_y_line_offset = 0
        self.previous_y_line_offset = 0
        self.last_x_caret_position = 0
        self.cut_shortcut_count = 0
        
        self.mode = BufferMode.COMMAND
        self.command_insert_history = []
        self.command_insert_history_index = 0
        self.command_insert_value = ""
        self.command_insert_value_saved = ""

        self.status_bar = Statusbar(app, self)
        self.command_executor = CommandExecutor(self)
        self.add_child_component(self.status_bar)

        self.token_lines = self.syntax_highlighter.parse_code(self.base_lines)

        last_opened_file = app.get_config_value("editor", "last_opened_file")
        if last_opened_file and os.path.isfile(last_opened_file):
            self.open_file(last_opened_file)

    @classmethod
    def __get_whitespaces_count(self, line):
        whitespaces_count = 0
        for i in line:
            if i == ' ':
                whitespaces_count += 1
            else:
                break
        return whitespaces_count

    def get_text_color(self, x, y):
        return self.syntax_highlighter.get_color(self.caret_position[0] + x, self.caret_position[1] + y)

    def open_file(self, filename):
        self.caret_position = self.application.get_config_value("last_caret_position", filename, default=[0, 0])
        self.current_y_line_offset, \
            self.previous_y_line_offset, \
            self.last_x_caret_position = self.application.get_config_value("last_scroll_offset", filename, default=[0, 0, 0])
        self.filename = filename
        self.syntax_highlighter, self.file_type = get_syntax_highlighter_for_filename(filename)

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

    def reload(self):
        self.forcefully_update_editor = 4
        self.token_lines = self.syntax_highlighter.parse_code(self.base_lines)
        
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
        line_text = self.base_lines[self.caret_position[1]]
        self.caret_blink_animation = 0
        self.caret_blink_animation_flag = True

        if key == pygame.K_TAB:
            unicode = "    "
        
        # Return to the command mode if escape is pressed
        if key == pygame.K_ESCAPE:
            self.mode = BufferMode.COMMAND
            self.command_insert_value = ""
            return
        # Change to the command insert mode if colon is pressed and in command mode
        elif self.mode == BufferMode.COMMAND and unicode == ':':
            self.mode = BufferMode.COMMAND_INSERT
            self.command_insert_value = ""
            self.command_insert_history_index = 0
            return
        # Execute command if in inset command mode and pressed return
        elif self.mode == BufferMode.COMMAND_INSERT and key == pygame.K_RETURN:
            self.mode = BufferMode.COMMAND
            self.command_executor.execute(self.command_insert_value)
            self.command_insert_history.append(self.command_insert_value)
            self.command_insert_value = ""
            return
        # Change to the insert mode if 'i' letter or 'insert' key is pressed and in command mode
        elif self.mode == BufferMode.COMMAND and (key == pygame.K_i or key == pygame.K_INSERT):
            self.mode = BufferMode.INSERT
            # Skip this key press, so we won't accidentally type it into the editor
            return
        
        if self.mode != BufferMode.COMMAND_INSERT:
            # Move caret using arrows
            if key == pygame.K_LEFT:
                self.caret_position[0] -= 1
                if self.caret_position[0] < 0:
                    self.caret_position[1] = max(self.caret_position[1] - 1, 0)
                    self.caret_position[0] = len(self.base_lines[self.caret_position[1]])
                self.last_x_caret_position = self.caret_position[0]
            elif key == pygame.K_RIGHT:
                self.caret_position[0] += 1
                if self.caret_position[0] > len(line_text):
                    if self.caret_position[1] + 1 < len(self.base_lines):
                        self.caret_position[0] = 0
                        self.caret_position[1] += 1
                    else:
                        self.caret_position[0] -= 1
                self.last_x_caret_position = self.caret_position[0]
            elif key == pygame.K_UP:
                self.caret_position[1] -= 1
                self.caret_position[1] = max(min(self.caret_position[1], len(self.base_lines) - 1), 0)
                self.caret_position[0] = min(self.last_x_caret_position, len(self.base_lines[self.caret_position[1]]))
            elif key == pygame.K_DOWN:
                self.caret_position[1] += 1
                self.caret_position[1] = max(min(self.caret_position[1], len(self.base_lines) - 1), 0)
                self.caret_position[0] = min(self.last_x_caret_position, len(self.base_lines[self.caret_position[1]]))
        else:
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

        # Check if a key combination was pressed
        if key == pygame.K_s:
            # Save the file if the 's' letter is pressed and in command mode OR if a modifier is pressed
            if self.mode == BufferMode.COMMAND or (key_modifier & pygame.KMOD_CTRL or key_modifier & pygame.KMOD_LMETA):
                self.save_file()
                self.status_bar.display_text(f"Saved file as {self.filename}")
                skip_letter_insert = True
        # Paste from clipboard if the 'v' letter is pressed and a modifier is pressed
        # or if just 'p' is pressed in COMMAND mode
        if (key == pygame.K_v and (key_modifier & pygame.KMOD_CTRL or key_modifier & pygame.KMOD_LMETA)) or (key == pygame.K_p and self.mode == BufferMode.COMMAND):
            is_text_updated = True
            skip_letter_insert = True
            text = pyperclip.paste()
            self.insert_at_current_caret(text)
            self.status_bar.display_text("Pasted text")
            
        # If 'r' letter is pressed and in command mode, repeat the last successful text search in the editor
        if key == pygame.K_r and self.mode == BufferMode.COMMAND:
            self.command_executor.repeat_last_search()
        # If 'o' letter is pressed and in command mode, insert new empty line below
        if key == pygame.K_o and self.mode == BufferMode.COMMAND:
            # Add the same amount of whitespaces to the new line
            whitespaces = BufferViewportComponent.__get_whitespaces_count(self.base_lines[self.caret_position[1]])
            skip_letter_insert = True
            is_text_updated = True
            self.caret_position[1] += 1
            self.base_lines.insert(self.caret_position[1], "")
            self.base_lines[self.caret_position[1]] += " " * whitespaces
            self.caret_position[0] = len(self.base_lines[self.caret_position[1]])
            self.mode = BufferMode.INSERT
        # If double 'd' letter is pressed and in command mode, cut current line and put it in clipboard.
        # Or if a combination ctrl + x is pressed
        if (key == pygame.K_d and self.mode == BufferMode.COMMAND) or \
            (key == pygame.K_x and (key_modifier & pygame.KMOD_CTRL or key_modifier & pygame.KMOD_LMETA)):
            if key == pygame.K_x or self.cut_shortcut_count >= 1:
                skip_letter_insert = True
                is_text_updated = True
                cut_text = self.base_lines.pop(self.caret_position[1]) + "\n"
                self.status_bar.display_text(f"Cut line at {self.caret_position[1]}")
                pyperclip.copy(cut_text)
                self.caret_position[1] = min(self.caret_position[1], len(self.base_lines) - 1)
                self.caret_position[0] = 0
                self.cut_shortcut_count = 0
            else:
                self.cut_shortcut_count += 1
         
        # TODO: fix modifier keys, they are not reported correctly when arrow key is pressed
        # If 'w' letter is pressed and in command mode, skip to next literal.
        # Or if a combination ctrl + right_arrow is pressed
        if (key == pygame.K_w and self.mode == BufferMode.COMMAND) or \
            (key == pygame.K_RIGHT and (key_modifier & pygame.KMOD_CTRL or key_modifier & pygame.KMOD_LMETA)):
            self.step_next_literal()
        # If 'b' letter is pressed and in command mode, skip to previous literal.
        # Or if a combination ctrl + left_arrow is pressed
        if (key == pygame.K_b and self.mode == BufferMode.COMMAND) or \
            (key == pygame.K_LEFT and (key_modifier & pygame.KMOD_CTRL or key_modifier & pygame.KMOD_LMETA)):
            self.step_previous_literal()

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
            if self.mode == BufferMode.INSERT:
                # Insert a new line below the caret if in insert mode
                is_text_updated = True

                # Add the same amount of whitespaces as on the previous line
                whitespaces = BufferViewportComponent.__get_whitespaces_count(self.base_lines[self.caret_position[1]])

                # Extract part of the line that we'd need to place on a new line.
                # Also remove it from the line we were on
                line_part = self.base_lines[self.caret_position[1]][self.caret_position[0]:]
                self.base_lines[self.caret_position[1]] = self.base_lines[self.caret_position[1]][:self.caret_position[0]]

                # Add a new line with the splitted part
                self.base_lines.insert(self.caret_position[1] + 1, whitespaces * " " + line_part)

                self.caret_position[0] = whitespaces
                self.caret_position[1] += 1
            else:
                # Just step further to the next line if in command mode (the same as pressing down arrow)
                self.caret_position[1] += 1
                self.caret_position[1] = max(min(self.caret_position[1], len(self.base_lines) - 1), 0)
                self.caret_position[0] = min(self.last_x_caret_position, len(self.base_lines[self.caret_position[1]]))
        elif key == pygame.K_DELETE:
            if self.mode == BufferMode.INSERT:
                # Remove the character after the caret if in insert mode
                is_text_updated = True

                # If the caret is in the end of the line and we have a line below, connect it with the previous one
                if self.caret_position[0] == len(line_text) and self.caret_position[1] < len(self.base_lines) - 1:
                    self.base_lines[self.caret_position[1]] += self.base_lines.pop(self.caret_position[1] + 1)
                # If the caret is not in the end of the line, just remove a letter
                else:
                    self.base_lines[self.caret_position[1]] = line_text[:self.caret_position[0]] + line_text[self.caret_position[0] + 1:]
            elif self.mode == BufferMode.COMMAND:
                # Just step further in the line if in command mode (the same as pressing right arrow)
                self.caret_position[0] += 1
                self.caret_position[0] = max(min(self.caret_position[0], len(self.base_lines[self.caret_position[1]])), 0)
                self.last_x_caret_position = self.caret_position[0]
        elif key == pygame.K_BACKSPACE:
            if self.mode == BufferMode.INSERT:
                # Remove the character before the caret if in insert mode
                is_text_updated = True
                
                # If the caret is not in the beginning of the line, just remove a letter
                if self.caret_position[0] > 0:
                    self.caret_position[0] -= 1
                    self.base_lines[self.caret_position[1]] = line_text[:self.caret_position[0]] + line_text[self.caret_position[0] + 1:]
                # Connect two lines otherwise
                elif self.caret_position[1] > 0:
                    self.caret_position[0] = len(self.base_lines[self.caret_position[1] - 1])
                    self.base_lines[self.caret_position[1] - 1] += self.base_lines[self.caret_position[1]]
                    self.base_lines.pop(self.caret_position[1])
                    self.caret_position[1] -= 1
            elif self.mode == BufferMode.COMMAND_INSERT:
                # Remove the last character from the command insert value
                self.command_insert_value = self.command_insert_value[:-1]
            elif self.mode == BufferMode.COMMAND:
                # Just step further in the line if in command mode (the same as pressing left arrow)
                self.caret_position[0] -= 1
                self.caret_position[0] = max(min(self.caret_position[0], len(self.base_lines[self.caret_position[1]])), 0)
                self.last_x_caret_position = self.caret_position[0]
        elif unicode.isalpha() or is_allowed_nonalpha_chars(unicode) and len(unicode) >= 1:
            if not skip_letter_insert:
                if self.mode == BufferMode.INSERT:
                    is_text_updated = True
                    line_text = self.insert_at_current_caret(unicode)
                elif self.mode == BufferMode.COMMAND_INSERT:
                    self.command_insert_value += unicode
        
        # If text was updated, parse it again
        if is_text_updated:
            self.is_unsaved = True
            self.token_lines = self.syntax_highlighter.parse_code(self.base_lines)
    
    def parse_token(self, token, color=(255, 255, 255), background=(0, 0, 0)):
        result = token
        if result.__class__ != str:
            result = token.value
            color = token.color
            background = token.background
        return result, color, background

    def step_next_literal(self):
        line_x_offset = 0
        for token in self.token_lines[self.caret_position[1]]:
            token, _, _ = self.parse_token(token)
            line_x_offset += len(token)
            if line_x_offset > self.caret_position[0] and token != " ":
                self.caret_position[0] = line_x_offset
                return
        
        if self.caret_position[0] < line_x_offset:
            self.caret_position[0] = line_x_offset
        else:
            self.caret_position[0] = 0
            self.caret_position[1] = min(self.caret_position[1] + 1, len(self.base_lines) - 1)

    def step_previous_literal(self):
        line_x_offset = len(self.base_lines[self.caret_position[1]])
        for token in self.token_lines[self.caret_position[1]][::-1]:
            token, _, _ = self.parse_token(token)
            line_x_offset -= len(token)
            if line_x_offset < self.caret_position[0] and token != " ":
                self.caret_position[0] = line_x_offset
                return

        if self.caret_position[0] > 0:
            self.caret_position[0] = 0
        else:
            self.caret_position[1] = max(self.caret_position[1] - 1, 0)
            self.caret_position[0] = len(self.base_lines[self.caret_position[1]])

    def find_first_pattern(self, pattern):
        """Searches for first appearance in the code after current caret position"""
        for idx, line in enumerate(self.base_lines[self.caret_position[1]:]):
            if (position := line.find(pattern)) != -1 and [position, idx + self.caret_position[1]] != self.caret_position:
                self.caret_position[0] = position
                self.caret_position[1] += idx
                self.center_caret_on_screen()
                return True

        # If couldn't find after caret, try to find from the beginning of the text
        for idx, line in enumerate(self.base_lines):
            if (position := line.find(pattern)) != -1 and [position, idx] != self.caret_position:
                self.caret_position[0] = position
                self.caret_position[1] = idx
                self.center_caret_on_screen()
                return True

        return False

    def insert_at_current_caret(self, text):
        line_text = self.base_lines[self.caret_position[1]]
        for char in text:
            if char == "\n":
                line_after_caret = self.base_lines[self.caret_position[1]][self.caret_position[0]:]
                self.base_lines[self.caret_position[1]] = line_text = line_text[:self.caret_position[0]]
                self.caret_position[0] = 0
                self.caret_position[1] += 1
                self.base_lines.insert(self.caret_position[1], line_after_caret)
                continue

            # Type the text into the editor lines
            self.base_lines[self.caret_position[1]] = line_text = line_text[:self.caret_position[0]] + char + line_text[self.caret_position[0]:]
            self.caret_position[0] += 1
        return line_text
    
    def set_caret_line(self, line):
        line -= 1
        if 0 <= line < len(self.base_lines):
            self.caret_position[1] = line
            self.caret_position[0] = len(self.base_lines[self.caret_position[1]])
            self.center_caret_on_screen()
    
    def center_caret_on_screen(self):
        self.current_y_line_offset = max(self.caret_position[1] - self.get_amount_of_lines_surf_height() // 2, 0)

    def propagate_event(self, event):
        if event.type == pygame.KEYDOWN:
            self.editor_current_pressed_key = [event.key, event.unicode, pygame.key.get_mods()]
            self.update_editor(*self.editor_current_pressed_key)
            self.editor_update_delay = 0.3
        if event.type == pygame.KEYUP:
            self.editor_current_pressed_key = [None, None, None]
        if event.type == pygame.VIDEORESIZE:
            self.surface = pygame.Surface((self.application.get_width(), self.application.get_height() - FONT_SIZE[1] * self.text_size))
            self.cache_lines_surface = pygame.Surface((self.application.get_width(), self.application.get_height() - FONT_SIZE[1] * self.text_size))
            self.forcefully_update_editor = 4

        return super().propagate_event(event)

    def get_amount_of_lines_surf_height(self):
        return round(self.surface.get_height() / (FONT_SIZE[1] * self.text_size))
    
    def get_amount_of_lines_surf_width(self):
        return round(self.surface.get_width() / (FONT_SIZE[0] * self.text_size))

    def draw_frame(self):
        # Calculate amount of lines that can fit the height of the editor surface
        amount_of_lines_surf_height = self.get_amount_of_lines_surf_height() - 1
        amount_of_lines_surf_width = self.get_amount_of_lines_surf_width() - 1

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
                and self.current_y_line_offset + amount_of_lines_surf_height + 1 < len(self.base_lines):
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
        line_x_offset = max(int(self.caret_position[0] - amount_of_lines_surf_width * 0.8), 0)
        # TODO: fix the condition below, so we don't redraw the whole text every frame
        if True or self.previous_lines_to_draw != lines_to_draw or self.forcefully_update_editor > 0:
            self.forcefully_update_editor -= 1
            self.forcefully_update_editor = max(self.forcefully_update_editor, 0)
            self.cache_lines_surface.fill((0, 0, 0))
            self.previous_lines_to_draw = lines_to_draw
            for line_number, tokens in enumerate(lines_to_draw):
                total_line_length = 0
                x_offset = 0
                y_offset = line_number * FONT_SIZE[1] * self.text_size

                for token in tokens:
                    line, color, background = self.parse_token(token, (255, 255, 255), (0, 0, 0))
                    line_length = len(line)
                    if total_line_length < line_x_offset:
                        line = line[line_x_offset - total_line_length:]
                    total_line_length += line_length
                    if not line:
                        continue
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
                ((self.caret_position[0] - line_x_offset) * FONT_SIZE[0] * self.text_size + self.lines_indicator_x_offset * self.text_size,
                 self.caret_position[1] * FONT_SIZE[1] * self.text_size + FONT_SIZE[1] * self.text_size - self.caret_height * self.text_size - self.current_y_line_offset * FONT_SIZE[1] * self.text_size,
                self.caret_width * self.text_size, self.caret_height * self.text_size)
            )

        return super().draw_frame()
