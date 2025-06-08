import pygame

from component import Component
from utils import draw_text, FONT_SIZE

from .buffer_mode import BufferMode


class Statusbar(Component):
    MODE_SIGNS = {
        BufferMode.COMMAND: 'C',
        BufferMode.INSERT: 'I',
        BufferMode.COMMAND_INSERT: 'CI',
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

        if self.editor.mode == BufferMode.COMMAND_INSERT:
            status_bar_text = f":{self.editor.command_insert_value}"
            self.status_bar_text_timeout = 0
        elif self.status_bar_text_timeout > 0:
            status_bar_text = self.status_bar_text
            status_bar_color = self.status_bar_text_color
            status_bar_background_color = self.status_bar_text_background

        if self.editor.mode == BufferMode.INSERT:
            status_bar_background_color = (100, 100, 190)

        # Draw current editor mode with a separator
        draw_text(
            self.surface,
            Statusbar.MODE_SIGNS[self.editor.mode],
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

