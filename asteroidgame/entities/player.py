import pygame
from .circleshape import CircleShape
from ..constants import *
from .shot import Shot

ANGULAR_MAX   = PLAYER_TURN_SPEED   # 300 deg/s
ANGULAR_ACCEL = 900                 # deg/s²  — reaches max in 0.33 s
ANGULAR_DECEL = 700                 # deg/s²  — coasts to stop in 0.43 s


class Player(CircleShape):
    def __init__(self, x, y):
        super().__init__(x, y, PLAYER_HITBOX_RADIUS)
        self.rotation         = 0
        self.angular_velocity = 0.0
        self.turn_dir         = 0       # -1 left, 0 straight, 1 right
        self.shot_cooldown    = 0.0
        self.shot_cooldown_time = PLAYER_SHOT_COOLDOWN_SECONDS
        self.shot_radius      = SHOT_RADIUS
        self.speed            = PLAYER_SPEED
        self.invincibility_timer = 0.0
        self.is_thrusting     = False
        self.just_fired       = False

        target = PLAYER_RADIUS * 2

        def _load(path):
            raw   = pygame.image.load(path).convert_alpha()
            scale = target / max(raw.get_width(), raw.get_height())
            return pygame.transform.scale(raw,
                (int(raw.get_width() * scale), int(raw.get_height() * scale)))

        self._image_straight = _load("assets/images/game/ship.png")
        self._image_left     = _load("assets/images/game/shipspriteturnleft.png")
        self._image_right    = _load("assets/images/game/shipspriteturnright.png")

    def draw(self, screen):
        if self.invincibility_timer > 0 and int(self.invincibility_timer * 8) % 2 == 0:
            return
        if self.turn_dir < 0:
            img = self._image_left
        elif self.turn_dir > 0:
            img = self._image_right
        else:
            img = self._image_straight
        rotated = pygame.transform.rotate(img, -self.rotation + 180)
        screen.blit(rotated, rotated.get_rect(center=(int(self.position.x), int(self.position.y))))

    def update(self, dt: float) -> None:
        self.just_fired = False
        self.invincibility_timer = max(0.0, self.invincibility_timer - dt)
        self.shot_cooldown = max(0.0, self.shot_cooldown - dt)
        keys = pygame.key.get_pressed()

        turning_left  = keys[pygame.K_a]
        turning_right = keys[pygame.K_d]

        if turning_left and not turning_right:
            self.angular_velocity -= ANGULAR_ACCEL * dt
            self.angular_velocity  = max(-ANGULAR_MAX, self.angular_velocity)
            self.turn_dir = -1
        elif turning_right and not turning_left:
            self.angular_velocity += ANGULAR_ACCEL * dt
            self.angular_velocity  = min(ANGULAR_MAX, self.angular_velocity)
            self.turn_dir = 1
        else:
            self.turn_dir = 0
            if abs(self.angular_velocity) <= ANGULAR_DECEL * dt:
                self.angular_velocity = 0.0
            elif self.angular_velocity > 0:
                self.angular_velocity -= ANGULAR_DECEL * dt
            else:
                self.angular_velocity += ANGULAR_DECEL * dt

        self.rotation += self.angular_velocity * dt

        if keys[pygame.K_w]:
            self.move(dt)
            self.is_thrusting = True
        elif keys[pygame.K_s]:
            self.move(-dt)
            self.is_thrusting = False
        else:
            self._decelerate(dt)
            self.is_thrusting = False

        if keys[pygame.K_SPACE]:
            self.shoot()

        self.position += self.velocity * dt

        r = self.radius
        if self.position.x < r:
            self.position.x = r
            self.velocity.x = max(0.0, self.velocity.x)
        elif self.position.x > SCREEN_WIDTH - r:
            self.position.x = SCREEN_WIDTH - r
            self.velocity.x = min(0.0, self.velocity.x)
        if self.position.y < r:
            self.position.y = r
            self.velocity.y = max(0.0, self.velocity.y)
        elif self.position.y > SCREEN_HEIGHT - r:
            self.position.y = SCREEN_HEIGHT - r
            self.velocity.y = min(0.0, self.velocity.y)

    def move(self, dt: float) -> None:
        direction = pygame.Vector2(0, 1).rotate(self.rotation)
        self.velocity += direction * (self.speed * 2) * dt
        if self.velocity.length() > self.speed:
            self.velocity = self.velocity.normalize() * self.speed

    def _decelerate(self, dt: float) -> None:
        decel = self.speed * 2 * dt
        if self.velocity.length() <= decel:
            self.velocity = pygame.Vector2(0, 0)
        else:
            self.velocity -= self.velocity.normalize() * decel

    def shoot(self):
        if self.shot_cooldown > 0:
            return None
        self.shot_cooldown = self.shot_cooldown_time
        self.just_fired    = True
        direction = pygame.Vector2(0, 1).rotate(self.rotation)
        shot = Shot(self.position.x, self.position.y, direction, self.shot_radius)
        shot.velocity = direction * SHOT_SPEED
        return shot
