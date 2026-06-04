import random
import pygame
from .circleshape import CircleShape
from .constants import LINE_WIDTH

ENEMY_RADIUS       = 18
ENEMY_SPEED_BASE   = 60
ENEMY_SPAWN_RATE_START = 8.0
ENEMY_SPAWN_RATE_MIN   = 2.0
ENEMY_SPAWN_RATE_STEP  = 0.4


class Enemy(CircleShape):
    def __init__(self, x, y, target_pos):
        super().__init__(x, y, ENEMY_RADIUS)
        speed = random.uniform(ENEMY_SPEED_BASE * 0.8, ENEMY_SPEED_BASE * 1.2)
        direction = target_pos - self.position
        if direction.length() > 0:
            self.velocity = direction.normalize() * speed

    def draw(self, screen):
        x, y, r = int(self.position.x), int(self.position.y), self.radius
        points = [(x, y - r), (x + r, y), (x, y + r), (x - r, y)]
        pygame.draw.polygon(screen, "white", points, LINE_WIDTH)
        half = int(r * 0.5)
        pygame.draw.line(screen, "white", (x - half, y), (x + half, y), 1)
        pygame.draw.line(screen, "white", (x, y - half), (x, y + half), 1)

    def update(self, dt):
        self.position += self.velocity * dt
