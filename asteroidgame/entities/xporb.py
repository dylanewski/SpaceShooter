import math
import random
import pygame
from .circleshape import CircleShape
from ..constants import XP_ORB_RADIUS, XP_ORB_LIFETIME


class XPOrb(CircleShape):
    def __init__(self, x, y):
        super().__init__(x, y, XP_ORB_RADIUS)
        angle = random.uniform(0, 360)
        self.velocity = pygame.Vector2(0, 1).rotate(angle) * random.uniform(20, 50)
        self._age = 0.0

    def draw(self, screen):
        pulse = math.sin(self._age * 5) * 1.5
        r = max(1, int(self.radius + pulse))
        pygame.draw.circle(screen, "white", (int(self.position.x), int(self.position.y)), r)

    def update(self, dt):
        self._age += dt
        if self._age >= XP_ORB_LIFETIME:
            self.kill()
            return
        self.velocity *= max(0.0, 1.0 - dt * 3)
        self.position += self.velocity * dt
