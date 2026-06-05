import math
import random
import pygame
from .circleshape import CircleShape
from ..constants import XP_ORB_LIFETIME

BIG_XP_ORB_RADIUS = 9
BIG_XP_VALUE      = 20


class BigXPOrb(CircleShape):
    containers: tuple

    def __init__(self, x, y):
        super().__init__(x, y, BIG_XP_ORB_RADIUS)
        angle = random.uniform(0, 360)
        self.velocity = pygame.Vector2(0, 1).rotate(angle) * random.uniform(30, 80)
        self._age = 0.0

    def draw(self, screen):
        pulse = math.sin(self._age * 6) * 2.5
        r     = max(2, int(self.radius + pulse))
        cx, cy = int(self.position.x), int(self.position.y)
        pygame.draw.circle(screen, (255, 190, 40),  (cx, cy), r)
        pygame.draw.circle(screen, (255, 240, 140), (cx, cy), max(1, r - 3), 2)

    def update(self, dt):
        self._age += dt
        if self._age >= XP_ORB_LIFETIME:
            self.kill()
            return
        self.velocity *= max(0.0, 1.0 - dt * 2.5)
        self.position += self.velocity * dt
