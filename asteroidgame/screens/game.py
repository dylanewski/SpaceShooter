import math
import random
import pygame

from ..constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    ASTEROID_SPAWN_RATE_SECONDS,
    PLAYER_RADIUS,
    XP_ORB_PICKUP_RADIUS,
    MAX_LIVES, LIFE_REGEN_TIME, INVINCIBILITY_TIME,
)
from ..logger import log_state, log_event
from ..ui import make_button, draw_button, draw_xp_bar, draw_lives

from ..entities.asteroid import Asteroid
from ..entities.asteroidfield import AsteroidField
from ..entities.enemy import Enemy, ENEMY_SPAWN_RATE_START, ENEMY_SPAWN_RATE_MIN, ENEMY_MAX_HEALTH
from ..entities.fireblob import FireBlob
from ..entities.particle import Particle
from ..entities.player import Player
from ..entities.missile import Missile
from ..entities.shot import Shot
from ..entities.vortex import Vortex, VORTEX_PULL_RADIUS
from ..entities.xporb import XPOrb

from . import upgrade


# ---------------------------------------------------------------------------
# Module-level effect helpers (called from run(); containers set before use)
# ---------------------------------------------------------------------------

def _spawn_explosion(x, y, radius):
    count = max(6, int(radius / 3))
    for _ in range(count):
        angle = random.uniform(0, 360)
        speed = random.uniform(80, 180 + radius * 2)
        vel   = pygame.Vector2(0, 1).rotate(angle) * speed / 0.4
        Particle(x, y, vel,
                 color=(200, 190, 170),
                 lifetime_range=(0.3, 0.7),
                 radius_range=(1.0, min(4.0, radius / 8)))


def _spawn_hit_effect(x, y, shot_vel=None):
    base = math.degrees(math.atan2(shot_vel.x, -shot_vel.y)) if shot_vel else 0
    for _ in range(14):
        a     = base + random.uniform(-70, 70) if shot_vel else random.uniform(0, 360)
        speed = random.uniform(180, 400)
        vel   = pygame.Vector2(0, 1).rotate(a) * speed / 0.4
        Particle(x, y, vel,
                 color=(255, 230, 130),
                 lifetime_range=(0.25, 0.55),
                 radius_range=(2.0, 5.0))


def _kill_asteroid(a) -> int:
    pos = pygame.Vector2(a.position)
    _spawn_explosion(pos.x, pos.y, a._full_radius)
    XPOrb(pos.x, pos.y)
    a.split()
    return 1


def _kill_enemy(e) -> int:
    _spawn_explosion(e.position.x, e.position.y, e._full_radius)
    for _ in range(5):
        XPOrb(e.position.x, e.position.y)
    e.kill()
    return 1


def _ray_hits(origin, direction, center, radius):
    """True if a ray from origin in direction intersects a circle."""
    v = center - origin
    t = v.dot(direction)
    return t > 0 and v.length_squared() - t * t < radius * radius


# ---------------------------------------------------------------------------
# Game screen
# ---------------------------------------------------------------------------

def run(screen, clock, font, big_font) -> tuple[str, int]:
    cx, cy = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2

    # --- surfaces ---
    game_surf     = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    pause_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    pause_overlay.fill((0, 0, 0, 160))
    pulse_surf    = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    laser_surf    = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    danger_surf   = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    exp_surf      = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    danger_font   = pygame.font.Font("assets/fonts/Symtext.ttf", 80)

    _skull_raw   = pygame.image.load("assets/images/game/Skull Ui.png").convert_alpha()
    _skull_size  = 34
    skull_image  = pygame.transform.scale(_skull_raw, (_skull_size, _skull_size))

    SHIELD_R         = PLAYER_RADIUS + 10
    shield_surf_size = SHIELD_R * 2 + 6
    shield_surf      = pygame.Surface((shield_surf_size, shield_surf_size), pygame.SRCALPHA)
    shield_center    = (shield_surf_size // 2, shield_surf_size // 2)

    PULSE_RADIUS   = 150
    SHAKE_DURATION = 0.3
    SHAKE_INTENSITY = 8

    # --- pause buttons ---
    resume_btn     = make_button((cx, cy - 20))
    end_game_btn   = make_button((cx, cy + 60))
    pause_home_btn = make_button((cx, cy + 140))

    # --- sprite groups ---
    updatable  = pygame.sprite.Group()
    drawable   = pygame.sprite.Group()
    particles  = pygame.sprite.Group()
    asteroids  = pygame.sprite.Group()
    enemies    = pygame.sprite.Group()
    shots      = pygame.sprite.Group()
    xp_orbs    = pygame.sprite.Group()
    fire_blobs = pygame.sprite.Group()
    vortexes   = pygame.sprite.Group()
    missiles   = pygame.sprite.Group()

    Asteroid.containers      = (updatable, drawable, asteroids)
    Enemy.containers         = (updatable, drawable, enemies)
    Player.containers        = (updatable, drawable)
    AsteroidField.containers = (updatable,)
    Shot.containers          = (updatable, drawable, shots)
    XPOrb.containers         = (updatable, drawable, xp_orbs)
    Particle.containers      = (updatable, particles)
    FireBlob.containers      = (updatable, fire_blobs)
    Vortex.containers        = (updatable, vortexes)
    Missile.containers       = (updatable, missiles)

    asteroid_field = AsteroidField()
    player         = Player(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)

    # --- game state ---
    score        = 0
    score_timer  = 0.0
    dt           = 0.0
    paused       = False
    game_time    = 0.0
    shake_timer  = 0.0

    xp               = 0
    level            = 1
    xp_to_next       = 7
    level_up_pending = False

    lives            = MAX_LIVES
    life_regen_time  = LIFE_REGEN_TIME
    life_regen_timer = 0.0

    # --- upgrade state ---
    shot_damage  = 10
    xp_multiplier = 1.0

    shield_stacks         = 0
    shield_active         = False
    shield_age            = 0.0
    shield_recharge_time  = 30.0
    shield_recharge_timer = 0.0

    pulse_stacks     = 0
    pulse_cooldown   = 5.0
    pulse_timer      = 0.0
    pulse_visual_age = 1.0

    afterburn_stacks = 0
    afterburn_timer  = 0.0

    homing_strength   = 0
    ricochet_stacks   = 0
    explosive_stacks   = 0
    explosion_visuals  = []   # list of [x, y, max_r, age]
    RICOCHET_RANGE    = 200
    EXPLOSION_RADIUS  = 80

    plow_stacks            = 0
    plow_cooldown          = 2.0
    plow_timer             = 0.0
    plow_invincibility_timer = 0.0
    plow_image             = None

    BUDDY_DISTANCE = 65
    buddy_stacks = 0
    buddy_image  = None

    vortex_stacks   = 0
    vortex_cooldown = 15.0
    vortex_timer    = 0.0

    missile_stacks        = 1
    missile_cooldown      = 6.0
    missile_timer         = 0.0
    missile_queue         = []
    missile_launch_timer  = 0.0

    laser_stacks     = 0
    laser_cooldown   = 8.0
    laser_timer      = 0.0
    laser_visual_age = 1.0
    laser_origin     = None
    laser_direction  = None

    # --- spawn state ---
    particle_timer    = 0.0
    enemy_spawn_rate  = ENEMY_SPAWN_RATE_START
    enemy_spawn_timer = 0.0

    # --- nested helpers ---

    def award_xp(amount=1):
        nonlocal xp, level, xp_to_next, level_up_pending
        xp += max(1, int(amount * xp_multiplier))
        if xp >= xp_to_next:
            xp -= xp_to_next
            level += 1
            xp_to_next = int(xp_to_next * 1.2)
            level_up_pending = True

    def apply_upgrade(name):
        nonlocal shot_damage, xp_multiplier, life_regen_time
        nonlocal shield_stacks, shield_active, shield_age, shield_recharge_time
        nonlocal pulse_stacks, pulse_cooldown
        nonlocal afterburn_stacks, homing_strength, ricochet_stacks, explosive_stacks
        nonlocal plow_stacks, plow_cooldown, plow_image
        nonlocal buddy_stacks, buddy_image
        nonlocal missile_stacks, missile_cooldown
        nonlocal laser_stacks, laser_cooldown, laser_visual_age, laser_origin, laser_direction
        nonlocal vortex_stacks, vortex_cooldown
        if name == "Rapid Fire":
            player.shot_cooldown_time *= 0.9
        elif name == "Higher Caliber Rounds":
            shot_damage += 6
        elif name == "Shield":
            shield_stacks += 1
            shield_recharge_time = 30.0 * (0.7 ** (shield_stacks - 1))
            shield_active = True
            shield_age    = 0.0
        elif name == "XP Generator":
            xp_multiplier *= 1.1
        elif name == "Bigger Bullets":
            player.shot_radius = int(player.shot_radius * 1.3)
        elif name == "Speed Boost":
            player.speed *= 1.2
        elif name == "Quick Regen":
            life_regen_time *= 0.75
        elif name == "Pulse Wave":
            pulse_stacks += 1
            pulse_cooldown = max(2.0, 5.0 - (pulse_stacks - 1) * 0.5)
        elif name == "Afterburn":
            afterburn_stacks += 1
        elif name == "Homing Shots":
            homing_strength += 1
        elif name == "Ricochet":
            ricochet_stacks += 1
        elif name == "Explosive Rounds":
            explosive_stacks += 1
        elif name == "Plow":
            plow_stacks   += 1
            plow_cooldown *= 0.9
            if plow_image is None:
                raw = pygame.image.load("assets/images/game/plow.png").convert_alpha()
                target = PLAYER_RADIUS * 2
                scale  = target / max(raw.get_width(), raw.get_height())
                plow_image = pygame.transform.scale(raw, (int(raw.get_width() * scale), int(raw.get_height() * scale)))
        elif name == "Little Buddy":
            buddy_stacks += 1
            if buddy_image is None:
                raw    = pygame.image.load("assets/images/game/lilbuddy.png").convert_alpha()
                target = PLAYER_RADIUS * 2 * 0.65
                scale  = target / max(raw.get_width(), raw.get_height())
                buddy_image = pygame.transform.scale(raw, (int(raw.get_width() * scale), int(raw.get_height() * scale)))
        elif name == "Vortex Field":
            vortex_stacks += 1
            vortex_cooldown = max(10.0, 15.0 - (vortex_stacks - 1) * 5)
        elif name == "Missile Salvo":
            missile_stacks += 1
        elif name == "Laser Beam":
            laser_stacks += 1
            laser_cooldown = max(4.0, 6.4 - (laser_stacks - 1) * 0.5)

    # -----------------------------------------------------------------------
    # Main loop
    # -----------------------------------------------------------------------
    while True:
        log_state()

        # --- events ---
        pause_action = None
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit", score
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                paused = not paused
            if paused and event.type == pygame.MOUSEBUTTONDOWN:
                if resume_btn.collidepoint(event.pos):
                    paused = False
                elif end_game_btn.collidepoint(event.pos):
                    pause_action = "quit"
                elif pause_home_btn.collidepoint(event.pos):
                    pause_action = "home"

        if pause_action:
            return pause_action, score

        game_surf.fill("black")

        # --- update (skipped while paused) ---
        if not paused:
            dt        = clock.tick(60) / 1000
            game_time += dt

            # time-based spawn rate ramp (0 → max over 300 s)
            _t = min(1.0, game_time / 300.0)
            asteroid_field.spawn_rate = (ASTEROID_SPAWN_RATE_SECONDS * 8 +
                (ASTEROID_SPAWN_RATE_SECONDS / 2 - ASTEROID_SPAWN_RATE_SECONDS * 8) * _t)
            enemy_spawn_rate = ENEMY_SPAWN_RATE_START + (ENEMY_SPAWN_RATE_MIN - ENEMY_SPAWN_RATE_START) * _t

            # score ticks up every second
            score_timer += dt
            if score_timer >= 1.0:
                score_timer -= 1.0
                score += 1

            # life regen
            if lives < MAX_LIVES:
                life_regen_timer += dt
                if life_regen_timer >= life_regen_time:
                    lives += 1
                    life_regen_timer = 0.0

            # shield age / recharge
            if shield_active:
                shield_age += dt
            elif shield_stacks > 0:
                shield_recharge_timer += dt
                if shield_recharge_timer >= shield_recharge_time:
                    shield_active = True
                    shield_age    = 0.0
                    shield_recharge_timer = 0.0

            # engine particle trail
            particle_timer += dt
            if particle_timer >= 0.03:
                particle_timer = 0.0
                backward = pygame.Vector2(0, 1).rotate(player.rotation + 180)
                exhaust  = player.position + backward * (PLAYER_RADIUS * 0.5)
                Particle(exhaust.x, exhaust.y, backward * player.speed)

            # pulse wave
            if pulse_stacks > 0:
                pulse_timer += dt
                if pulse_timer >= pulse_cooldown:
                    pulse_timer      = 0.0
                    pulse_visual_age = 0.0
                    dmg = max(10, 3 * level)
                    for a in list(asteroids):
                        if a.alive() and a.position.distance_to(player.position) <= PULSE_RADIUS:
                            if a.take_damage(dmg):
                                score += _kill_asteroid(a)
                    for e in list(enemies):
                        if e.alive() and e.position.distance_to(player.position) <= PULSE_RADIUS:
                            if e.take_damage(dmg):
                                score += _kill_enemy(e)

            # afterburn fire trail
            if afterburn_stacks > 0:
                if player.is_thrusting and player.velocity.length() >= player.speed * 0.9:
                    afterburn_timer += dt
                    spawn_interval = 0.12 / (1.0 + (afterburn_stacks - 1) * 0.3)
                    if afterburn_timer >= spawn_interval and len(fire_blobs) < afterburn_stacks * 8:
                        afterburn_timer = 0.0
                        blob_lifetime   = 5.0 * (1.0 + (afterburn_stacks - 1) * 0.5)
                        FireBlob(player.position.x, player.position.y, max(5, afterburn_stacks * level), blob_lifetime)
                else:
                    afterburn_timer = 0.0

            # vortex auto-fire + pull + damage
            if vortex_stacks > 0:
                vortex_timer += dt
                if vortex_timer >= vortex_cooldown and pygame.key.get_pressed()[pygame.K_SPACE]:
                    vortex_timer = 0.0
                    Vortex(player.position.x, player.position.y,
                           pygame.Vector2(0, 1).rotate(player.rotation), max(5, level))

            for v in list(vortexes):
                if not v.is_vortexing:
                    TRAVEL_HIT_R = 18
                    for a in list(asteroids):
                        if a.alive() and v.position.distance_to(a.position) < a.radius + TRAVEL_HIT_R:
                            v.anchor()
                            break
                    if not v.is_vortexing:
                        for e in list(enemies):
                            if e.alive() and v.position.distance_to(e.position) < e.radius + TRAVEL_HIT_R:
                                v.anchor()
                                break
                if not v.is_vortexing:
                    continue
                for a in list(asteroids):
                    if a.alive():
                        dist = a.position.distance_to(v.position)
                        if 0 < dist < v.pull_radius:
                            a.velocity += (v.position - a.position).normalize() * (1 - dist / v.pull_radius) * 280 * dt
                for e in list(enemies):
                    if e.alive():
                        dist = e.position.distance_to(v.position)
                        if 0 < dist < v.pull_radius:
                            e.velocity += (v.position - e.position).normalize() * (1 - dist / v.pull_radius) * 280 * dt
                if v.damage_timer >= 1.0:
                    v.damage_timer -= 1.0
                    vdmg = int(v.damage_per_second)
                    for a in list(asteroids):
                        if a.alive() and a.position.distance_to(v.position) < v.pull_radius:
                            if a.take_damage(vdmg):
                                score += _kill_asteroid(a)
                    for e in list(enemies):
                        if e.alive() and e.position.distance_to(v.position) < v.pull_radius:
                            if e.take_damage(vdmg):
                                score += _kill_enemy(e)

            if missile_stacks > 0:
                missile_timer += dt
                if missile_timer >= missile_cooldown and pygame.key.get_pressed()[pygame.K_SPACE]:
                    missile_timer  = 0.0
                    missile_count  = missile_stacks * 3
                    targets = sorted(
                        [t for t in list(asteroids) + list(enemies) if t.alive()],
                        key=lambda t: t.position.distance_to(player.position)
                    )
                    wing = pygame.Vector2(0, 1).rotate(player.rotation + 90)
                    side = random.choice([-1, 1])
                    missile_queue.clear()
                    for i in range(missile_count):
                        if targets:
                            missile_queue.append((side, targets[i % len(targets)]))
                            side = -side
                    missile_launch_timer = 0.0

            if missile_queue:
                missile_launch_timer -= dt
                if missile_launch_timer <= 0:
                    ms, tgt = missile_queue.pop(0)
                    if tgt.alive():
                        forward = pygame.Vector2(0, 1).rotate(player.rotation)
                        wing    = pygame.Vector2(0, 1).rotate(player.rotation + 90)
                        spawn   = player.position + wing * (ms * 18)
                        Missile(spawn.x, spawn.y, tgt, launch_dir=forward, boost_time=0.4)
                    missile_launch_timer = 0.1

            for m in list(missiles):
                for a in list(asteroids):
                    if m.alive() and a.alive() and m.position.distance_to(a.position) < m.radius + a.radius:
                        missile_dmg = max(7, (max(20, 4 * level) + (missile_stacks - 1) * 5) // 3)
                        if a.take_damage(missile_dmg):
                            score += _kill_asteroid(a)
                        _spawn_explosion(m.position.x, m.position.y, 15)
                        m.kill()
                        break
                for e in list(enemies):
                    if m.alive() and e.alive() and m.position.distance_to(e.position) < m.radius + e.radius:
                        missile_dmg = max(7, (max(20, 4 * level) + (missile_stacks - 1) * 5) // 3)
                        if e.take_damage(missile_dmg):
                            score += _kill_enemy(e)
                        _spawn_explosion(m.position.x, m.position.y, 15)
                        m.kill()
                        break

            if laser_stacks > 0:
                laser_timer += dt
                if laser_timer >= laser_cooldown and pygame.key.get_pressed()[pygame.K_SPACE]:
                    laser_timer      = 0.0
                    laser_visual_age = 0.0
                    laser_origin     = pygame.Vector2(player.position)
                    laser_direction  = pygame.Vector2(0, 1).rotate(player.rotation).normalize()
                    laser_dmg        = max(25, 3 * level)
                    for a in list(asteroids):
                        if a.alive() and _ray_hits(laser_origin, laser_direction, a.position, a.radius):
                            if a.take_damage(laser_dmg):
                                score += _kill_asteroid(a)
                            else:
                                _spawn_hit_effect(a.position.x, a.position.y)
                    for e in list(enemies):
                        if e.alive() and _ray_hits(laser_origin, laser_direction, e.position, e.radius):
                            if e.take_damage(laser_dmg):
                                score += _kill_enemy(e)
                            else:
                                _spawn_hit_effect(e.position.x, e.position.y)

            for blob in list(fire_blobs):
                if blob.damage_timer >= 1.0:
                    blob.damage_timer -= 1.0
                    bdmg = int(blob.damage_per_second)
                    for a in list(asteroids):
                        if blob.alive() and a.alive() and blob.position.distance_to(a.position) < blob.radius + a.radius:
                            if a.take_damage(bdmg):
                                score += _kill_asteroid(a)
                    for e in list(enemies):
                        if blob.alive() and e.alive() and blob.position.distance_to(e.position) < blob.radius + e.radius:
                            if e.take_damage(bdmg):
                                score += _kill_enemy(e)

            plow_timer             = min(plow_cooldown, plow_timer + dt)
            plow_invincibility_timer = max(0.0, plow_invincibility_timer - dt)

            if plow_stacks > 0 and plow_timer >= plow_cooldown:
                forward  = pygame.Vector2(0, 1).rotate(player.rotation)
                nose     = player.position + forward * (PLAYER_RADIUS * 0.9)
                PLOW_R   = 30
                plow_dmg = max(35, plow_stacks * 5 * level)
                plow_hit = False
                for a in list(asteroids):
                    if a.alive() and not plow_hit and nose.distance_to(a.position) < PLOW_R + a.radius:
                        plow_timer = 0.0
                        plow_hit   = True
                        plow_invincibility_timer = 0.5
                        if a.take_damage(plow_dmg):
                            score += _kill_asteroid(a)
                        else:
                            _spawn_hit_effect(nose.x, nose.y)
                for e in list(enemies):
                    if e.alive() and not plow_hit and nose.distance_to(e.position) < PLOW_R + e.radius:
                        plow_timer = 0.0
                        plow_hit   = True
                        plow_invincibility_timer = 0.5
                        if e.take_damage(plow_dmg):
                            score += _kill_enemy(e)
                        else:
                            _spawn_hit_effect(nose.x, nose.y)

            shots_before_update = set(shots)

            if buddy_stacks > 0 and player.just_fired:
                buddy_dmg = max(1, int(shot_damage * (0.5 + (buddy_stacks - 1) * 0.07)))
                bpos      = player.position + pygame.Vector2(0, 1).rotate(player.rotation + 90) * BUDDY_DISTANCE
                s         = Shot(bpos.x, bpos.y, pygame.Vector2(0, 1).rotate(player.rotation), player.shot_radius)
                s.damage  = buddy_dmg

            if homing_strength > 0:
                TURN_SPEED   = homing_strength * 15
                HOMING_RANGE = 380
                for s in shots:
                    if s.velocity.length() == 0:
                        continue
                    nearest, nearest_dist = None, float('inf')
                    for target in list(asteroids) + list(enemies):
                        if target.alive():
                            d = s.position.distance_to(target.position)
                            if d < nearest_dist:
                                nearest_dist, nearest = d, target
                    if nearest and nearest_dist < HOMING_RANGE:
                        to_target = nearest.position - s.position
                        if to_target.length() > 0:
                            max_turn = TURN_SPEED * dt
                            turn     = max(-max_turn, min(max_turn, s.velocity.angle_to(to_target)))
                            s.velocity = s.velocity.rotate(turn).normalize() * s.velocity.length()

            for u in updatable:
                u.update(dt)

            if ricochet_stacks > 0 and player.just_fired:
                for s in shots:
                    if s not in shots_before_update:
                        s.bounces_left = ricochet_stacks

            # shot → asteroid collisions
            for a in list(asteroids):
                for s in list(shots):
                    if a.alive() and s.alive() and a.collides_with(s):
                        log_event("asteroid_shot")
                        dmg = s.damage or shot_damage
                        if explosive_stacks > 0 and not s.fragment:
                            exp_r = EXPLOSION_RADIUS + (explosive_stacks - 1) * 20
                            splash = max(5, shot_damage // 3) * explosive_stacks
                            _spawn_explosion(s.position.x, s.position.y, exp_r // 2)
                            explosion_visuals.append([s.position.x, s.position.y, exp_r, 0.0])
                            for ta in list(asteroids):
                                if ta.alive() and ta is not a and ta.position.distance_to(s.position) < exp_r:
                                    if ta.take_damage(splash):
                                        score += _kill_asteroid(ta)
                            for te in list(enemies):
                                if te.alive() and te.position.distance_to(s.position) < exp_r:
                                    if te.take_damage(splash):
                                        score += _kill_enemy(te)
                        if s.bounces_left > 0:
                            s.bounces_left -= 1
                            other = [t for t in list(asteroids) + list(enemies) if t.alive() and t is not a]
                            if other:
                                nearest = min(other, key=lambda t: t.position.distance_to(s.position))
                                if nearest.position.distance_to(s.position) < RICOCHET_RANGE:
                                    s.velocity = (nearest.position - s.position).normalize() * s.velocity.length()
                                else:
                                    s.kill()
                            else:
                                s.kill()
                        else:
                            s.kill()
                        if a.take_damage(dmg):
                            score += _kill_asteroid(a)
                        else:
                            _spawn_hit_effect(a.position.x, a.position.y)

            # shot → enemy collisions
            for e in list(enemies):
                for s in list(shots):
                    if e.alive() and s.alive() and e.collides_with(s):
                        shot_vel = pygame.Vector2(s.velocity)
                        dmg      = s.damage or shot_damage
                        if explosive_stacks > 0 and not s.fragment:
                            exp_r = EXPLOSION_RADIUS + (explosive_stacks - 1) * 20
                            splash = max(5, shot_damage // 3) * explosive_stacks
                            _spawn_explosion(s.position.x, s.position.y, exp_r // 2)
                            explosion_visuals.append([s.position.x, s.position.y, exp_r, 0.0])
                            for ta in list(asteroids):
                                if ta.alive() and ta.position.distance_to(s.position) < exp_r:
                                    if ta.take_damage(splash):
                                        score += _kill_asteroid(ta)
                            for te in list(enemies):
                                if te.alive() and te is not e and te.position.distance_to(s.position) < exp_r:
                                    if te.take_damage(splash):
                                        score += _kill_enemy(te)
                        if s.bounces_left > 0:
                            s.bounces_left -= 1
                            other = [t for t in list(asteroids) + list(enemies) if t.alive() and t is not e]
                            if other:
                                nearest = min(other, key=lambda t: t.position.distance_to(s.position))
                                if nearest.position.distance_to(s.position) < RICOCHET_RANGE:
                                    s.velocity = (nearest.position - s.position).normalize() * s.velocity.length()
                                else:
                                    s.kill()
                            else:
                                s.kill()
                        else:
                            s.kill()
                        if e.take_damage(dmg):
                            score += _kill_enemy(e)
                        else:
                            _spawn_hit_effect(e.position.x, e.position.y, shot_vel)

            # shield intercepts asteroids
            if shield_active:
                for a in list(asteroids):
                    if a.alive() and a.position.distance_to(player.position) < SHIELD_R + a._full_radius:
                        _spawn_explosion(a.position.x, a.position.y, a._full_radius)
                        XPOrb(a.position.x, a.position.y)
                        a.kill()
                        shield_active         = False
                        shield_age            = 0.0
                        shield_recharge_timer = 0.0
                        break

            # enemy spawn
            if level >= 2:
                enemy_spawn_timer += dt
                if enemy_spawn_timer >= enemy_spawn_rate:
                    enemy_spawn_timer = 0.0
                    margin = 30
                    edge = random.choice([
                        pygame.Vector2(-margin,              random.uniform(0, 1) * SCREEN_HEIGHT),
                        pygame.Vector2(SCREEN_WIDTH + margin, random.uniform(0, 1) * SCREEN_HEIGHT),
                        pygame.Vector2(random.uniform(0, 1) * SCREEN_WIDTH, -margin),
                        pygame.Vector2(random.uniform(0, 1) * SCREEN_WIDTH, SCREEN_HEIGHT + margin),
                    ])
                    e = Enemy(edge.x, edge.y)
                    e.health = int(ENEMY_MAX_HEALTH * (1.0 + int(game_time // 60) * 0.10))
                    toward_center = (pygame.Vector2(cx, cy) - edge).normalize()
                    e.velocity = toward_center * e.velocity.length()

            # xp orb attraction + collection
            for orb in list(xp_orbs):
                dist = orb.position.distance_to(player.position)
                if dist < XP_ORB_PICKUP_RADIUS and dist > 0:
                    orb.velocity = (player.position - orb.position).normalize() * (100 + (1 - dist / XP_ORB_PICKUP_RADIUS) * 400)
                if dist < player.radius + orb.radius:
                    orb.kill()
                    award_xp()

        else:
            clock.tick(60)

        # --- draw ---
        for m in missiles:
            m.draw(game_surf)
        for v in vortexes:
            v.draw(game_surf)
        for blob in fire_blobs:
            blob.draw(game_surf)
        for p in particles:
            p.draw(game_surf)
        for d in drawable:
            d.draw(game_surf)

        if plow_stacks > 0 and plow_image is not None:
            forward      = pygame.Vector2(0, 1).rotate(player.rotation)
            nose         = player.position + forward * (PLAYER_RADIUS * 0.9)
            rotated_plow = pygame.transform.rotate(plow_image, -player.rotation + 180)
            if plow_timer < plow_cooldown:
                mask = pygame.Surface(rotated_plow.get_size(), pygame.SRCALPHA)
                mask.fill((255, 255, 255, 80))
                rotated_plow.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
            game_surf.blit(rotated_plow, rotated_plow.get_rect(center=(int(nose.x), int(nose.y))))

        if buddy_stacks > 0 and buddy_image is not None:
            bpos          = player.position + pygame.Vector2(0, 1).rotate(player.rotation + 90) * BUDDY_DISTANCE
            rotated_buddy = pygame.transform.rotate(buddy_image, -player.rotation + 180)
            game_surf.blit(rotated_buddy, rotated_buddy.get_rect(center=(int(bpos.x), int(bpos.y))))

        if shield_active:
            alpha = int(abs(math.sin(shield_age * 3)) * 255)
            shield_surf.fill((0, 0, 0, 0))
            pygame.draw.circle(shield_surf, (100, 150, 255, alpha), shield_center, SHIELD_R, 3)
            game_surf.blit(shield_surf, shield_surf.get_rect(center=(int(player.position.x), int(player.position.y))))

        next_exp = []
        for ev in explosion_visuals:
            ev[3] += dt
            if ev[3] < 0.35:
                next_exp.append(ev)
                t     = ev[3] / 0.35
                r     = max(1, int(ev[2] * t))
                alpha = int(230 * (1 - t))
                exp_surf.fill((0, 0, 0, 0))
                pygame.draw.circle(exp_surf, (255, 130, 0, alpha),          (int(ev[0]), int(ev[1])), r, 4)
                pygame.draw.circle(exp_surf, (255, 230, 80, min(255, alpha + 50)), (int(ev[0]), int(ev[1])), max(1, r - 5), 2)
                game_surf.blit(exp_surf, (0, 0))
        explosion_visuals[:] = next_exp

        if pulse_visual_age < 1.0:
            pulse_visual_age += dt / 0.5
            t     = min(1.0, pulse_visual_age)
            alpha = int(220 * (1 - t))
            pulse_surf.fill((0, 0, 0, 0))
            pygame.draw.circle(pulse_surf, (100, 180, 255, alpha),
                               (int(player.position.x), int(player.position.y)), int(PULSE_RADIUS * t), 4)
            game_surf.blit(pulse_surf, (0, 0))

        if laser_visual_age < 1.0 and laser_origin is not None:
            laser_visual_age += dt / 0.25
            t     = min(1.0, laser_visual_age)
            alpha = int(220 * (1 - t))
            end   = laser_origin + laser_direction * 2000
            beam_w = 2 + laser_stacks * 2
            core_w = laser_stacks
            laser_surf.fill((0, 0, 0, 0))
            pygame.draw.line(laser_surf, (180, 220, 255, alpha),
                             (int(laser_origin.x), int(laser_origin.y)),
                             (int(end.x), int(end.y)), beam_w)
            pygame.draw.line(laser_surf, (255, 255, 255, min(255, alpha + 60)),
                             (int(laser_origin.x), int(laser_origin.y)),
                             (int(end.x), int(end.y)), core_w)
            game_surf.blit(laser_surf, (0, 0))

        if lives == 1:
            pulse = (math.sin(game_time * 2.5) + 1) / 2
            bw    = 22
            da    = int(40 + pulse * 130)
            danger_surf.fill((0, 0, 0, 0))
            pygame.draw.rect(danger_surf, (220, 0, 0, da), (0, 0, SCREEN_WIDTH, bw))
            pygame.draw.rect(danger_surf, (220, 0, 0, da), (0, SCREEN_HEIGHT - bw, SCREEN_WIDTH, bw))
            pygame.draw.rect(danger_surf, (220, 0, 0, da), (0, 0, bw, SCREEN_HEIGHT))
            pygame.draw.rect(danger_surf, (220, 0, 0, da), (SCREEN_WIDTH - bw, 0, bw, SCREEN_HEIGHT))
            game_surf.blit(danger_surf, (0, 0))
            if int(game_time * 2) % 2 == 0:
                dtxt = danger_font.render("DANGER", True, (220, 0, 0))
                game_surf.blit(dtxt, dtxt.get_rect(center=(cx, SCREEN_HEIGHT // 2)))

        game_surf.blit(font.render(f"{score}", True, "white"), (10, 10))
        draw_xp_bar(game_surf, font, cx, level, xp, xp_to_next)
        draw_lives(game_surf, lives, life_regen_timer / life_regen_time)

        bar_w     = 14
        bar_x     = SCREEN_WIDTH - 22
        bar_top   = int(SCREEN_HEIGHT * 0.2)
        bar_h     = int((SCREEN_HEIGHT - 30) * 0.7)
        bar_bot   = bar_top + bar_h
        fill_frac = min(1.0, game_time / 300.0)
        fill_h    = int(bar_h * fill_frac)
        skull_x = bar_x + bar_w // 2 - skull_image.get_width() // 2
        skull_y = bar_top - skull_image.get_height() - 2
        game_surf.blit(skull_image, (skull_x, skull_y))
        pygame.draw.rect(game_surf, (45, 45, 45),    (bar_x, bar_top, bar_w, bar_h))
        pygame.draw.rect(game_surf, (255, 255, 255), (bar_x, bar_bot - fill_h, bar_w, fill_h))
        pygame.draw.rect(game_surf, (120, 120, 120), (bar_x, bar_top, bar_w, bar_h), 1)

        # screen shake composite
        if shake_timer > 0:
            shake_timer = max(0.0, shake_timer - dt)
            intensity   = int(SHAKE_INTENSITY * shake_timer / SHAKE_DURATION)
            ox, oy      = random.randint(-intensity, intensity), random.randint(-intensity, intensity)
        else:
            ox, oy = 0, 0
        screen.fill("black")
        screen.blit(game_surf, (ox, oy))

        if level_up_pending:
            level_up_pending = False
            chosen = upgrade.run(screen, clock, font, screen.copy())
            if chosen == "quit":
                return "quit", score
            apply_upgrade(chosen)

        if paused:
            screen.blit(pause_overlay, (0, 0))
            screen.blit(big_font.render("PAUSED", True, "white"),
                        big_font.render("PAUSED", True, "white").get_rect(center=(cx, cy - 100)))
            draw_button(screen, font, resume_btn,     "Resume")
            draw_button(screen, font, end_game_btn,   "End Game")
            draw_button(screen, font, pause_home_btn, "Home")

        pygame.display.flip()

        # --- player collision (after flip so last frame is visible) ---
        if not paused:
            for a in list(asteroids) + list(enemies):
                if a.collides_with(player) and player.invincibility_timer <= 0 and plow_invincibility_timer <= 0:
                    log_event("player_hit")
                    if shield_active:
                        shield_active         = False
                        shield_age            = 0.0
                        shield_recharge_timer = 0.0
                    else:
                        lives            -= 1
                        life_regen_timer  = 0.0
                        shake_timer       = SHAKE_DURATION
                        if lives <= 0:
                            return "game_over", score
                        player.invincibility_timer = INVINCIBILITY_TIME
                    break
