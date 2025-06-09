import pygame

from typing import List

from utils import *
from utils.font_renderer import draw_text
from utils.font import FONT_SIZE
from component import Component

from .buffer_mode import BufferMode


class BufferToken:
    def __init__(self, value, color, background=(0, 0, 0), is_new_line=False):
        self.value = value
        self.color = color
        self.background = background
        self.is_new_line = is_new_line

    def __repr__(self):
        return f"Token[{self.value}, {self.color}, {self.background}, {self.is_new_line}]"


class BufferViewportComponent(Component):
    def __init__(self, app, enable_line_indicator=False):
        super().__init__(app)
        self.base_lines = [""]
        self.token_lines = []
        self.text_scale = self.application.get_text_scale()
        self.scroll_offset = 5
        self.caret_width = 2
        self.caret_height = FONT_SIZE[1]
        self.buffer_id = None
        self.previous_mode = None
        self.enable_line_indicator = enable_line_indicator

        self.previous_lines_to_draw = None
        self.cache_lines_surface = pygame.Surface((self.surface.get_width(), self.surface.get_height()))
        # Amount of frames that needs to be forcefully drawn by the buffer without caching
        self.forcefully_update_buffer = 4

        self.caret_position = [0, 0]
        self.caret_blink_animation = 0
        self.caret_animation_speed = 6
        self.caret_blink_animation_flag = False
        self.lines_indicator_x_offset = 0
        self.current_y_line_offset = 0
        self.previous_y_line_offset = 0
        self.last_x_caret_position = 0

        self.command_executor = self.application.get_command_executor()

    def generate_tokens(self) -> List[List[BufferToken]]: ...

    def get_status_bar(self):
        return self.application.status_bar

    def update(self, dt):
        if self.previous_mode is None:
            self.previous_mode = self.get_mode()

        self.caret_blink_animation += dt * self.caret_animation_speed
        if self.caret_blink_animation > 2:
            self.caret_blink_animation_flag = not self.caret_blink_animation_flag
            self.caret_blink_animation = 0

        # Save current caret position in config
        if self.buffer_id:
            self.application.store_config_value("last_caret_position", self.buffer_id, self.caret_position)

        # Also the scroll offset
        if self.buffer_id:
            self.application.store_config_value(
                "last_scroll_offset", self.buffer_id,
                [self.current_y_line_offset,
                self.previous_y_line_offset,
                self.last_x_caret_position]
            )

        current_size = (self.surface.get_width(), self.surface.get_height())
        if current_size != (self.cache_lines_surface.get_width(), self.cache_lines_surface.get_height()):
            self.cache_lines_surface = pygame.Surface(current_size)

        return super().update(dt)

    def get_mode(self):
        return self.application.get_command_executor().get_mode()

    def set_mode(self, mode):
        self.application.get_command_executor().set_mode(mode)

    def update_buffer(self, key, unicode, modifier, skip_letter_insert=False, is_text_updated=False):
        if self.previous_mode != self.get_mode():
            self.previous_mode = self.get_mode()
            return

        if not self.base_lines:
            self.base_lines.append("")
        self.caret_blink_animation = 0
        self.caret_blink_animation_flag = True

        self.caret_position[1] = max(min(self.caret_position[1], len(self.base_lines) - 1), 0)
        self.caret_position[0] = max(min(self.caret_position[0], len(self.base_lines[self.caret_position[1]])), 0)
        line_text = self.base_lines[self.caret_position[1]]

        if key == pygame.K_TAB and self.get_mode() == BufferMode.COMMAND:
            self.caret_position[0] += 4
            if self.caret_position[0] > len(line_text):
                if self.caret_position[1] + 1 < len(self.base_lines):
                    self.caret_position[0] = 0
                    self.caret_position[1] += 1
                else:
                    self.caret_position[0] -= 4
            self.last_x_caret_position = self.caret_position[0]
         
        # TODO: fix modifier keys, they are not reported correctly when arrow key is pressed
        # If 'w' letter is pressed and in command mode, skip to next literal.
        # Or if a combination ctrl + right_arrow is pressed
        if (key == pygame.K_w and self.get_mode() == BufferMode.COMMAND) or \
            (key == pygame.K_RIGHT and (modifier & pygame.KMOD_CTRL or modifier & pygame.KMOD_LMETA)):
            self.step_next_literal()
        # If 'b' letter is pressed and in command mode, skip to previous literal.
        # Or if a combination ctrl + left_arrow is pressed
        if (key == pygame.K_b and self.get_mode() == BufferMode.COMMAND) or \
            (key == pygame.K_LEFT and (modifier & pygame.KMOD_CTRL or modifier & pygame.KMOD_LMETA)):
            self.step_previous_literal()

        # Key combinations for increasing/decreasing scale of the text
        if key == pygame.K_EQUALS and (modifier & pygame.KMOD_CTRL or modifier & pygame.KMOD_LMETA):
            if FONT_SIZE[1] * (self.text_scale + 3) < self.surface.get_height() * 0.2:
                scale = self.application.get_text_scale() + 1
                self.application.store_config_value("main", "text_scale", min(scale, 5))
            return
        elif key == pygame.K_MINUS and (modifier & pygame.KMOD_CTRL or modifier & pygame.KMOD_LMETA):
            scale = self.application.get_text_scale() - 1
            self.application.store_config_value("main", "text_scale", max(scale, 1))
            return
        
        if self.get_mode() != BufferMode.COMMAND_INSERT and modifier == 0:
            # Move caret using arrows
            if key == pygame.K_LEFT:
                self.caret_position[0] -= 1
                if self.caret_position[0] < 0 and self.caret_position[1] > 0:
                    self.caret_position[1] = max(self.caret_position[1] - 1, 0)
                    self.caret_position[0] = len(self.base_lines[self.caret_position[1]])
                elif self.caret_position[0] < 0:
                    self.caret_position[0] = 0                    
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

        # Step further to the next line if in command mode (the same as pressing down arrow)
        if key == pygame.K_RETURN and self.get_mode() == BufferMode.COMMAND:
            self.caret_position[1] += 1
            self.caret_position[1] = max(min(self.caret_position[1], len(self.base_lines) - 1), 0)
            self.caret_position[0] = min(self.last_x_caret_position, len(self.base_lines[self.caret_position[1]]))
        # Step further in the line if in command mode (the same as pressing right arrow)

        elif key == pygame.K_DELETE and self.get_mode() == BufferMode.INSERT:
            # Remove the character after the caret if in insert mode
            is_text_updated = True

            # If the caret is in the end of the line and we have a line below, connect it with the previous one
            if self.caret_position[0] == len(line_text) and self.caret_position[1] < len(self.base_lines) - 1:
                self.base_lines[self.caret_position[1]] += self.base_lines.pop(self.caret_position[1] + 1)
            # If the caret is not in the end of the line, just remove a letter
            else:
                self.base_lines[self.caret_position[1]] = line_text[:self.caret_position[0]] + line_text[self.caret_position[0] + 1:]
        elif key == pygame.K_BACKSPACE and self.get_mode() == BufferMode.INSERT:
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
        elif key == pygame.K_DELETE and self.get_mode() == BufferMode.COMMAND:
            self.caret_position[0] += 1
            self.caret_position[0] = max(min(self.caret_position[0], len(self.base_lines[self.caret_position[1]])), 0)
            self.last_x_caret_position = self.caret_position[0]
        elif key == pygame.K_BACKSPACE:
            # Step further in the line if in command mode (the same as pressing left arrow)
            if self.get_mode() == BufferMode.COMMAND:
                self.caret_position[0] -= 1
                self.caret_position[0] = max(min(self.caret_position[0], len(self.base_lines[self.caret_position[1]])), 0)
                self.last_x_caret_position = self.caret_position[0]
        elif unicode.isalpha() or is_allowed_nonalpha_chars(unicode) and len(unicode) >= 1:
            if not skip_letter_insert:
                if self.get_mode() == BufferMode.INSERT:
                    is_text_updated = True
                    line_text = self.insert_at_current_caret(unicode)
        
        # If text was updated, parse it again
        if is_text_updated:
            self.token_lines = self.generate_tokens()

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

            # Type the text into the buffer lines
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
        if event.type == pygame.VIDEORESIZE:
            self.forcefully_update_buffer = 4

        return super().propagate_event(event)
    
    def key_down_event(self, key, unicode, modifier):
        self.key_pressed_event(key, unicode, modifier)

    def key_pressed_event(self, key, unicode, modifier):
        self.update_buffer(key, unicode, modifier)

    def mouse_wheel_event(self, x, y):
        # TODO: I need to reverse the scrolling direction.
        #       I dunno if that's because i am on mac or thats's how
        #       things needs to be done. Look at that
        scroll_direction = y * -1 + self.caret_position[1]
        self.caret_position[1] = max(min(scroll_direction, len(self.base_lines) - 1), 1)
        self.caret_position[0] = len(self.base_lines[self.caret_position[1]])
        return super().mouse_wheel_event(x, y)

    def get_amount_of_lines_surf_height(self):
        return round(self.surface.get_height() / (FONT_SIZE[1] * self.text_scale))
    
    def get_amount_of_lines_surf_width(self):
        return round(self.surface.get_width() / (FONT_SIZE[0] * self.text_scale))

    def draw(self):
        # Calculate amount of lines that can fit the height of the buffer surface
        amount_of_lines_surf_height = self.get_amount_of_lines_surf_height() - 1
        amount_of_lines_surf_width = self.get_amount_of_lines_surf_width() - 1

        # Calculate the offset of lines that should be displayed on the screen based on current caret Y
        y_line_offset = self.caret_position[1] - amount_of_lines_surf_height

        # Scroll upwards if self.scroll_offset amount of lines is left before we reach the top of the screen
        if self.current_y_line_offset > 0 \
                and y_line_offset < self.current_y_line_offset - (amount_of_lines_surf_height - self.scroll_offset):
            self.current_y_line_offset -= (self.current_y_line_offset - (amount_of_lines_surf_height - self.scroll_offset)) - y_line_offset
        # Scroll upwards if self.scroll_offset amount of lines is left before we reach the bottom of the screen
        # And if we'd not go over the total amount of lines
        elif y_line_offset + self.scroll_offset > self.current_y_line_offset \
                and y_line_offset > self.previous_y_line_offset \
                and self.current_y_line_offset + amount_of_lines_surf_height + 1 < len(self.base_lines):
            self.current_y_line_offset += y_line_offset - self.previous_y_line_offset
        elif y_line_offset > self.current_y_line_offset:
            self.current_y_line_offset = max(y_line_offset, 0)
        self.previous_y_line_offset = y_line_offset

        # Get list of lines of texts relative to current caret position
        lines_to_draw = self.token_lines[self.current_y_line_offset:self.current_y_line_offset + amount_of_lines_surf_height + 1]

        # Draw the lines of text
        new_lines_indicator_width = 1

        # Draw line numbers indicator on the left
        if self.enable_line_indicator:
            for line_number, tokens in enumerate(lines_to_draw):
                y_offset = line_number * FONT_SIZE[1] * self.text_scale
                line_number += self.current_y_line_offset
                line_indicator_color = (170, 170, 170)

                if line_number == self.caret_position[1]:
                    line_indicator_color = (255, 255, 255)

                # Draw the line indicator
                line_indicator_len = ((self.lines_indicator_x_offset - 4) * self.text_scale) // FONT_SIZE[0] * self.text_scale
                line_indicator_text = str(line_number + 1)
                line_indicator_text = " " * (line_indicator_len - len(line_indicator_text)) + line_indicator_text
                line_indicator_width, _ = draw_text(
                    self.surface,
                    line_indicator_text,
                    line_indicator_color,
                    (0, 0, 0),
                    0, y_offset,
                    pixel_size=(self.text_scale, self.text_scale)
                )
                pygame.draw.rect(
                    self.surface,
                    line_indicator_color,
                    ((self.lines_indicator_x_offset - 4) * self.text_scale, y_offset,
                    int(1.5 * self.text_scale), FONT_SIZE[1] * self.text_scale)
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
        if True or self.previous_lines_to_draw != lines_to_draw or self.forcefully_update_buffer > 0:
            self.forcefully_update_buffer -= 1
            self.forcefully_update_buffer = max(self.forcefully_update_buffer, 0)
            self.cache_lines_surface.fill((0, 0, 0))
            self.previous_lines_to_draw = lines_to_draw
            for line_number, tokens in enumerate(lines_to_draw):
                total_line_length = 0
                x_offset = 0
                y_offset = line_number * FONT_SIZE[1] * self.text_scale

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
                        pixel_size=(self.text_scale, self.text_scale),
                    )
                    x_offset += offset * self.text_scale
            
            self.lines_indicator_x_offset = new_lines_indicator_width

        # Draw the lines
        if self.enable_line_indicator:
            self.surface.blit(self.cache_lines_surface, (self.lines_indicator_x_offset * self.text_scale, 0))
        else:
            self.surface.blit(self.cache_lines_surface, (0, 0))

        # Draw the caret at its current position
        if self.caret_blink_animation_flag and self.is_focused:
            pygame.draw.rect(
                self.surface,
                (255, 255, 255),
                ((self.caret_position[0] - line_x_offset) * FONT_SIZE[0] * self.text_scale + self.lines_indicator_x_offset * self.text_scale,
                 self.caret_position[1] * FONT_SIZE[1] * self.text_scale + FONT_SIZE[1] * self.text_scale - self.caret_height * self.text_scale - self.current_y_line_offset * FONT_SIZE[1] * self.text_scale,
                self.caret_width * self.text_scale, self.caret_height * self.text_scale)
            )

        return super().draw()
