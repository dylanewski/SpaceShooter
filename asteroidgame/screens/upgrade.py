import random
from collections import Counter
import pygame
from ..constants import SCREEN_WIDTH, SCREEN_HEIGHT, LINE_WIDTH

RARITY_WEIGHTS = {
    "common":    70,
    "uncommon":  18,
    "rare":      9,
    "legendary": 1,
}

RARITY_COLORS = {
    "common":    (255, 255, 255),
    "uncommon":  (80, 200, 100),
    "rare":      (80, 130, 255),
    "legendary": (255, 160, 30),
}

UPGRADE_POOL = [
    {"name": "Rapid Fire",       "rarity": "common"},
    {"name": "Higher Caliber Rounds", "rarity": "common"},
    {"name": "XP Generator",     "rarity": "common"},
    {"name": "Bigger Bullets",   "rarity": "common"},
    {"name": "Speed Boost",      "rarity": "common"},
    {"name": "Bolt Dash",        "rarity": "rare"},
    {"name": "Quick Regen",      "rarity": "common"},
    {"name": "Crit Chance Up",   "rarity": "common"},
    {"name": "Shield",           "rarity": "rare"},
    {"name": "Homing Shots",     "rarity": "rare"},
    {"name": "Missile Salvo",    "rarity": "rare"},
    {"name": "Laser Beam",       "rarity": "rare"},
    {"name": "Ricochet",         "rarity": "rare"},
    {"name": "Explosive Rounds", "rarity": "rare"},
    {"name": "Mines",            "rarity": "uncommon"},
    {"name": "Pulse Wave",       "rarity": "uncommon"},
    {"name": "Afterburn",        "rarity": "uncommon"},
    {"name": "Plow",             "rarity": "uncommon"},
    {"name": "Vortex Field",     "rarity": "legendary"},
    {"name": "Little Buddy",     "rarity": "legendary"},
]

_overlay    = None
_name_font  = None
_title_font = None


def _get_name_font():
    global _name_font
    if _name_font is None:
        _name_font = pygame.font.Font("assets/fonts/Symtext.ttf", 22)
    return _name_font


def _get_title_font():
    global _title_font
    if _title_font is None:
        _title_font = pygame.font.Font("assets/fonts/Symtext.ttf", 56)
    return _title_font


def _get_overlay():
    global _overlay
    if _overlay is None:
        _overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        _overlay.fill((0, 0, 0, 180))
    return _overlay


def _weighted_sample(pool, k):
    tier_counts = Counter(u["rarity"] for u in pool)
    weights = [RARITY_WEIGHTS[u["rarity"]] / tier_counts[u["rarity"]] for u in pool]

    chosen = []
    available = list(zip(pool, weights))
    for _ in range(min(k, len(available))):
        total = sum(w for _, w in available)
        r = random.uniform(0, total)
        cumulative = 0
        for i, (item, weight) in enumerate(available):
            cumulative += weight
            if r <= cumulative:
                chosen.append(item)
                available.pop(i)
                break
    return chosen


def run(screen, clock, font, background) -> str:
    choices = _weighted_sample(UPGRADE_POOL, 3)

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

        title = _get_title_font().render("LEVEL  UP", True, "white")
        screen.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, card_y - 60)))

        for rect, upgrade in cards:
            hovering = rect.collidepoint(mouse_pos)
            rarity_color = RARITY_COLORS[upgrade["rarity"]]

            pygame.draw.rect(screen, (70, 70, 70) if hovering else (30, 30, 30), rect)
            pygame.draw.rect(screen, rarity_color, rect, LINE_WIDTH)

            icon_rect = pygame.Rect(rect.centerx - ICON_SIZE // 2, rect.top + 15, ICON_SIZE, ICON_SIZE)
            pygame.draw.rect(screen, (50, 50, 50), icon_rect)
            pygame.draw.rect(screen, rarity_color, icon_rect, LINE_WIDTH)

            name = _get_name_font().render(upgrade["name"], True, rarity_color)
            screen.blit(name, name.get_rect(center=(rect.centerx, rect.bottom - 22)))

        pygame.display.flip()
        clock.tick(60)
