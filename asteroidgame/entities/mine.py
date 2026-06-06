import pygame
from .circleshape import CircleShape

MINE_RADIUS   = 12
MINE_LIFETIME = 10.0


class Mine(CircleShape):
    containers = ()

    def __init__(self, x, y, damage):
        super().__init__(x, y, MINE_RADIUS)
        self.velocity = pygame.Vector2(0, 0)
        self.damage   = damage
        self.lifetime = MINE_LIFETIME
        self._age     = 0.0

    def update(self, dt):
        self._age     += dt
        self.lifetime -= dt

    def draw(self, screen):
        pos   = (int(self.position.x), int(self.position.y))
        warn  = self.lifetime < 3.0
        blink = warn and int(self._age * (6 if self.lifetime < 1.5 else 3)) % 2 == 0
        ring  = (255, 80, 80) if blink else ((200, 60, 60) if warn else (160, 50, 50))
        pygame.draw.circle(screen, (25, 25, 25), pos, MINE_RADIUS)
        pygame.draw.circle(screen, ring,          pos, MINE_RADIUS, 2)
        pygame.draw.circle(screen, (220, 80, 80), pos, 4)
        pygame.draw.circle(screen, ring,          pos, MINE_RADIUS - 4, 1)
