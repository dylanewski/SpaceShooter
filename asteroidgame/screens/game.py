import math
import random
import pygame
from ..asteroid import Asteroid
from ..asteroidfield import AsteroidField
from ..constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    ASTEROID_SPAWN_RATE_SECONDS,
    PLAYER_RADIUS,
    XP_ORB_PICKUP_RADIUS,
    MAX_LIVES, LIFE_REGEN_TIME, INVINCIBILITY_TIME,
)
from ..logger import log_state, log_event
from ..player import Player
from ..shot import Shot
from ..ui import make_button, draw_button, draw_xp_bar, draw_lives
from ..enemy import Enemy, ENEMY_SPAWN_RATE_START, ENEMY_SPAWN_RATE_MIN, ENEMY_SPAWN_RATE_STEP
from ..particle import Particle
from ..xporb import XPOrb
from . import upgrade


def _spawn_explosion(x, y, radius):
    count = max(6, int(radius / 3))
    for _ in range(count):
        angle = random.uniform(0, 360)
        speed = random.uniform(80, 180 + radius * 2)
        vel = pygame.Vector2(0, 1).rotate(angle) * speed / 0.4
        Particle(x, y, vel,
                 color=(200, 190, 170),
                 lifetime_range=(0.3, 0.7),
                 radius_range=(1.0, min(4.0, radius / 8)))


def _apply_damage(asteroid, damage):
    children = asteroid.split()
    if damage > 1:
        for child in children:
            if child.alive():
                _apply_damage(child, damage - 1)


def run(screen, clock, font, big_font) -> tuple[str, int]:
    cx, cy = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2

    pause_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    pause_overlay.fill((0, 0, 0, 160))
    resume_btn     = make_button((cx, cy - 20))
    end_game_btn   = make_button((cx, cy + 60))
    pause_home_btn = make_button((cx, cy + 140))

    SHIELD_R = PLAYER_RADIUS + 10
    shield_surf_size = SHIELD_R * 2 + 6
    shield_surf = pygame.Surface((shield_surf_size, shield_surf_size), pygame.SRCALPHA)
    shield_surf_center = (shield_surf_size // 2, shield_surf_size // 2)

    updatable = pygame.sprite.Group()
    drawable  = pygame.sprite.Group()
    particles = pygame.sprite.Group()
    asteroids = pygame.sprite.Group()
    enemies   = pygame.sprite.Group()
    shots     = pygame.sprite.Group()
    xp_orbs   = pygame.sprite.Group()
    Asteroid.containers      = (updatable, drawable, asteroids)
    Enemy.containers         = (updatable, drawable, enemies)
    Player.containers        = (updatable, drawable)
    AsteroidField.containers = (updatable,)
    Shot.containers          = (updatable, drawable, shots)
    XPOrb.containers         = (updatable, drawable, xp_orbs)
    Particle.containers      = (updatable, particles)
    asteroid_field = AsteroidField()
    asteroid_field.spawn_rate = ASTEROID_SPAWN_RATE_SECONDS * 4
    player = Player(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)

    score        = 0
    score_timer  = 0.0
    dt           = 0.0
    paused       = False
    xp           = 0
    level        = 1
    xp_to_next   = 25
    level_up_pending = False

    enemy_spawn_rate  = ENEMY_SPAWN_RATE_START
    enemy_spawn_timer = 0.0
    lives            = MAX_LIVES
    life_regen_time  = LIFE_REGEN_TIME
    life_regen_timer = 0.0
    particle_timer  = 0.0
    shot_damage     = 1
    xp_multiplier  = 1.0
    shield_stacks  = 0
    shield_active  = False
    shield_age     = 0.0
    shield_recharge_time  = 30.0
    shield_recharge_timer = 0.0

    def award_xp(amount=1):
        nonlocal xp, level, xp_to_next, level_up_pending
        xp += max(1, int(amount * xp_multiplier))
        if xp >= xp_to_next:
            xp -= xp_to_next
            level += 1
            xp_to_next = int(xp_to_next * 1.2)
            level_up_pending = True
            asteroid_field.spawn_rate = max(
                ASTEROID_SPAWN_RATE_SECONDS / 2,
                asteroid_field.spawn_rate - 0.2,
            )
            enemy_spawn_rate = max(
                ENEMY_SPAWN_RATE_MIN,
                enemy_spawn_rate - ENEMY_SPAWN_RATE_STEP,
            )

    def apply_upgrade(name):
        nonlocal shot_damage, xp_multiplier, life_regen_time
        nonlocal shield_stacks, shield_active, shield_age, shield_recharge_time
        if name == "Rapid Fire":
            player.shot_cooldown_time *= 0.9
        elif name == "Power Shot":
            shot_damage += 1
        elif name == "Shield":
            shield_stacks += 1
            shield_recharge_time = 30.0 * (0.7 ** (shield_stacks - 1))
            shield_active = True
            shield_age = 0.0
        elif name == "XP Generator":
            xp_multiplier *= 1.1
        elif name == "Larger Artillery":
            player.shot_radius = int(player.shot_radius * 1.3)
        elif name == "Speed Boost":
            player.speed *= 1.2
        elif name == "Quick Regen":
            life_regen_time *= 2 / 3

    while True:
        log_state()

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

        screen.fill("black")

        if not paused:
            dt = clock.tick(60) / 1000
            score_timer += dt
            if score_timer >= 1.0:
                score_timer -= 1.0
                score += 1

            if lives < MAX_LIVES:
                life_regen_timer += dt
                if life_regen_timer >= life_regen_time:
                    lives += 1
                    life_regen_timer = 0.0

            if shield_active:
                shield_age += dt
            elif shield_stacks > 0:
                shield_recharge_timer += dt
                if shield_recharge_timer >= shield_recharge_time:
                    shield_active = True
                    shield_age = 0.0
                    shield_recharge_timer = 0.0

            particle_timer += dt
            if particle_timer >= 0.03:
                particle_timer = 0.0
                backward = pygame.Vector2(0, 1).rotate(player.rotation + 180)
                exhaust = player.position + backward * (PLAYER_RADIUS * 0.5)
                Particle(exhaust.x, exhaust.y, backward * player.speed)

            for u in updatable:
                u.update(dt)

            for a in list(asteroids):
                for s in list(shots):
                    if a.alive() and s.alive() and a.collides_with(s):
                        log_event("asteroid_shot")
                        orb_pos = pygame.Vector2(a.position)
                        _spawn_explosion(orb_pos.x, orb_pos.y, a._full_radius)
                        _apply_damage(a, shot_damage)
                        s.kill()
                        score += 1
                        XPOrb(orb_pos.x, orb_pos.y)

            if level >= 2:
                enemy_spawn_timer += dt
                if enemy_spawn_timer >= enemy_spawn_rate:
                    enemy_spawn_timer = 0.0
                    margin = 30
                    edge = random.choice([
                        pygame.Vector2(-margin, random.uniform(0, 1) * SCREEN_HEIGHT),
                        pygame.Vector2(SCREEN_WIDTH + margin, random.uniform(0, 1) * SCREEN_HEIGHT),
                        pygame.Vector2(random.uniform(0, 1) * SCREEN_WIDTH, -margin),
                        pygame.Vector2(random.uniform(0, 1) * SCREEN_WIDTH, SCREEN_HEIGHT + margin),
                    ])
                    Enemy(edge.x, edge.y, pygame.Vector2(player.position))

            for e in list(enemies):
                for s in list(shots):
                    if e.alive() and s.alive() and e.collides_with(s):
                        _spawn_explosion(e.position.x, e.position.y, e.radius)
                        XPOrb(e.position.x, e.position.y)
                        e.kill()
                        s.kill()
                        score += 1

            if shield_active:
                for a in list(asteroids):
                    if a.alive():
                        dist = a.position.distance_to(player.position)
                        if dist < SHIELD_R + a._full_radius:
                            _spawn_explosion(a.position.x, a.position.y, a._full_radius)
                            XPOrb(a.position.x, a.position.y)
                            a.kill()
                            shield_active = False
                            shield_age = 0.0
                            shield_recharge_timer = 0.0
                            break

            for orb in list(xp_orbs):
                dist = orb.position.distance_to(player.position)
                if dist < XP_ORB_PICKUP_RADIUS:
                    direction = player.position - orb.position
                    if direction.length() > 0:
                        pull = 100 + (1 - dist / XP_ORB_PICKUP_RADIUS) * 400
                        orb.velocity = direction.normalize() * pull
                if dist < player.radius + orb.radius:
                    orb.kill()
                    award_xp()
        else:
            clock.tick(60)

        for p in particles:
            p.draw(screen)
        for d in drawable:
            d.draw(screen)

        if shield_active:
            alpha = int(abs(math.sin(shield_age * 3)) * 255)
            shield_surf.fill((0, 0, 0, 0))
            pygame.draw.circle(shield_surf, (100, 150, 255, alpha), shield_surf_center, SHIELD_R, 3)
            screen.blit(shield_surf, shield_surf.get_rect(center=(int(player.position.x), int(player.position.y))))

        score_surface = font.render(f"Score: {score}", True, "white")
        screen.blit(score_surface, (10, 10))
        draw_xp_bar(screen, font, cx, level, xp, xp_to_next)
        draw_lives(screen, lives, life_regen_timer / life_regen_time)

        if level_up_pending:
            level_up_pending = False
            chosen = upgrade.run(screen, clock, font, big_font, screen.copy())
            if chosen == "quit":
                return "quit", score
            apply_upgrade(chosen)

        if paused:
            screen.blit(pause_overlay, (0, 0))
            pause_title = big_font.render("PAUSED", True, "white")
            screen.blit(pause_title, pause_title.get_rect(center=(cx, cy - 100)))
            draw_button(screen, font, resume_btn, "Resume")
            draw_button(screen, font, end_game_btn, "End Game")
            draw_button(screen, font, pause_home_btn, "Home")

        pygame.display.flip()

        if not paused:
            for a in list(asteroids) + list(enemies):
                if a.collides_with(player) and player.invincibility_timer <= 0:
                    log_event("player_hit")
                    if shield_active:
                        shield_active = False
                        shield_age = 0.0
                        shield_recharge_timer = 0.0
                    else:
                        lives -= 1
                        life_regen_timer = 0.0
                        if lives <= 0:
                            return "game_over", score
                        player.invincibility_timer = INVINCIBILITY_TIME
                    break
