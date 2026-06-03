import pygame
import random
from asteroidgame.logger import log_event
from .circleshape import CircleShape
from .constants import ASTEROID_MIN_RADIUS, LINE_WIDTH


class Asteroid(CircleShape):
    def __init__(self, x: float, y: float, radius: float) -> None:
        super().__init__(x, y, radius)

    def draw(self, screen):
        pygame.draw.circle(screen, "white", self.position, self.radius, LINE_WIDTH)

    def update(self, dt: float) -> None:
        self.position += self.velocity * dt

    def split(self) -> list["Asteroid"]:
        if self.radius <= ASTEROID_MIN_RADIUS:
            self.kill()
            return []
        
        log_event("asteroid_split")
        angle = random.uniform(20, 50)
        velocity1 = self.velocity.rotate(angle)
        velocity2 = self.velocity.rotate(-angle)
        new_radius = self.radius - ASTEROID_MIN_RADIUS

        offset_distance = self.radius
        direction1 = velocity1.normalize() if velocity1.length() else pygame.Vector2(1, 0)
        direction2 = velocity2.normalize() if velocity2.length() else pygame.Vector2(1, 0)
        position1 = self.position + direction1 * offset_distance
        position2 = self.position + direction2 * offset_distance

        asteroid1 = Asteroid(position1.x, position1.y, new_radius)
        asteroid2 = Asteroid(position2.x, position2.y, new_radius)

        asteroid1.velocity = velocity1 * 1.2
        asteroid2.velocity = velocity2 * 1.2

        self.kill()
        return [asteroid1, asteroid2]
