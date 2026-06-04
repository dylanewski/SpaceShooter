import math
import random
import pygame
from .circleshape import CircleShape
from .constants import SHOT_RADIUS, SHOT_SPEED

_base_images = []


def _get_base_images():
    if not _base_images:
        for i in range(1, 3):
            _base_images.append(pygame.image.load(f"assets/images/game/shot_{i}.png").convert_alpha())
    return _base_images


class Shot(CircleShape):
    def __init__(self, x, y, direction):
        super().__init__(x, y, SHOT_RADIUS)
        self.direction = direction
        self.velocity = direction * SHOT_SPEED

        base = random.choice(_get_base_images())
        target = SHOT_RADIUS * 2
        scale = target / max(base.get_width(), base.get_height())
        self._image = pygame.transform.scale(base, (int(base.get_width() * scale), int(base.get_height() * scale)))
        self._angle = math.degrees(math.atan2(direction.x, -direction.y))

    def draw(self, screen):
        rotated = pygame.transform.rotate(self._image, self._angle)
        screen.blit(rotated, rotated.get_rect(center=(int(self.position.x), int(self.position.y))))

    def update(self, dt: float) -> None:
        self.position += self.velocity * dt
