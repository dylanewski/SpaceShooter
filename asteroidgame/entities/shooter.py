import math
import random
import pygame
from .circleshape import CircleShape
from ..constants import SCREEN_WIDTH, SCREEN_HEIGHT, SHOOTER_SHOT_DAMAGE

SHOOTER_RADIUS     = 22
SHOOTER_SPEED      = 85
SHOOTER_MAX_HEALTH = 35
SHOOTER_MOVE_TIME  = 2.0
SHOOTER_SHOT_SPEED = 420
SHOOTER_TURN_SPEED = 150   # degrees per second

ALIGN_THRESHOLD = 6.0   # degrees: must be this close to player before lock starts
LOCK_REQUIRED   = 1.0   # seconds of continuous alignment before firing

_IMAGE_SIZE = 86        # scaled to max dimension in pixels (~20% larger)

_STATE_MOVING = "moving"
_STATE_FIRING = "firing"

_image_cache   = None   # cleared each import so new PNG / size changes take effect
_muzzle_offset = 32     # fallback; overwritten when image loads


def _load_image():
    global _image_cache, _muzzle_offset
    if _image_cache is None:
        raw   = pygame.image.load("assets/images/game/Shooter.png").convert_alpha()
        scale = _IMAGE_SIZE / max(raw.get_width(), raw.get_height())
        w     = int(raw.get_width()  * scale)
        h     = int(raw.get_height() * scale)
        _image_cache   = pygame.transform.scale(raw, (w, h))
        _muzzle_offset = int(h * 0.38)  # laser eye sits slightly above the bottom edge
    return _image_cache


def _shortest_turn(current, target):
    diff = (target - current) % 360
    if diff > 180:
        diff -= 360
    return diff


class Shooter(CircleShape):
    containers = ()

    def __init__(self, x, y, player):
        super().__init__(x, y, SHOOTER_RADIUS)
        self._full_radius     = SHOOTER_RADIUS
        self._player          = player
        self.health           = SHOOTER_MAX_HEALTH
        self.crit_flash_timer = 0.0
        self._state           = _STATE_MOVING
        self._move_timer      = random.uniform(0.5, SHOOTER_MOVE_TIME)
        self._lock_timer      = 0.0
        self.velocity         = self._dir_to_random_interior()
        self.rotation         = self._vec_to_angle(self.velocity)
        self._laser_surf      = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)

    # -----------------------------------------------------------------------

    def _dir_to_random_interior(self):
        PAD = 80
        tx  = random.uniform(PAD, SCREEN_WIDTH  - PAD)
        ty  = random.uniform(PAD, SCREEN_HEIGHT - PAD)
        d   = pygame.Vector2(tx - self.position.x, ty - self.position.y)
        return (d.normalize() if d.length() > 0 else pygame.Vector2(0, 1)) * SHOOTER_SPEED

    def _vec_to_angle(self, v):
        """Direction vector → rotation angle where 0 = south (matches image)."""
        if v.length_squared() == 0:
            return self.rotation
        return math.degrees(math.atan2(v.x, v.y))

    def _rotate_toward(self, target_angle, dt):
        delta = _shortest_turn(self.rotation, target_angle)
        step  = min(abs(delta), SHOOTER_TURN_SPEED * dt)
        self.rotation += math.copysign(step, delta)

    def _muzzle(self):
        """World position of the laser eye (bottom center of sprite)."""
        return self.position + pygame.Vector2(0, 1).rotate(-self.rotation) * _muzzle_offset

    def take_damage(self, amount: int) -> bool:
        self.health -= amount
        return self.health <= 0

    def _launch(self):
        from .boss_shot import BossShot, BOSS_SHOT_RADIUS
        if self._player.alive():
            muzzle = self._muzzle()
            d      = self._player.position - muzzle
            shot   = BossShot(muzzle.x, muzzle.y, d)
            shot.radius   = max(3, BOSS_SHOT_RADIUS // 2)
            shot.damage   = SHOOTER_SHOT_DAMAGE
            shot.velocity = (d.normalize() * SHOOTER_SHOT_SPEED
                             if d.length() > 0 else pygame.Vector2(0, 1) * SHOOTER_SHOT_SPEED)

    # -----------------------------------------------------------------------

    def draw(self, screen):
        pos = (int(self.position.x), int(self.position.y))

        # sniper laser — only once muzzle is roughly facing player; follows muzzle rotation exactly
        if self._state == _STATE_FIRING and self._player.alive():
            d_to_player  = self._player.position - self.position
            angle_to_player = self._vec_to_angle(d_to_player)
            angle_off    = abs(_shortest_turn(self.rotation, angle_to_player))
            if angle_off <= 45.0:
                progress = self._lock_timer / LOCK_REQUIRED
                muzzle   = self._muzzle()
                d_muzzle = self._player.position - muzzle
                tip      = muzzle + (d_muzzle.normalize() * 2000 if d_muzzle.length() > 0 else pygame.Vector2(0, 2000))
                self._laser_surf.fill((0, 0, 0, 0))
                pygame.draw.line(self._laser_surf,
                                 (255, 60, 60, 40 + int(progress * 40)),
                                 (int(muzzle.x), int(muzzle.y)),
                                 (int(tip.x),    int(tip.y)), 5)
                pygame.draw.line(self._laser_surf,
                                 (255, 210, 210, 80 + int(progress * 140)),
                                 (int(muzzle.x), int(muzzle.y)),
                                 (int(tip.x),    int(tip.y)), 1)
                screen.blit(self._laser_surf, (0, 0))

        if self.crit_flash_timer > 0:
            pygame.draw.circle(screen, (255, 255, 255), pos, SHOOTER_RADIUS)
            return

        # image: PNG faces south (laser eye at bottom) → rotate by +self.rotation
        rotated = pygame.transform.rotate(_load_image(), self.rotation)
        screen.blit(rotated, rotated.get_rect(center=pos))

    # -----------------------------------------------------------------------

    def update(self, dt: float) -> None:
        self.crit_flash_timer = max(0.0, self.crit_flash_timer - dt)

        if self._state == _STATE_MOVING:
            self._move_timer += dt
            self.position    += self.velocity * dt
            if self.velocity.length_squared() > 0:
                self._rotate_toward(self._vec_to_angle(self.velocity), dt)
            if self._move_timer >= SHOOTER_MOVE_TIME:
                self._state      = _STATE_FIRING
                self._lock_timer = 0.0
                self.velocity    = pygame.Vector2(0, 0)

        else:  # _STATE_FIRING
            if self._player.alive():
                d            = self._player.position - self.position
                target_angle = self._vec_to_angle(d)
                self._rotate_toward(target_angle, dt)
                aligned = abs(_shortest_turn(self.rotation, target_angle)) <= ALIGN_THRESHOLD
                self._lock_timer = (self._lock_timer + dt) if aligned else 0.0

            if self._lock_timer >= LOCK_REQUIRED:
                self._launch()
                self._state      = _STATE_MOVING
                self._move_timer = 0.0
                self._lock_timer = 0.0
                self.velocity    = self._dir_to_random_interior()

        KILL_MARGIN = 300
        if (self.position.x < -KILL_MARGIN or self.position.x > SCREEN_WIDTH + KILL_MARGIN or
                self.position.y < -KILL_MARGIN or self.position.y > SCREEN_HEIGHT + KILL_MARGIN):
            self.kill()
