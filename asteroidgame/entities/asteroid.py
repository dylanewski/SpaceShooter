import pygame
import random
from ..logger import log_event
from .circleshape import CircleShape
from ..constants import ASTEROID_MIN_RADIUS, ASTEROID_HITBOX_SCALE

_base_images = []


def _get_base_images():
    if not _base_images:
        for i in range(1, 5):
            _base_images.append(pygame.image.load(f"assets/images/game/asteroid_{i}.png").convert_alpha())
    return _base_images


class Asteroid(CircleShape):
    def __init__(self, x: float, y: float, radius: float) -> None:
        super().__init__(x, y, radius * ASTEROID_HITBOX_SCALE)
        self._full_radius = radius
        base = random.choice(_get_base_images())
        target = radius * 2
        scale = target / max(base.get_width(), base.get_height())
        self._image = pygame.transform.scale(base, (int(base.get_width() * scale), int(base.get_height() * scale)))
        self._angle = random.uniform(0, 360)
        self._rotation_speed = random.uniform(-50, 50)
        self.health = 10

    def draw(self, screen):
        rotated = pygame.transform.rotate(self._image, self._angle)
        screen.blit(rotated, rotated.get_rect(center=(int(self.position.x), int(self.position.y))))

    def update(self, dt: float) -> None:
        self.position += self.velocity * dt
        self._angle += self._rotation_speed * dt

    def take_damage(self, amount: int) -> bool:
        self.health -= amount
        return self.health <= 0

    def split(self) -> list["Asteroid"]:
        if self._full_radius <= ASTEROID_MIN_RADIUS:
            self.kill()
            return []

        log_event("asteroid_split")
        angle = random.uniform(20, 50)
        velocity1 = self.velocity.rotate(angle)
        velocity2 = self.velocity.rotate(-angle)
        new_radius = self._full_radius - ASTEROID_MIN_RADIUS

        direction1 = velocity1.normalize() if velocity1.length() else pygame.Vector2(1, 0)
        direction2 = velocity2.normalize() if velocity2.length() else pygame.Vector2(1, 0)
        position1 = self.position + direction1 * self._full_radius
        position2 = self.position + direction2 * self._full_radius

        asteroid1 = Asteroid(position1.x, position1.y, new_radius)
        asteroid2 = Asteroid(position2.x, position2.y, new_radius)
        asteroid1.velocity = velocity1 * 1.2
        asteroid2.velocity = velocity2 * 1.2

        self.kill()
        return [asteroid1, asteroid2]
