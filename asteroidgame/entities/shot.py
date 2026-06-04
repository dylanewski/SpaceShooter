import pygame
from .circleshape import CircleShape
from ..constants import SHOT_RADIUS, SHOT_SPEED, LINE_WIDTH


class Shot(CircleShape):
    def __init__(self, x, y, direction, radius=SHOT_RADIUS):
        super().__init__(x, y, radius)
        self.velocity = direction * SHOT_SPEED
        self.damage       = 0  # 0 = use default shot_damage from game state
        self.bounces_left = 0  # remaining ricochet bounces
        self.fragment     = False  # fragments don't ricochet or explode

    def draw(self, screen):
        pygame.draw.circle(screen, "white", (int(self.position.x), int(self.position.y)), self.radius)

    def update(self, dt: float) -> None:
        self.position += self.velocity * dt
