import math
import random
import pygame
from ..constants import SCREEN_WIDTH, SCREEN_HEIGHT
from .boss_shot import BossShot

BOSS2_MAX_HP     = 1200
BOSS2_RADIUS     = 80    # collision + visual radius
BOSS2_SHOOT_RATE = 2.0   # seconds between shots


class Boss2(pygame.sprite.Sprite):
    containers: tuple

    def __init__(self, x, y, player):
        if hasattr(self, "containers"):
            super().__init__(*self.containers)
        else:
            super().__init__()
        self.position         = pygame.Vector2(x, y)
        self._player          = player
        self.health           = BOSS2_MAX_HP
        self.crit_flash_timer = 0.0
        self._shoot_timer     = 0.0
        self._age             = 0.0

    # --- interface expected by combat / draw systems ---

    def get_segments(self):
        """Single segment: (position, radius)."""
        yield (pygame.Vector2(self.position), BOSS2_RADIUS)

    def take_damage(self, amount: int) -> bool:
        self.health -= amount
        return self.health <= 0

    # --- internal ---

    def _shoot(self):
        if not self._player.alive():
            return
        d = self._player.position - self.position
        # fire 3 spread shots
        for offset in (-15, 0, 15):
            BossShot(self.position.x, self.position.y, d.rotate(offset))

    def update(self, dt: float) -> None:
        self._age             += dt
        self.crit_flash_timer  = max(0.0, self.crit_flash_timer - dt)
        self._shoot_timer     += dt
        if self._shoot_timer >= BOSS2_SHOOT_RATE:
            self._shoot_timer = 0.0
            self._shoot()

    def draw(self, screen):
        pos   = (int(self.position.x), int(self.position.y))
        pulse = math.sin(self._age * 2.0) * 6

        if self.crit_flash_timer > 0:
            pygame.draw.circle(screen, (255, 255, 255), pos, BOSS2_RADIUS)
            return

        r = int(BOSS2_RADIUS + pulse)
        # outer glow ring
        pygame.draw.circle(screen, (60, 0, 80),   pos, r + 8)
        # body
        pygame.draw.circle(screen, (120, 20, 160), pos, r)
        # inner core
        pygame.draw.circle(screen, (200, 80, 240), pos, r // 2)
        # border ring
        pygame.draw.circle(screen, (180, 40, 220), pos, r, 3)

        # PLACEHOLDER label
        try:
            font = pygame.font.SysFont(None, 28)
            lbl  = font.render("BOSS 2", True, (255, 200, 255))
            screen.blit(lbl, lbl.get_rect(center=pos))
        except Exception:
            pass
