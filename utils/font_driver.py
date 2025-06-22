import pygame
import string

from enum import Enum
from functools import lru_cache

from .font_bitmap import *
from .strings import is_allowed_alpha_chars


class FontType(Enum):
    BITMAP: str = 'bitmap'
    TRUETYPE_MONOSPACE = 'tt_monospace'


class FontDriver:
    def __init__(self, font_type):
        self.font_type = font_type
        self.current_font_name = "CozetteVector"
        self.font_cache = {}

    def change_font_type(self, type):
        self.font_type = type

    def get_font_size(self):
        if self.font_type == FontType.TRUETYPE_MONOSPACE:
            return 9, 20
        return 8, 16

    @lru_cache(maxsize=128)
    def draw_bitmap(
        self,
        color,
        background,
        bitmap,
        pixel_size: int = (1, 1),
    ):
        width, height = self.get_font_size()
        surface = pygame.Surface((width * pixel_size[0], height * pixel_size[1]), pygame.SRCALPHA)
        for index_x in range(width):
            for index_y in range(height):
                index = (index_y) * width + index_x
                if bitmap[index]:
                    pygame.draw.rect(surface, color, (index_x * pixel_size[1], index_y * pixel_size[1], *pixel_size))
                else:
                    pygame.draw.rect(surface, background, (index_x * pixel_size[1], index_y * pixel_size[1], *pixel_size))
        return surface

    @lru_cache(maxsize=128)
    def draw_truetype_monospace(
        self,
        color,
        background,
        letter,
        pixel_size: int = (1, 1),
    ):
        font_name = self.current_font_name
        if font_name not in self.font_cache:
            self.font_cache[font_name] = pygame.font.Font(f"assets/font/{font_name}.ttf", self.get_font_size()[1])
        surf = self.font_cache[font_name].render(letter, False, color, background)
        # if pixel_size != (1, 1):
        #     surf = pygame.transform.scale(surf, pixel_size)
        return surf

    def draw_text(
        self,
        surface,
        text,
        color,
        background,
        x, y,
        pixel_size=(5, 5),
    ):
        font_size = self.get_font_size()
        largest_x = 0
        x_offset = 0
        y_offset = 0
        for letter in text:
            if letter == "\n":
                if largest_x < x_offset:
                    largest_x = x_offset
                x_offset = 0
                y_offset += font_size[1] * pixel_size[1]
                continue
            
            result_surface = None
            if self.font_type == FontType.BITMAP:
                if bitmap := BITMAP_LETTERS_FONT.get(letter, BITMAP_LETTERS_FONT[None]):
                    result_surface = self.draw_bitmap(
                        color, background,
                        bitmap,
                        pixel_size=pixel_size
                    )
            elif self.font_type == FontType.TRUETYPE_MONOSPACE:
                if is_allowed_alpha_chars(letter, additional=string.punctuation + " "):
                    result_surface = self.draw_truetype_monospace(
                        color, background,
                        letter,
                        pixel_size=pixel_size
                    )
            
            if result_surface:
                surface.blit(result_surface, (x + x_offset, y + y_offset))
            x_offset += font_size[0] * pixel_size[0]
        
        if largest_x < x_offset:
            largest_x = x_offset
        return int(largest_x / pixel_size[0]), int(y_offset / pixel_size[1])
