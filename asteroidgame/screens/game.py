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
from ..entities.enemy import Enemy, ENEMY_SPAWN_RATE_START, ENEMY_SPAWN_RATE_MIN
from ..entities.fireblob import FireBlob
from ..entities.particle import Particle
from ..entities.player import Player
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
    _spawn_explosion(e.position.x, e.position.y, e.radius)
    for _ in range(5):
        XPOrb(e.position.x, e.position.y)
    e.kill()
    return 1


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

    SHIELD_R         = PLAYER_RADIUS + 10
    shield_surf_size = SHIELD_R * 2 + 6
    shield_surf      = pygame.Surface((shield_surf_size, shield_surf_size), pygame.SRCALPHA)
    shield_center    = (shield_surf_size // 2, shield_surf_size // 2)

    PULSE_RADIUS   = 220
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

    Asteroid.containers      = (updatable, drawable, asteroids)
    Enemy.containers         = (updatable, drawable, enemies)
    Player.containers        = (updatable, drawable)
    AsteroidField.containers = (updatable,)
    Shot.containers          = (updatable, drawable, shots)
    XPOrb.containers         = (updatable, drawable, xp_orbs)
    Particle.containers      = (updatable, particles)
    FireBlob.containers      = (updatable, fire_blobs)
    Vortex.containers        = (updatable, vortexes)

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
    xp_to_next       = 12
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

    vortex_stacks   = 0
    vortex_cooldown = 15.0
    vortex_timer    = 0.0

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
        nonlocal afterburn_stacks
        nonlocal vortex_stacks, vortex_cooldown
        if name == "Rapid Fire":
            player.shot_cooldown_time *= 0.9
        elif name == "Power Shot":
            shot_damage += 5
        elif name == "Shield":
            shield_stacks += 1
            shield_recharge_time = 30.0 * (0.7 ** (shield_stacks - 1))
            shield_active = True
            shield_age    = 0.0
        elif name == "XP Generator":
            xp_multiplier *= 1.1
        elif name == "Larger Artillery":
            player.shot_radius = int(player.shot_radius * 1.3)
        elif name == "Speed Boost":
            player.speed *= 1.2
        elif name == "Quick Regen":
            life_regen_time *= 2 / 3
        elif name == "Pulse Wave":
            pulse_stacks += 1
            pulse_cooldown = max(2.0, 5.0 - (pulse_stacks - 1) * 0.5)
        elif name == "Afterburn":
            afterburn_stacks += 1
        elif name == "Vortex Field":
            vortex_stacks += 1
            vortex_cooldown = max(10.0, 15.0 - (vortex_stacks - 1) * 5)

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
            asteroid_field.spawn_rate = (ASTEROID_SPAWN_RATE_SECONDS * 4 +
                (ASTEROID_SPAWN_RATE_SECONDS / 2 - ASTEROID_SPAWN_RATE_SECONDS * 4) * _t)
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
                    if afterburn_timer >= 0.12:
                        afterburn_timer = 0.0
                        FireBlob(player.position.x, player.position.y, afterburn_stacks * level)
                else:
                    afterburn_timer = 0.0

            # vortex auto-fire + pull + damage
            if vortex_stacks > 0:
                vortex_timer += dt
                if vortex_timer >= vortex_cooldown:
                    vortex_timer = 0.0
                    Vortex(player.position.x, player.position.y,
                           pygame.Vector2(0, 1).rotate(player.rotation), level)

            for v in list(vortexes):
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

            # fire blob damage
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

            for u in updatable:
                u.update(dt)

            # shot → asteroid collisions
            for a in list(asteroids):
                for s in list(shots):
                    if a.alive() and s.alive() and a.collides_with(s):
                        log_event("asteroid_shot")
                        s.kill()
                        if a.take_damage(shot_damage):
                            score += _kill_asteroid(a)
                        else:
                            _spawn_hit_effect(a.position.x, a.position.y)

            # shot → enemy collisions
            for e in list(enemies):
                for s in list(shots):
                    if e.alive() and s.alive() and e.collides_with(s):
                        shot_vel = pygame.Vector2(s.velocity)
                        s.kill()
                        if e.take_damage(shot_damage):
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
                    Enemy(edge.x, edge.y)

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
        for v in vortexes:
            v.draw(game_surf)
        for blob in fire_blobs:
            blob.draw(game_surf)
        for p in particles:
            p.draw(game_surf)
        for d in drawable:
            d.draw(game_surf)

        if shield_active:
            alpha = int(abs(math.sin(shield_age * 3)) * 255)
            shield_surf.fill((0, 0, 0, 0))
            pygame.draw.circle(shield_surf, (100, 150, 255, alpha), shield_center, SHIELD_R, 3)
            game_surf.blit(shield_surf, shield_surf.get_rect(center=(int(player.position.x), int(player.position.y))))

        if pulse_visual_age < 1.0:
            pulse_visual_age += dt / 0.5
            t     = min(1.0, pulse_visual_age)
            alpha = int(220 * (1 - t))
            pulse_surf.fill((0, 0, 0, 0))
            pygame.draw.circle(pulse_surf, (100, 180, 255, alpha),
                               (int(player.position.x), int(player.position.y)), int(PULSE_RADIUS * t), 4)
            game_surf.blit(pulse_surf, (0, 0))

        game_surf.blit(font.render(f"Score: {score}", True, "white"), (10, 10))
        draw_xp_bar(game_surf, font, cx, level, xp, xp_to_next)
        draw_lives(game_surf, lives, life_regen_timer / life_regen_time)

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
            chosen = upgrade.run(screen, clock, font, big_font, screen.copy())
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
                if a.collides_with(player) and player.invincibility_timer <= 0:
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
