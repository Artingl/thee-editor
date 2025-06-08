from .buffer_component import BufferViewportComponent

from utils import FONT_SIZE


class EditorViewportComponent(BufferViewportComponent):
    def __init__(self, app):
        super().__init__(app, (app.get_width(), app.get_height() - FONT_SIZE[1]))

