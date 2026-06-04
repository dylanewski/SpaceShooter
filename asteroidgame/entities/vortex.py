import math
import pygame

VORTEX_LIFETIME    = 10.0
VORTEX_TRAVEL_TIME = 2.0
VORTEX_TRAVEL_SPEED = 340
VORTEX_PULL_RADIUS = 200


class Vortex(pygame.sprite.Sprite):
    containers: tuple

    def __init__(self, x, y, direction, level):
        if hasattr(self, "containers"):
            super().__init__(*self.containers)
        else:
            super().__init__()

        self.position          = pygame.Vector2(x, y)
        self.velocity          = direction * VORTEX_TRAVEL_SPEED
        self.lifetime          = VORTEX_LIFETIME
        self.pull_radius       = VORTEX_PULL_RADIUS
        self.damage_per_second = float(level)
        self.damage_timer      = 0.0
        self._angle            = 0.0

    @property
    def is_vortexing(self):
        return self.lifetime <= VORTEX_LIFETIME - VORTEX_TRAVEL_TIME

    def update(self, dt):
        self.lifetime  -= dt
        self._angle    += 150 * dt
        if not self.is_vortexing:
            self.position += self.velocity * dt
        else:
            self.damage_timer += dt
        if self.lifetime <= 0:
            self.kill()

    def draw(self, screen):
        t  = max(0.0, self.lifetime / VORTEX_LIFETIME)
        cx = int(self.position.x)
        cy = int(self.position.y)

        if not self.is_vortexing:
            pygame.draw.circle(screen, (140, 80, 220), (cx, cy), 10, 2)
            dot_a = math.radians(self._angle * 4)
            pygame.draw.circle(screen, (200, 140, 255),
                               (int(cx + math.cos(dot_a) * 10),
                                int(cy + math.sin(dot_a) * 10)), 3)
        else:
            for ring_r, speed_mult, color in [
                (int(VORTEX_PULL_RADIUS * 0.92),          1, (80,  40, 140)),
                (int(VORTEX_PULL_RADIUS * 0.55 * t + 18), 2, (140,  80, 220)),
                (int(VORTEX_PULL_RADIUS * 0.28 * t + 8),  4, (200, 140, 255)),
            ]:
                if ring_r < 2:
                    continue
                pygame.draw.circle(screen, color, (cx, cy), ring_r, 1)
                dot_a = math.radians(self._angle * speed_mult)
                pygame.draw.circle(screen, color,
                                   (int(cx + math.cos(dot_a) * ring_r),
                                    int(cy + math.sin(dot_a) * ring_r)), 3)
