import math
import random
import pygame

from ..entities.particle import Particle
from ..entities.xporb import XPOrb


def spawn_explosion(x, y, radius):
    count = max(6, int(radius / 3))
    for _ in range(count):
        angle = random.uniform(0, 360)
        speed = random.uniform(80, 180 + radius * 2)
        vel   = pygame.Vector2(0, 1).rotate(angle) * speed / 0.4
        Particle(x, y, vel,
                 color=(200, 190, 170),
                 lifetime_range=(0.3, 0.7),
                 radius_range=(1.0, min(4.0, radius / 8)))


def spawn_hit_effect(x, y, shot_vel=None):
    base = math.degrees(math.atan2(shot_vel.x, -shot_vel.y)) if shot_vel else 0
    for _ in range(14):
        a     = base + random.uniform(-70, 70) if shot_vel else random.uniform(0, 360)
        speed = random.uniform(180, 400)
        vel   = pygame.Vector2(0, 1).rotate(a) * speed / 0.4
        Particle(x, y, vel,
                 color=(255, 230, 130),
                 lifetime_range=(0.25, 0.55),
                 radius_range=(2.0, 5.0))


def spawn_boss_explosion(x, y, radius):
    """Fiery, high-particle explosion used for boss-death cascade."""
    count  = max(30, int(radius * 1.5))
    colors = [(255, 60, 0), (255, 170, 0), (255, 100, 20), (220, 30, 0), (255, 230, 80)]
    for _ in range(count):
        angle = random.uniform(0, 360)
        speed = random.uniform(150, 500 + radius * 3)
        vel   = pygame.Vector2(0, 1).rotate(angle) * speed / 0.4
        Particle(x, y, vel,
                 color=random.choice(colors),
                 lifetime_range=(0.5, 1.6),
                 radius_range=(2.0, min(10.0, radius / 4)))


def ray_hits(origin, direction, center, radius):
    """True if a ray from origin in direction intersects a circle."""
    v = center - origin
    t = v.dot(direction)
    return t > 0 and v.length_squared() - t * t < radius * radius


def kill_centibomb(c) -> int:
    from ..entities.boss_shot import BossShot
    spawn_explosion(c.position.x, c.position.y, c._full_radius)
    for i in range(5):
        d = pygame.Vector2(0, 1).rotate(360 / 5 * i)
        BossShot(c.position.x, c.position.y, d)
    for _ in range(3):
        XPOrb(c.position.x, c.position.y)
    c.kill()
    return 1


def kill_entity(e) -> int:
    """Route to the right kill function — Centibomb explodes, Enemy does not."""
    from ..entities.centibomb import Centibomb
    if isinstance(e, Centibomb):
        return kill_centibomb(e)
    return kill_enemy(e)


_COMBO_MILESTONES = {10, 25, 50, 100, 250, 500, 1000}


def combo_kill(state, kill_fn, entity) -> int:
    result = kill_fn(entity)
    if result:
        state.combo_count += 1
        state.combo_timer  = 1.0
        if state.combo_count in _COMBO_MILESTONES:
            state.award_xp(state.combo_count)
            state.combo_shake_timer = 0.25
    return result


def kill_asteroid(a) -> int:
    pos = pygame.Vector2(a.position)
    spawn_explosion(pos.x, pos.y, a._full_radius)
    XPOrb(pos.x, pos.y)
    a.split()
    return 1


def kill_enemy(e) -> int:
    spawn_explosion(e.position.x, e.position.y, e._full_radius)
    for _ in range(5):
        XPOrb(e.position.x, e.position.y)
    e.kill()
    return 1
