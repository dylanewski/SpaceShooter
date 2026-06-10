import pygame
from .constants import LINE_WIDTH, SCREEN_WIDTH, PLAYER_MAX_HP


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


def draw_hp_bar(screen, font, hp, regen_rate):
    BAR_W, BAR_H = 160, 16
    bar_x = SCREEN_WIDTH - 20 - BAR_W
    bar_y = 30
    frac  = max(0.0, min(1.0, hp / PLAYER_MAX_HP))

    if frac > 0.5:
        r = int(255 * (1.0 - frac) * 2)
        color = (r, 200, 60)
    else:
        g = int(200 * frac * 2)
        color = (220, g, 30)

    pygame.draw.rect(screen, (40, 40, 40), (bar_x, bar_y, BAR_W, BAR_H))
    pygame.draw.rect(screen, color,        (bar_x, bar_y, int(BAR_W * frac), BAR_H))
    pygame.draw.rect(screen, "white",      (bar_x, bar_y, BAR_W, BAR_H), LINE_WIDTH)

    lbl = font.render(f"{int(hp)}", True, "white")
    screen.blit(lbl, lbl.get_rect(midright=(bar_x - 6, bar_y + BAR_H // 2)))
