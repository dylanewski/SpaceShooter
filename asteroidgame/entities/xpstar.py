import math
import random
import pygame
from ..constants import SCREEN_WIDTH, SCREEN_HEIGHT

XP_STAR_RADIUS   = 12
XP_STAR_VALUE    = 10
XP_STAR_LIFETIME = 12.0


class XPStar(pygame.sprite.Sprite):
    containers: tuple

    def __init__(self):
        if hasattr(self, "containers"):
            super().__init__(*self.containers)
        else:
            super().__init__()

        margin = 80
        self.position = pygame.Vector2(
            random.uniform(margin, SCREEN_WIDTH  - margin),
            random.uniform(margin, SCREEN_HEIGHT - margin),
        )
        self.radius = XP_STAR_RADIUS
        self._age   = 0.0
        self._spin  = random.uniform(0, 360)

    def update(self, dt):
        self._age  += dt
        self._spin += 60 * dt
        if self._age >= XP_STAR_LIFETIME:
            self.kill()

    def draw(self, screen):
        POP_DUR = 0.3
        if self._age < POP_DUR:
            t     = self._age / POP_DUR
            scale = 1.0 + 0.25 * math.sin(math.pi * t) - 0.05 * math.sin(2 * math.pi * t)
        else:
            scale = 1.0
        outer = max(1, int(self.radius * scale))
        inner = max(1, int(self.radius * 0.42 * scale))
        cx, cy = int(self.position.x), int(self.position.y)
        pts = []
        for i in range(10):
            angle = math.radians(self._spin + i * 36 - 90)
            r     = outer if i % 2 == 0 else inner
            pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
        pulse = (math.sin(self._age * 4) + 1) / 2
        b     = int(200 + pulse * 55)
        pygame.draw.polygon(screen, (b, b, b), pts)
        pygame.draw.polygon(screen, (255, 255, 255), pts, 1)
