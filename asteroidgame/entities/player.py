import pygame
from .circleshape import CircleShape
from ..constants import *
from .shot import Shot

ANGULAR_MAX   = PLAYER_TURN_SPEED   # 300 deg/s
ANGULAR_ACCEL = 900                 # deg/s²  — reaches max in 0.33 s
ANGULAR_DECEL = 700                 # deg/s²  — coasts to stop in 0.43 s

DASH_COOLDOWN_TIME   = 3.0
DASH_INVINCIBILITY   = 1.0
DASH_SPEED_MULT      = 2.0   # base — ~1/3 the distance of 3.5; upgrades scale this
DOUBLE_TAP_WINDOW    = 0.25
TRAIL_POINT_LIFE     = 0.45   # seconds each ghost persists
TRAIL_SPAWN_INTERVAL = 0.04   # add a new ghost every 0.04 s during dash
TRAIL_ACTIVE_DUR     = 0.30   # how long to keep spawning ghost points

_DASH_DIRS = {
    pygame.K_w: pygame.Vector2(0, 1),   # forward only
}


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
        self.just_dashed      = False

        self.dash_cooldown_time  = DASH_COOLDOWN_TIME   # upgradeable
        self.dash_speed_mult     = DASH_SPEED_MULT      # upgradeable
        self.dash_cooldown       = 0.0
        self._internal_time      = 0.0
        self._last_tap_time      = {k: -999.0 for k in _DASH_DIRS}
        self._prev_keys          = {k: False  for k in _DASH_DIRS}
        self._dash_active_timer  = 0.0   # counts down while spawning trail points
        self._trail_spawn_timer  = 0.0
        self._dash_trail         = []    # [x, y, angle, life]

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
        # dash trail — oldest (darkest) first, newest (brightest) on top
        for x, y, angle, life in self._dash_trail:
            frac = life / TRAIL_POINT_LIFE          # 1.0 = just spawned, 0.0 = dying
            alpha = int(frac * 210)
            if alpha <= 0:
                continue
            ghost = pygame.transform.rotate(self._image_straight, -angle + 180).copy()
            white_add = int(frac * 200)
            ghost.fill((white_add, white_add, white_add, 0), special_flags=pygame.BLEND_RGB_ADD)
            ghost.set_alpha(alpha)
            screen.blit(ghost, ghost.get_rect(center=(int(x), int(y))))

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
        self.just_fired  = False
        self.just_dashed = False
        self.invincibility_timer = max(0.0, self.invincibility_timer - dt)
        self.shot_cooldown       = max(0.0, self.shot_cooldown - dt)
        self.dash_cooldown       = max(0.0, self.dash_cooldown - dt)
        self._internal_time     += dt
        keys = pygame.key.get_pressed()

        # --- double-tap dash detection ---
        _dashed_this_frame = False
        for key, local_dir in _DASH_DIRS.items():
            pressed_now  = bool(keys[key])
            just_pressed = pressed_now and not self._prev_keys[key]
            if just_pressed:
                if (self.dash_cooldown <= 0 and
                        self._internal_time - self._last_tap_time[key] <= DOUBLE_TAP_WINDOW):
                    dash_dir = local_dir.rotate(self.rotation)
                    self.velocity            = dash_dir * (self.speed * self.dash_speed_mult)
                    self.invincibility_timer = DASH_INVINCIBILITY
                    self.dash_cooldown       = self.dash_cooldown_time
                    self._last_tap_time[key] = -999.0
                    self._dash_active_timer  = TRAIL_ACTIVE_DUR
                    self._trail_spawn_timer  = 0.0
                    self._dash_trail.clear()
                    _dashed_this_frame       = True
                    self.just_dashed         = True
                else:
                    self._last_tap_time[key] = self._internal_time
            self._prev_keys[key] = pressed_now

        # --- dash trail spawning ---
        if self._dash_active_timer > 0:
            self._dash_active_timer -= dt
            self._trail_spawn_timer -= dt
            if self._trail_spawn_timer <= 0:
                self._trail_spawn_timer = TRAIL_SPAWN_INTERVAL
                self._dash_trail.append([self.position.x, self.position.y,
                                         self.rotation, TRAIL_POINT_LIFE])
        for entry in self._dash_trail:
            entry[3] -= dt
        self._dash_trail = [e for e in self._dash_trail if e[3] > 0]

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

        if _dashed_this_frame:
            self.is_thrusting = bool(keys[pygame.K_w])
        elif keys[pygame.K_w]:
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
        # During the dash burst window let velocity exceed normal max
        burst_active = self.dash_cooldown > self.dash_cooldown_time - 0.5
        max_speed    = self.speed * self.dash_speed_mult if burst_active else self.speed
        if self.velocity.length() > max_speed:
            self.velocity = self.velocity.normalize() * max_speed

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
