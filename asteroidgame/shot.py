from .circleshape import CircleShape
from .constants import LINE_WIDTH, SHOT_RADIUS, SHOT_SPEED
import pygame


class Shot(CircleShape):
    def __init__(self, x, y, direction):
        super().__init__(x, y, SHOT_RADIUS)
        self.direction = direction
        self.velocity = direction * SHOT_SPEED

    def draw(self, screen):
        pygame.draw.circle(screen, "white", self.position, self.radius, LINE_WIDTH)

    def update(self, dt: float) -> None:
        self.position += self.velocity * dt