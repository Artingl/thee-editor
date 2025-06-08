import pygame

from functools import lru_cache
from .font import *

@lru_cache(maxsize=128)
def draw_bitmap(color, background, bitmap, width, height, pixel_size: int = (1, 1)):
    surface = pygame.Surface((width * pixel_size[0], height * pixel_size[1]))
    for index_x in range(width):
        for index_y in range(height):
            index = (index_y) * width + index_x
            if bitmap[index]:
                pygame.draw.rect(surface, color, (index_x * pixel_size[1], index_y * pixel_size[1], *pixel_size))
            else:
                pygame.draw.rect(surface, background, (index_x * pixel_size[1], index_y * pixel_size[1], *pixel_size))
    return surface


def draw_text(surface, text, color, background, x, y, pixel_size=(5, 5)):
    largest_x = 0
    x_offset = 0
    y_offset = 0
    for letter in text:
        if letter == "\n":
            if largest_x < x_offset:
                largest_x = x_offset
            x_offset = 0
            y_offset += FONT_SIZE[1] * pixel_size[1]
            continue
        
        if bitmap := BITMAP_LETTERS_FONT.get(letter, BITMAP_LETTERS_FONT[None]):
            result_surface = draw_bitmap(
                color, background,
                bitmap, *FONT_SIZE,
                pixel_size=pixel_size
            )
            surface.blit(result_surface, (x + x_offset, y + y_offset))
        x_offset += FONT_SIZE[0] * pixel_size[0]
    
    if largest_x < x_offset:
        largest_x = x_offset
    return int(largest_x / pixel_size[0]), int(y_offset / pixel_size[1])

