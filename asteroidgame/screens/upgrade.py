import random
import pygame
from ..constants import SCREEN_WIDTH, SCREEN_HEIGHT, LINE_WIDTH

UPGRADE_POOL = [
    {"name": "Rapid Fire"},
    {"name": "Power Shot"},
    {"name": "Shield"},
    {"name": "XP Generator"},
    {"name": "Larger Artillery"},
    {"name": "Speed Boost"},
    {"name": "Quick Regen"},
]

_overlay = None
_name_font = None


def _get_name_font():
    global _name_font
    if _name_font is None:
        _name_font = pygame.font.Font("assets/fonts/8-bitanco.ttf", 28)
    return _name_font


def _get_overlay():
    global _overlay
    if _overlay is None:
        _overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        _overlay.fill((0, 0, 0, 180))
    return _overlay


def run(screen, clock, font, big_font, background) -> str:
    choices = random.sample(UPGRADE_POOL, 3)

    CARD_W, CARD_H = 220, 230
    ICON_SIZE = 140
    GAP = 40
    total_w = 3 * CARD_W + 2 * GAP
    card_x = (SCREEN_WIDTH - total_w) // 2
    card_y = SCREEN_HEIGHT // 2 - CARD_H // 2 + 20

    cards = [
        (pygame.Rect(card_x + i * (CARD_W + GAP), card_y, CARD_W, CARD_H), choice)
        for i, choice in enumerate(choices)
    ]

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.MOUSEBUTTONDOWN:
                for rect, upgrade in cards:
                    if rect.collidepoint(event.pos):
                        return upgrade["name"]

        mouse_pos = pygame.mouse.get_pos()

        screen.blit(background, (0, 0))
        screen.blit(_get_overlay(), (0, 0))

        title = big_font.render("LEVEL  UP", True, "white")
        screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, card_y - 60)))

        for rect, upgrade in cards:
            hovering = rect.collidepoint(mouse_pos)
            pygame.draw.rect(screen, (70, 70, 70) if hovering else (30, 30, 30), rect)
            pygame.draw.rect(screen, "white", rect, LINE_WIDTH)

            icon_rect = pygame.Rect(rect.centerx - ICON_SIZE // 2, rect.top + 15, ICON_SIZE, ICON_SIZE)
            pygame.draw.rect(screen, (50, 50, 50), icon_rect)
            pygame.draw.rect(screen, (100, 100, 100), icon_rect, LINE_WIDTH)

            name = _get_name_font().render(upgrade["name"], True, "white")
            screen.blit(name, name.get_rect(center=(rect.centerx, rect.bottom - 22)))

        pygame.display.flip()
        clock.tick(60)
