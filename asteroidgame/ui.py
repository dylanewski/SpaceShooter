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


def draw_xp_bar(screen, font, cx, level, xp, xp_to_next):
    BAR_W, BAR_H = 500, 18
    bar_x = cx - BAR_W // 2
    bar_y = 10

    fill = int(BAR_W * min(xp / xp_to_next, 1.0))
    pygame.draw.rect(screen, (40, 40, 40),   (bar_x, bar_y, BAR_W, BAR_H))
    pygame.draw.rect(screen, "white",        (bar_x, bar_y, fill,  BAR_H))
    pygame.draw.rect(screen, "white",        (bar_x, bar_y, BAR_W, BAR_H), LINE_WIDTH)

    lvl_text = font.render(f"LVL {level}", True, "white")
    screen.blit(lvl_text, lvl_text.get_rect(midright=(bar_x - 10, bar_y + BAR_H // 2)))
