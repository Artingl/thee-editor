import pygame

from component import Component

from .editor_component import EditorViewportComponent
from .buffer_mode import BufferMode


class Statusbar(Component):
    MODE_SIGNS = {
        BufferMode.COMMAND: 'C',
        BufferMode.INSERT: 'I',
        BufferMode.COMMAND_INSERT: 'X',
    }

    def __init__(self, app):
        super().__init__(app)
        self.status_bar_text = ""
        self.status_bar_text_color = (255, 255, 255)
        self.status_bar_text_background = (0, 0, 0)
        self.status_bar_text_timeout = 0

    def propagate_event(self, event):
        font_size = self.application.get_font_driver().get_font_size()
        if event.type == pygame.VIDEORESIZE:
            self.surface = pygame.Surface((self.application.get_width(), font_size[1] * self.application.get_text_scale()))
            self.y = self.application.get_height() - font_size[1] * self.application.get_text_scale()
    
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
    
    def draw(self):
        font_size = self.application.get_font_driver().get_font_size()
        self.update_dimensions(
            (self.application.get_width(), font_size[1] * self.application.get_text_scale()),
            (0, self.application.get_height() - font_size[1] * self.application.get_text_scale())
        )

        command_executor = self.application.get_command_executor()
        current_buffer = self.application.get_focused_buffer_viewport()
        text_scale = self.application.get_text_scale()

        status_bar_background_color = (0, 0, 0)
        status_bar_color = (255, 255, 255)
        status_bar_text = ""

        if isinstance(current_buffer, EditorViewportComponent):
            status_bar_text = f"{current_buffer.filename} ({current_buffer.file_type}); "

        status_bar_text += f"{current_buffer.caret_position[1] + 1} line at {current_buffer.caret_position[0]}"
        if command_executor.get_mode() == BufferMode.COMMAND_INSERT:
            status_bar_text = f":{command_executor.command_insert_value}"
            self.status_bar_text_timeout = 0
        elif self.status_bar_text_timeout > 0:
            status_bar_text = self.status_bar_text
            status_bar_color = self.status_bar_text_color
            status_bar_background_color = self.status_bar_text_background

        if command_executor.get_mode() == BufferMode.INSERT:
            status_bar_background_color = (100, 100, 190)

        # Draw current buffer mode with a separator
        self.application.font_driver.draw_text(
            self.surface,
            Statusbar.MODE_SIGNS[command_executor.get_mode()],
            (255, 255, 255),
            (0, 0, 0),
            (max(current_buffer.lines_indicator_x_offset, (font_size[0] * 2 + 2) * text_scale) - 4) * text_scale - (font_size[0] + 2) * text_scale, 0,
            pixel_size=(text_scale, text_scale)
        )
        pygame.draw.rect(
            self.surface,
            (255, 255, 255),
            ((max(current_buffer.lines_indicator_x_offset, (font_size[0] * 2 + 2) * text_scale) - 4) * text_scale, 0,
            int(1.5 * text_scale), font_size[1] * text_scale)
        )
        # Draw status bar
        self.application.font_driver.draw_text(
            self.surface,
            status_bar_text,
            status_bar_color,
            status_bar_background_color,
            max(current_buffer.lines_indicator_x_offset, (font_size[0] * 2 + 2) * text_scale), 0,
            (text_scale, text_scale)
        )
        
        pygame.draw.rect(
            self.surface,
            (170, 170, 170),
            (0, 0, self.get_width(), 1)
        )

        return super().draw()
