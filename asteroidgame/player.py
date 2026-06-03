import pygame
from .circleshape import CircleShape
from .constants import *
from .shot import Shot

class Player(CircleShape):
    def __init__(self, x, y):
        super().__init__(x, y, PLAYER_RADIUS)
        self.rotation = 0
        self.shot_cooldown = 0.0
        raw = pygame.image.load("assets/images/game/ship.png").convert_alpha()
        target = PLAYER_RADIUS * 2
        scale = target / max(raw.get_width(), raw.get_height())
        self._image = pygame.transform.scale(raw, (int(raw.get_width() * scale), int(raw.get_height() * scale)))

    def draw(self, screen):
        rotated = pygame.transform.rotate(self._image, -self.rotation + 180)
        rect = rotated.get_rect(center=(int(self.position.x), int(self.position.y)))
        screen.blit(rotated, rect)

    def rotate(self,dt):
        self.rotation += PLAYER_TURN_SPEED * dt

    def update(self, dt: float) -> None:
        self.shot_cooldown = max(0.0, self.shot_cooldown - dt)
        keys = pygame.key.get_pressed()

        if keys[pygame.K_a]:
            self.rotate(-dt)
        if keys[pygame.K_d]:
            self.rotate(dt)
        if keys[pygame.K_w]:
            self.move(dt)
        if keys[pygame.K_s]:
            self.move(-dt)
        if keys[pygame.K_SPACE]:
            self.shoot()

    def move(self, dt: float) -> None:
        unit_vector = pygame.Vector2(0, 1)
        rotated_vector = unit_vector.rotate(self.rotation)
        rotated_with_speed_vector = rotated_vector * PLAYER_SPEED * dt
        self.position += rotated_with_speed_vector
    
    def shoot(self):
        if self.shot_cooldown > 0:
            return None
        self.shot_cooldown = PLAYER_SHOT_COOLDOWN_SECONDS
        direction = pygame.Vector2(0, 1).rotate(self.rotation)
        shot = Shot(self.position.x, self.position.y, direction)
        shot.velocity = direction * PLAYER_SHOT_SPEED
        return shot
        