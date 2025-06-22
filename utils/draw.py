import pygame
from pygame.rect import Rect
from pygame.surface import Surface


def draw_transparent_rect(surface: Surface, color, rect, *args, **kwargs) -> Rect:
    position = (0, 0)
    dimensions = (0, 0)
    if isinstance(rect, Rect):
        position = (rect.x, rect.y)
        dimensions = (rect.width, rect.height)
    elif (isinstance(rect, list) or isinstance(rect, tuple)) and len(rect) > 3:
        position = (rect[0], rect[1])
        dimensions = (rect[2], rect[3])
    else:
        raise ValueError("Invalid value for rect")

    alpha_surf = pygame.Surface(dimensions, pygame.SRCALPHA)
    result = pygame.draw.rect(alpha_surf, color, (0, 0, *dimensions), *args, **kwargs)
    surface.blit(alpha_surf, position)
    return result
