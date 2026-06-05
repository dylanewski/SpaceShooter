import pygame

FIRE_BLOB_RADIUS   = 14
FIRE_BLOB_LIFETIME = 5.0


class FireBlob(pygame.sprite.Sprite):
    containers: tuple

    def __init__(self, x, y, damage_per_second, lifetime=FIRE_BLOB_LIFETIME):
        if hasattr(self, "containers"):
            super().__init__(*self.containers)
        else:
            super().__init__()

        self.position          = pygame.Vector2(x, y)
        self.radius            = FIRE_BLOB_RADIUS
        self.lifetime          = lifetime
        self._max_lifetime     = lifetime
        self.damage_per_second = damage_per_second

    def draw(self, screen):
        t = max(0.0, self.lifetime / self._max_lifetime)
        r = max(1, int(self.radius * t))
        color = (255, int(110 * t + 10), 0)
        pygame.draw.circle(screen, color, (int(self.position.x), int(self.position.y)), r)

    def update(self, dt):
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.kill()
