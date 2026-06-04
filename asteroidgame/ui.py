import pygame
from .constants import LINE_WIDTH, SCREEN_WIDTH, MAX_LIVES


def make_button(center, width=220, height=60):
    rect = pygame.Rect(0, 0, width, height)
    rect.center = center
    return rect


def draw_button(screen, font, rect, label):
    pygame.draw.rect(screen, "white", rect, LINE_WIDTH)
    text = font.render(label, True, "white")
    screen.blit(text, text.get_rect(center=rect.center))


def draw_xp_bar(screen, font, cx, level, xp, xp_to_next, xp_visual=None):
    BAR_W, BAR_H = 500, 18
    bar_x = cx - BAR_W // 2
    bar_y = 10

    target = min(xp / xp_to_next, 1.0)
    visual = target if xp_visual is None else min(xp_visual, 1.0)

    fill_target = int(BAR_W * target)
    fill_visual = int(BAR_W * visual)

    pygame.draw.rect(screen, (40, 40, 40), (bar_x, bar_y, BAR_W, BAR_H))
    if fill_target > fill_visual:
        pygame.draw.rect(screen, (90, 90, 90),
                         (bar_x + fill_visual, bar_y, fill_target - fill_visual, BAR_H))
    pygame.draw.rect(screen, "white", (bar_x, bar_y, fill_visual, BAR_H))
    pygame.draw.rect(screen, "white", (bar_x, bar_y, BAR_W, BAR_H), LINE_WIDTH)

    lvl_text = font.render(f"{level}", True, "white")
    screen.blit(lvl_text, lvl_text.get_rect(midright=(bar_x - 10, bar_y + BAR_H // 2)))


def draw_lives(screen, lives, regen_progress):
    ICON_R = 10
    GAP    = 28
    y      = 19
    start_x = SCREEN_WIDTH - 20 - (MAX_LIVES - 1) * GAP

    for i in range(MAX_LIVES):
        x = start_x + i * GAP
        if i < lives:
            pygame.draw.circle(screen, "white", (x, y), ICON_R)
        else:
            pygame.draw.circle(screen, (60, 60, 60), (x, y), ICON_R)
            pygame.draw.circle(screen, "white",      (x, y), ICON_R, LINE_WIDTH)
            if i == lives:
                bar_w  = ICON_R * 2
                filled = int(bar_w * regen_progress)
                pygame.draw.rect(screen, (50, 50, 50),  (x - ICON_R, y + ICON_R + 4, bar_w,   3))
                pygame.draw.rect(screen, "white",        (x - ICON_R, y + ICON_R + 4, filled, 3))
