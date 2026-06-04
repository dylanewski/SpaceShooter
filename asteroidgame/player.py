import pygame
from .circleshape import CircleShape
from .constants import *
from .shot import Shot

class Player(CircleShape):
    def __init__(self, x, y):
        super().__init__(x, y, PLAYER_HITBOX_RADIUS)
        self.rotation = 0
        self.shot_cooldown = 0.0
        self.shot_cooldown_time = PLAYER_SHOT_COOLDOWN_SECONDS
        self.shot_radius = SHOT_RADIUS
        self.speed = PLAYER_SPEED
        self.invincibility_timer = 0.0
        raw = pygame.image.load("assets/images/game/ship.png").convert_alpha()
        target = PLAYER_RADIUS * 2
        scale = target / max(raw.get_width(), raw.get_height())
        self._image = pygame.transform.scale(raw, (int(raw.get_width() * scale), int(raw.get_height() * scale)))

    def draw(self, screen):
        if self.invincibility_timer > 0 and int(self.invincibility_timer * 8) % 2 == 0:
            return
        rotated = pygame.transform.rotate(self._image, -self.rotation + 180)
        rect = rotated.get_rect(center=(int(self.position.x), int(self.position.y)))
        screen.blit(rotated, rect)

    def rotate(self,dt):
        self.rotation += PLAYER_TURN_SPEED * dt

    def update(self, dt: float) -> None:
        self.invincibility_timer = max(0.0, self.invincibility_timer - dt)
        self.shot_cooldown = max(0.0, self.shot_cooldown - dt)
        keys = pygame.key.get_pressed()

        if keys[pygame.K_a]:
            self.rotate(-dt)
        if keys[pygame.K_d]:
            self.rotate(dt)

        if keys[pygame.K_w]:
            self.move(dt)
        elif keys[pygame.K_s]:
            self.move(-dt)
        else:
            self._decelerate(dt)

        if keys[pygame.K_SPACE]:
            self.shoot()

        self.position += self.velocity * dt

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
        direction = pygame.Vector2(0, 1).rotate(self.rotation)
        shot = Shot(self.position.x, self.position.y, direction, self.shot_radius)
        shot.velocity = direction * PLAYER_SHOT_SPEED
        return shot
        