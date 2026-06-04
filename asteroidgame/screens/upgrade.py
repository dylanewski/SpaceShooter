import random
import pygame
from ..constants import SCREEN_WIDTH, SCREEN_HEIGHT, LINE_WIDTH

UPGRADE_POOL = [
    {"name": "Rapid Fire",    "desc": "Reduce shot cooldown"},
    {"name": "Power Shots",   "desc": "Increase shot damage"},
    {"name": "Speed Boost",   "desc": "Move faster"},
    {"name": "Big Shots",     "desc": "Larger projectiles"},
    {"name": "Shield Up",     "desc": "Tighter hitbox"},
    {"name": "Double XP",     "desc": "Earn 2x XP"},
    {"name": "Tough Hull",    "desc": "Survive one hit"},
    {"name": "Magnet Pull",   "desc": "Pull in XP orbs"},
    {"name": "Overdrive",     "desc": "Temporary speed burst"},
]

_overlay = None


def _get_overlay():
    global _overlay
    if _overlay is None:
        _overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        _overlay.fill((0, 0, 0, 200))
    return _overlay


def run(screen, clock, font, big_font) -> str:
    choices = random.sample(UPGRADE_POOL, 3)

    CARD_W, CARD_H = 300, 180
    GAP = 40
    total_w = 3 * CARD_W + 2 * GAP
    card_x = (SCREEN_WIDTH - total_w) // 2
    card_y = SCREEN_HEIGHT // 2 - CARD_H // 2 + 30

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

        screen.blit(_get_overlay(), (0, 0))

        title = big_font.render("LEVEL  UP", True, "white")
        screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, card_y - 70)))

        for rect, upgrade in cards:
            hovering = rect.collidepoint(mouse_pos)
            pygame.draw.rect(screen, (70, 70, 70) if hovering else (30, 30, 30), rect)
            pygame.draw.rect(screen, "white", rect, LINE_WIDTH)
            name = font.render(upgrade["name"], True, "white")
            desc = font.render(upgrade["desc"], True, (180, 180, 180))
            screen.blit(name, name.get_rect(center=(rect.centerx, rect.centery - 25)))
            screen.blit(desc, desc.get_rect(center=(rect.centerx, rect.centery + 25)))

        pygame.display.flip()
        clock.tick(60)
