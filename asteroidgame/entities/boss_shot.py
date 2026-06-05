import math
import random
import pygame
from .circleshape import CircleShape
from ..constants import SCREEN_WIDTH, SCREEN_HEIGHT

BOSS_SHOT_SPEED  = 210
BOSS_SHOT_RADIUS = 14


class BossShot(CircleShape):
    containers: tuple

    def __init__(self, x, y, direction):
        super().__init__(x, y, BOSS_SHOT_RADIUS)
        self.velocity = direction.normalize() * BOSS_SHOT_SPEED if direction.length() > 0 \
                        else pygame.Vector2(0, 1) * BOSS_SHOT_SPEED
        self._age = 0.0

    def draw(self, screen):
        pulse = math.sin(self._age * 10) * 2
        r     = max(3, int(self.radius + pulse))
        cx, cy = int(self.position.x), int(self.position.y)
        pygame.draw.circle(screen, (180, 0,   0),   (cx, cy), r)
        pygame.draw.circle(screen, (255, 50,  50),  (cx, cy), max(1, r - 5), 2)

    def update(self, dt):
        self._age      += dt
        self.position  += self.velocity * dt
        margin = 100
        if (self.position.x < -margin or self.position.x > SCREEN_WIDTH  + margin or
                self.position.y < -margin or self.position.y > SCREEN_HEIGHT + margin):
            self.kill()
