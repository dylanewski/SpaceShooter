import random
import pygame


class Particle(pygame.sprite.Sprite):
    containers: tuple

    def __init__(self, x, y, base_velocity, *,
                 color=(255, 200, 80),
                 lifetime_range=(0.2, 0.45),
                 radius_range=(1.5, 3.0)):
        if hasattr(self, "containers"):
            super().__init__(*self.containers)
        else:
            super().__init__()

        self.position = pygame.Vector2(x, y)
        spread = pygame.Vector2(random.uniform(-40, 40), random.uniform(-40, 40))
        self.velocity = base_velocity * 0.4 + spread
        self.max_lifetime = random.uniform(*lifetime_range)
        self.lifetime = self.max_lifetime
        self.radius = random.uniform(*radius_range)
        self.color = color

    def draw(self, screen):
        t = self.lifetime / self.max_lifetime
        r = max(1, int(self.radius * t))
        c = (int(self.color[0] * t), int(self.color[1] * t), int(self.color[2] * t))
        pygame.draw.circle(screen, c, (int(self.position.x), int(self.position.y)), r)

    def update(self, dt):
        self.lifetime -= dt
        if self.lifetime <= 0:
            self.kill()
            return
        self.velocity *= max(0.0, 1.0 - dt * 4)
        self.position += self.velocity * dt
