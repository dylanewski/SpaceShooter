import glob
import random
import pygame
from .circleshape import CircleShape
from ..constants import SCREEN_WIDTH, SCREEN_HEIGHT

ENEMY_RADIUS           = 110
ENEMY_HITBOX_RADIUS    = 55
ENEMY_SPEED            = 22
ENEMY_MAX_HEALTH       = 70
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
        self.health           = ENEMY_MAX_HEALTH
        self._wander_timer    = random.uniform(2.0, 5.0)
        self.crit_flash_timer = 0.0

    def draw(self, screen):
        rotated = pygame.transform.rotate(self._image, self._angle)
        rect = rotated.get_rect(center=(int(self.position.x), int(self.position.y)))
        if self.crit_flash_timer > 0:
            flash = rotated.copy()
            flash.fill((255, 255, 255, 0), special_flags=pygame.BLEND_RGB_ADD)
            screen.blit(flash, rect)
        else:
            screen.blit(rotated, rect)

    def take_damage(self, amount: int) -> bool:
        self.health -= amount
        return self.health <= 0

    def update(self, dt: float) -> None:
        self.crit_flash_timer = max(0.0, self.crit_flash_timer - dt)
        self._angle += self._rotation_speed * dt
        self._wander_timer -= dt
        if self._wander_timer <= 0:
            self._wander_timer = random.uniform(2.0, 5.0)
            # Always aim toward a random interior point so junk stays a threat
            PAD = 80
            tx  = random.uniform(PAD, SCREEN_WIDTH  - PAD)
            ty  = random.uniform(PAD, SCREEN_HEIGHT - PAD)
            d   = pygame.Vector2(tx - self.position.x, ty - self.position.y)
            direction = d.normalize() if d.length() > 0 else pygame.Vector2(0, 1)
            self.velocity = direction * random.uniform(ENEMY_SPEED * 0.7, ENEMY_SPEED * 1.3)

        self.position += self.velocity * dt

        # kill when well off-screen so junk drifts in and out cleanly (no wrap flash)
        KILL_MARGIN = 300
        if (self.position.x < -KILL_MARGIN or self.position.x > SCREEN_WIDTH + KILL_MARGIN or
                self.position.y < -KILL_MARGIN or self.position.y > SCREEN_HEIGHT + KILL_MARGIN):
            self.kill()
