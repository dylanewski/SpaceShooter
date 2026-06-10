import math
import random
import pygame
from .circleshape import CircleShape
from ..constants import SCREEN_WIDTH, SCREEN_HEIGHT, ENEMY_CONTACT_DAMAGE

DASHER_RADIUS         = 36
DASHER_SPEED          = 80
DASHER_DASH_SPEED     = 560
DASHER_MAX_HEALTH     = 35
DASHER_TRACK_TIME     = 1.4   # seconds orienting before dash
DASHER_TURN_SPEED     = 100   # degrees per second
DASHER_CONTACT_DAMAGE = 30    # only active during dash

_STATE_ENTERING = "entering"
_STATE_TRACKING = "tracking"
_STATE_DASHING  = "dashing"


def _shortest_turn(current, target):
    diff = (target - current) % 360
    if diff > 180:
        diff -= 360
    return diff


class Dasher(CircleShape):
    containers = ()

    def __init__(self, x, y, player):
        super().__init__(x, y, DASHER_RADIUS)
        self._player          = player
        self.health           = DASHER_MAX_HEALTH
        self.crit_flash_timer = 0.0
        self._full_radius     = DASHER_RADIUS
        self.contact_damage   = ENEMY_CONTACT_DAMAGE   # bumped to 30 on dash
        self._state           = _STATE_ENTERING
        self._track_timer     = 0.0
        PAD = 120
        self._target = pygame.Vector2(
            random.uniform(PAD, SCREEN_WIDTH - PAD),
            random.uniform(PAD, SCREEN_HEIGHT - PAD),
        )
        d = self._target - pygame.Vector2(x, y)
        self.velocity = (d.normalize() if d.length() > 0 else pygame.Vector2(0, 1)) * DASHER_SPEED
        self.rotation = math.degrees(math.atan2(self.velocity.x, self.velocity.y))

    def take_damage(self, amount: int) -> bool:
        self.health -= amount
        return self.health <= 0

    def draw(self, screen):
        pos = (int(self.position.x), int(self.position.y))

        if self.crit_flash_timer > 0:
            pygame.draw.circle(screen, (255, 255, 255), pos, DASHER_RADIUS)
            return

        if self._state == _STATE_DASHING:
            body_col = (255, 60, 0)
            ring_col = (255, 220, 0)
        elif self._state == _STATE_TRACKING:
            frac     = min(1.0, self._track_timer / DASHER_TRACK_TIME)
            body_col = (int(100 + frac * 155), 15, 15)
            ring_col = (255, int(80 + frac * 120), 0)
        else:
            body_col = (120, 25, 25)
            ring_col = (180, 55, 35)

        pygame.draw.circle(screen, body_col, pos, DASHER_RADIUS)
        pygame.draw.circle(screen, ring_col, pos, DASHER_RADIUS, 3)

        forward = pygame.Vector2(0, 1).rotate(-self.rotation)
        tip   = self.position + forward * (DASHER_RADIUS + 10)
        left  = self.position + pygame.Vector2(0, 1).rotate(-self.rotation + 145) * (DASHER_RADIUS * 0.55)
        right = self.position + pygame.Vector2(0, 1).rotate(-self.rotation - 145) * (DASHER_RADIUS * 0.55)
        pygame.draw.polygon(screen, ring_col, [
            (int(tip.x),   int(tip.y)),
            (int(left.x),  int(left.y)),
            (int(right.x), int(right.y)),
        ])

        if self._state == _STATE_TRACKING and self._track_timer > 0.2:
            frac = min(1.0, self._track_timer / DASHER_TRACK_TIME)
            rect = pygame.Rect(
                pos[0] - DASHER_RADIUS - 8, pos[1] - DASHER_RADIUS - 8,
                (DASHER_RADIUS + 8) * 2,   (DASHER_RADIUS + 8) * 2,
            )
            pygame.draw.arc(screen, (255, 160, 0),
                            rect, -math.pi / 2, -math.pi / 2 + 2 * math.pi * frac, 3)

    def update(self, dt: float) -> None:
        self.crit_flash_timer = max(0.0, self.crit_flash_timer - dt)
        self.position += self.velocity * dt

        if self._state == _STATE_ENTERING:
            if self.velocity.length_squared() > 0:
                self.rotation = math.degrees(math.atan2(self.velocity.x, self.velocity.y))
            if self.position.distance_to(self._target) < 55:
                self.velocity     = pygame.Vector2(0, 0)
                self._state       = _STATE_TRACKING
                self._track_timer = 0.0

        elif self._state == _STATE_TRACKING:
            self._track_timer += dt
            if self._player.alive():
                d = self._player.position - self.position
                if d.length_squared() > 0:
                    target_angle = math.degrees(math.atan2(d.x, d.y))
                    diff = _shortest_turn(self.rotation, target_angle)
                    step = min(abs(diff), DASHER_TURN_SPEED * dt)
                    self.rotation += math.copysign(step, diff)
            if self._track_timer >= DASHER_TRACK_TIME:
                self._state         = _STATE_DASHING
                self.contact_damage = DASHER_CONTACT_DAMAGE
                forward             = pygame.Vector2(0, 1).rotate(-self.rotation)
                self.velocity       = forward * DASHER_DASH_SPEED

        elif self._state == _STATE_DASHING:
            MARGIN = 200
            if (self.position.x < -MARGIN or self.position.x > SCREEN_WIDTH + MARGIN or
                    self.position.y < -MARGIN or self.position.y > SCREEN_HEIGHT + MARGIN):
                self.kill()
