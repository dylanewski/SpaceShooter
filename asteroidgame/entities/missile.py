import pygame

MISSILE_SPEED     = 240
MISSILE_TURN      = 300  # degrees/sec
MISSILE_RADIUS    = 6
MISSILE_LIFETIME  = 9.0


class Missile(pygame.sprite.Sprite):
    containers: tuple

    def __init__(self, x, y, target, launch_dir=None, boost_time=0.0):
        if hasattr(self, "containers"):
            super().__init__(*self.containers)
        else:
            super().__init__()

        self.position    = pygame.Vector2(x, y)
        self.target      = target
        self.radius      = MISSILE_RADIUS
        self._age        = 0.0
        self._boost_time = boost_time

        if launch_dir is not None:
            self.velocity = launch_dir.normalize() * MISSILE_SPEED
        else:
            direction = target.position - self.position
            if direction.length() == 0:
                direction = pygame.Vector2(0, -1)
            self.velocity = direction.normalize() * MISSILE_SPEED

    def update(self, dt):
        self._age += dt
        if self._age > MISSILE_LIFETIME:
            self.kill()
            return
        if self._age > self._boost_time and self.target.alive():
            to_target = self.target.position - self.position
            if to_target.length() > 0 and self.velocity.length() > 0:
                max_turn  = MISSILE_TURN * dt
                turn      = max(-max_turn, min(max_turn, self.velocity.angle_to(to_target)))
                self.velocity = self.velocity.rotate(turn).normalize() * MISSILE_SPEED
        self.position += self.velocity * dt

    def draw(self, screen):
        t     = min(1.0, self._age * 4)
        color = (255, int(180 - 80 * t), int(40 - 40 * t))
        pygame.draw.circle(screen, color, (int(self.position.x), int(self.position.y)), self.radius)
        pygame.draw.circle(screen, (255, 255, 200), (int(self.position.x), int(self.position.y)), max(1, self.radius - 3))
