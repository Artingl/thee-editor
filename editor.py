import pygame
import string

from syntax_highlighter import *
from component import *
from font import draw_text, FONT_SIZE


class Editor(Component):
    def __init__(self):
        super().__init__((800, 600))

        self.file_name = "main.c"
        self.base_lines_of_text = []
        self.token_lines = []
        self.text_size = 1
        self.scroll_offset = 4
        self.caret_width = 1
        self.caret_height = FONT_SIZE[1]
        self.syntax_highlighter = CSyntaxParser(self)

        self.caret_position = [0, 0]
        self.caret_blink_animation = 0
        self.caret_animation_speed = 6
        self.caret_blink_animation_flag = False
        self.editor_type_delay = 0
        self.editor_current_pressed_key = [None, None, None]
        self.lines_indicator_x_offset = 0
        self.current_y_line_offset = 0
        self.previous_y_line_offset = 0
        self.last_x_caret_position = 0

        self.load_file()

    @classmethod
    def __get_whitespaces(self, line):
        whitespaces_count = 0
        for i in line:
            if i == ' ':
                whitespaces_count += 1
            else:
                break
        return whitespaces_count

    @classmethod
    def __is_allowed_nonalpha_chars(cls, chars):
        allowed_nonalpha_chars = string.punctuation + string.digits + " "
        return all(i in allowed_nonalpha_chars for i in chars)

    def get_text_color(self, x, y):
        return self.syntax_highlighter.get_color(self.caret_position[0] + x, self.caret_position[1] + y)

    def load_file(self):
        with open(self.file_name, "r") as file:
            self.base_lines_of_text = file.read().split("\n")
            self.token_lines = self.syntax_highlighter.parse_code(self.base_lines_of_text)

    def save_file(self):
        with open(self.file_name, "w") as file:
            file.write('\n'.join(self.base_lines_of_text))

    def update(self, dt):
        self.caret_blink_animation += dt * self.caret_animation_speed
        self.editor_type_delay -= dt
        if self.caret_blink_animation > 2:
            self.caret_blink_animation_flag = not self.caret_blink_animation_flag
            self.caret_blink_animation = 0
        
        if self.editor_type_delay <= 0:
            self.update_editor(*self.editor_current_pressed_key)
            self.editor_type_delay = 0.02

    def update_editor(self, key, key_unicode, key_modifier):
        if not key:
            return

        is_text_updated = False
        line_text = self.base_lines_of_text[self.caret_position[1]]
        self.caret_blink_animation = 0
        self.caret_blink_animation_flag = True

        if key == pygame.K_TAB:
            key_unicode = "    "

        # Check if a key combination was pressed
        if key == pygame.K_s and key_modifier & pygame.KMOD_CTRL:
            self.save_file()
        elif key == pygame.K_EQUALS and key_modifier & pygame.KMOD_CTRL:
            self.text_size += 1
        elif key == pygame.K_MINUS and key_modifier & pygame.KMOD_CTRL:
            self.text_size -= 1
            self.text_size = max(self.text_size, 1)
        else:
            if key == pygame.K_LEFT:
                self.caret_position[0] -= 1
                self.caret_position[0] = max(min(self.caret_position[0], len(self.base_lines_of_text[self.caret_position[1]])), 0)
                self.last_x_caret_position = self.caret_position[0]
            elif key == pygame.K_RIGHT:
                self.caret_position[0] += 1
                self.caret_position[0] = max(min(self.caret_position[0], len(self.base_lines_of_text[self.caret_position[1]])), 0)
                self.last_x_caret_position = self.caret_position[0]
            elif key == pygame.K_UP:
                self.caret_position[1] -= 1
                self.caret_position[1] = max(min(self.caret_position[1], len(self.base_lines_of_text) - 1), 0)
                self.caret_position[0] = min(self.last_x_caret_position, len(self.base_lines_of_text[self.caret_position[1]]))
            elif key == pygame.K_DOWN:
                self.caret_position[1] += 1
                self.caret_position[1] = max(min(self.caret_position[1], len(self.base_lines_of_text) - 1), 0)
                self.caret_position[0] = min(self.last_x_caret_position, len(self.base_lines_of_text[self.caret_position[1]]))
            elif key == pygame.K_RETURN:
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
            elif key == pygame.K_DELETE:
                is_text_updated = True

                # If the caret is in the end of the line and we have a line below, connect it with the previous one
                if self.caret_position[0] == len(line_text) and self.caret_position[1] < len(self.base_lines_of_text) - 1:
                    self.base_lines_of_text[self.caret_position[1]] += self.base_lines_of_text.pop(self.caret_position[1] + 1)
                # If the caret is not in the end of the line, just remove a letter
                else:
                    self.base_lines_of_text[self.caret_position[1]] = line_text[:self.caret_position[0]] + line_text[self.caret_position[0] + 1:]
            elif key == pygame.K_BACKSPACE:
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
            elif key_unicode.isalpha() or Editor.__is_allowed_nonalpha_chars(key_unicode) and len(key_unicode) >= 1:
                is_text_updated = True
                
                for char in key_unicode:
                    # Type the text into the editor lines
                    self.base_lines_of_text[self.caret_position[1]] = line_text = line_text[:self.caret_position[0]] + char + line_text[self.caret_position[0]:]
                    self.caret_position[0] += 1
        if is_text_updated:
            self.token_lines = self.syntax_highlighter.parse_code(self.base_lines_of_text)
        
    def propagate_event(self, event):
        if event.type == pygame.KEYDOWN:
            self.editor_current_pressed_key = [event.key, event.unicode, event.mod]
            self.update_editor(*self.editor_current_pressed_key)
            self.editor_type_delay = 0.3
        if event.type == pygame.KEYUP:
            self.editor_current_pressed_key = [None, None, None]
        if event.type == pygame.VIDEORESIZE:
            self.surface = pygame.Surface((event.w, event.h))

        return super().propagate_event(event)

    def draw_frame(self):
        # Calculate amount of lines that can fit the height of the editor surface
        amount_of_lines_surf_height = int(self.surface.get_height() / (FONT_SIZE[1] * self.text_size)) - 1

        # Calculate the offset of lines that should be displayed on the screen based on current caret Y
        y_line_offset = self.caret_position[1] - amount_of_lines_surf_height

        # Scroll upwards if self.scroll_offset amount of lines is left before we reach the top of the screen
        if self.current_y_line_offset > 0 \
                and y_line_offset < self.current_y_line_offset - (amount_of_lines_surf_height - self.scroll_offset):
            self.current_y_line_offset -= 1
        # Scroll upwards if self.scroll_offset amount of lines is left before we reach the bottom of the screen
        # And if we'd not go over the total amount of lines
        elif self.current_y_line_offset > 0 \
                and y_line_offset + self.scroll_offset > self.current_y_line_offset \
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

        for line_number, tokens in enumerate(lines_to_draw):
            x_offset = 0
            y_offset = line_number * FONT_SIZE[1] * self.text_size
            line_number += self.current_y_line_offset

            # Draw the line indicator
            line_indicator_width, _ = draw_text(
                self.surface,
                f"{line_number + 1}",
                (255, 255, 255),
                (0, 0, 0),
                0, y_offset,
                pixel_size=(self.text_size, self.text_size)
            )
            pygame.draw.rect(
                self.surface,
                (255, 255, 255),
                ((self.lines_indicator_x_offset - 4) * self.text_size, y_offset,
                int(1.5 * self.text_size), FONT_SIZE[1] * self.text_size)
            )

            # Dynamically update the lines indicator offset based on the width of the line number string
            line_indicator_width += 5
            if line_indicator_width > new_lines_indicator_width:
                new_lines_indicator_width = line_indicator_width
                if self.lines_indicator_x_offset == 0:
                    self.lines_indicator_x_offset = new_lines_indicator_width

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
                    self.surface,
                    line,
                    color, background,
                    self.lines_indicator_x_offset * self.text_size + x_offset, y_offset,
                    pixel_size=(self.text_size, self.text_size),
                )
                x_offset += offset * self.text_size
            
        self.lines_indicator_x_offset = new_lines_indicator_width

        # Draw the caret at its current position
        if self.caret_blink_animation_flag:
            pygame.draw.rect(
                self.surface,
                (255, 255, 255),
                (self.caret_position[0] * FONT_SIZE[0] * self.text_size + self.lines_indicator_x_offset * self.text_size,
                 self.caret_position[1] * FONT_SIZE[1] * self.text_size +FONT_SIZE[1] * self.text_size - self.caret_height * self.text_size - self.current_y_line_offset * FONT_SIZE[1] * self.text_size,
                self.caret_width * self.text_size, self.caret_height * self.text_size)
            )

        return super().draw_frame()

        

        
