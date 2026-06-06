import random
import pygame
from .circleshape import CircleShape
from ..constants import SCREEN_WIDTH, SCREEN_HEIGHT

SHOOTER_RADIUS      = 22
SHOOTER_SPEED       = 85
SHOOTER_MAX_HEALTH  = 35
SHOOTER_MOVE_TIME   = 2.0
SHOOTER_AIM_TIME    = 0.4   # pause before firing
SHOOTER_SHOT_SPEED  = 110

_STATE_MOVING = "moving"
_STATE_FIRING = "firing"


class Shooter(CircleShape):
    containers = ()

    def __init__(self, x, y, player):
        super().__init__(x, y, SHOOTER_RADIUS)
        self._full_radius   = SHOOTER_RADIUS
        self._player        = player
        self.health         = SHOOTER_MAX_HEALTH
        self.crit_flash_timer = 0.0
        self._state         = _STATE_MOVING
        self._move_timer    = random.uniform(0.5, SHOOTER_MOVE_TIME)
        self._aim_timer     = 0.0
        self.velocity       = self._dir_to_random_interior()

    def _dir_to_random_interior(self):
        PAD = 80
        tx = random.uniform(PAD, SCREEN_WIDTH  - PAD)
        ty = random.uniform(PAD, SCREEN_HEIGHT - PAD)
        d  = pygame.Vector2(tx - self.position.x, ty - self.position.y)
        return (d.normalize() if d.length() > 0 else pygame.Vector2(0, 1)) * SHOOTER_SPEED

    def take_damage(self, amount: int) -> bool:
        self.health -= amount
        return self.health <= 0

    def _launch(self):
        from .boss_shot import BossShot
        if self._player.alive():
            d = self._player.position - self.position
            shot = BossShot(self.position.x, self.position.y, d)
            shot.velocity = (d.normalize() * SHOOTER_SHOT_SPEED
                             if d.length() > 0 else pygame.Vector2(0, 1) * SHOOTER_SHOT_SPEED)

    def draw(self, screen):
        pos = (int(self.position.x), int(self.position.y))
        if self.crit_flash_timer > 0:
            pygame.draw.circle(screen, (255, 255, 255), pos, SHOOTER_RADIUS)
            return
        firing   = self._state == _STATE_FIRING
        body_col = (240, 90, 30)  if firing else (210, 150, 40)
        ring_col = (160, 50, 10)  if firing else (140, 100, 20)
        pygame.draw.circle(screen, body_col, pos, SHOOTER_RADIUS)
        pygame.draw.circle(screen, ring_col, pos, SHOOTER_RADIUS, 3)
        pygame.draw.circle(screen, (255, 220, 100), pos, SHOOTER_RADIUS // 3)

    def update(self, dt: float) -> None:
        self.crit_flash_timer = max(0.0, self.crit_flash_timer - dt)

        if self._state == _STATE_MOVING:
            self._move_timer += dt
            self.position    += self.velocity * dt
            if self._move_timer >= SHOOTER_MOVE_TIME:
                self._state      = _STATE_FIRING
                self._aim_timer  = SHOOTER_AIM_TIME
                self.velocity    = pygame.Vector2(0, 0)
        else:
            self._aim_timer -= dt
            if self._aim_timer <= 0:
                self._launch()
                self._state      = _STATE_MOVING
                self._move_timer = 0.0
                self.velocity    = self._dir_to_random_interior()

        KILL_MARGIN = 300
        if (self.position.x < -KILL_MARGIN or self.position.x > SCREEN_WIDTH + KILL_MARGIN or
                self.position.y < -KILL_MARGIN or self.position.y > SCREEN_HEIGHT + KILL_MARGIN):
            self.kill()
