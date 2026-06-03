import pygame
from .constants import LINE_WIDTH


def make_button(center, width=220, height=60):
    rect = pygame.Rect(0, 0, width, height)
    rect.center = center
    return rect


def draw_button(screen, font, rect, label):
    pygame.draw.rect(screen, "white", rect, LINE_WIDTH)
    text = font.render(label, True, "white")
    screen.blit(text, text.get_rect(center=rect.center))
