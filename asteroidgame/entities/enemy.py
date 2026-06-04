import glob
import random
import pygame
from .circleshape import CircleShape
from ..constants import SCREEN_WIDTH, SCREEN_HEIGHT

ENEMY_RADIUS           = 110
ENEMY_HITBOX_RADIUS    = 55
ENEMY_SPEED            = 22
ENEMY_MAX_HEALTH       = 50
ENEMY_SPAWN_RATE_START = 15.0
ENEMY_SPAWN_RATE_MIN   = 2.0
ENEMY_SPAWN_RATE_STEP  = 0.4

_base_images = []


def _get_base_images():
    if not _base_images:
        paths = sorted(glob.glob("assets/images/game/junk_*.png"))
        for path in paths:
            _base_images.append(pygame.image.load(path).convert_alpha())
    return _base_images


class Enemy(CircleShape):
    def __init__(self, x, y):
        super().__init__(x, y, ENEMY_HITBOX_RADIUS)
        self._full_radius = ENEMY_RADIUS
        base = random.choice(_get_base_images())
        target = ENEMY_RADIUS * 2
        scale = target / max(base.get_width(), base.get_height())
        self._image = pygame.transform.scale(base, (int(base.get_width() * scale), int(base.get_height() * scale)))
        self._angle = random.uniform(0, 360)
        self._rotation_speed = random.uniform(-25, 25)
        angle = random.uniform(0, 360)
        self.velocity = pygame.Vector2(0, 1).rotate(angle) * random.uniform(ENEMY_SPEED * 0.7, ENEMY_SPEED * 1.3)
        self.health = ENEMY_MAX_HEALTH
        self._wander_timer = random.uniform(2.0, 5.0)

    def draw(self, screen):
        rotated = pygame.transform.rotate(self._image, self._angle)
        screen.blit(rotated, rotated.get_rect(center=(int(self.position.x), int(self.position.y))))

    def take_damage(self, amount: int) -> bool:
        self.health -= amount
        return self.health <= 0

    def update(self, dt: float) -> None:
        self._angle += self._rotation_speed * dt
        self._wander_timer -= dt
        if self._wander_timer <= 0:
            self._wander_timer = random.uniform(2.0, 5.0)
            angle = random.uniform(0, 360)
            self.velocity = pygame.Vector2(0, 1).rotate(angle) * random.uniform(ENEMY_SPEED * 0.7, ENEMY_SPEED * 1.3)

        self.position += self.velocity * dt

        if self.position.x < -self.radius:
            self.position.x = SCREEN_WIDTH + self.radius
        elif self.position.x > SCREEN_WIDTH + self.radius:
            self.position.x = -self.radius
        if self.position.y < -self.radius:
            self.position.y = SCREEN_HEIGHT + self.radius
        elif self.position.y > SCREEN_HEIGHT + self.radius:
            self.position.y = -self.radius
