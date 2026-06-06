import pygame

from ..constants import SCREEN_WIDTH, SCREEN_HEIGHT, PLAYER_RADIUS
from ..entities.asteroid import Asteroid
from ..entities.asteroidfield import AsteroidField
from ..entities.enemy import Enemy
from ..entities.fireblob import FireBlob
from ..entities.particle import Particle
from ..entities.player import Player
from ..entities.missile import Missile
from ..entities.shot import Shot
from ..entities.vortex import Vortex
from ..entities.boss import Boss
from ..entities.boss_shot import BossShot
from ..entities.centibomb import Centibomb
from ..entities.mine import Mine
from ..entities.shooter import Shooter
from ..entities.xporb import XPOrb
from ..entities.bigxporb import BigXPOrb
from ..entities.xpstar import XPStar
from ..ui import make_button
from ..logger import log_state

from . import upgrade
from .game_state import GameState, DEATH_DURATION
from .game_systems import (
    update_timers, update_particle_trail,
    handle_boss_trigger, update_spawn_rates,
    handle_boss_intro, handle_xp_collection, apply_upgrade,
)
from .game_abilities import (
    handle_pulse, handle_afterburn, handle_vortex,
    handle_missile_ability, handle_laser_ability, handle_bolt_dash,
    resolve_buddy_pre_update, append_buddy_history, tag_ricochet, steer_homing,
)
from .game_spawn import (
    handle_enemy_spawn, handle_xp_star_spawn, handle_centibomb_spawn,
    handle_shooter_spawn, handle_mine_drop,
)
from .game_combat import (
    handle_shot_asteroid, handle_shot_enemy, handle_shot_boss, handle_shot_centibomb,
    handle_missile_enemies, handle_missile_boss,
    handle_blob_damage, handle_plow, handle_shield, handle_mine_contact,
    handle_boss_shot_player, handle_player_damage,
)
from .game_draw import draw_frame, draw_death_frame, draw_pause_overlay


# ---------------------------------------------------------------------------

def run(screen, clock, font, big_font) -> tuple[str, int]:
    cx, cy = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2

    # --- surfaces ---
    game_surf     = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    pause_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    pause_overlay.fill((0, 0, 0, 160))

    SHIELD_R         = PLAYER_RADIUS + 10
    shield_surf_size = SHIELD_R * 2 + 6
    shield_surf      = pygame.Surface((shield_surf_size, shield_surf_size), pygame.SRCALPHA)

    surfs = {
        'shield': shield_surf,
        'pulse':  pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA),
        'laser':  pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA),
        'danger': pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA),
        'exp':    pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA),
    }

    # --- fonts ---
    fonts = {
        'main':   font,
        'big':    big_font,
        'icon':   pygame.font.Font("assets/fonts/Symtext.ttf", 11),
        'danger': pygame.font.Font("assets/fonts/Symtext.ttf", 36),
    }

    # --- boss intro image ---
    try:
        _excl_raw   = pygame.image.load("assets/images/game/skull!boss.png").convert_alpha()
        _excl_scale = 600 / max(_excl_raw.get_width(), _excl_raw.get_height())
        boss_excl_image = pygame.transform.scale(
            _excl_raw,
            (int(_excl_raw.get_width() * _excl_scale), int(_excl_raw.get_height() * _excl_scale))
        )
    except Exception:
        boss_excl_image = None

    _skull_raw  = pygame.image.load("assets/images/game/skulluismall.png").convert_alpha()
    skull_image = pygame.transform.scale(_skull_raw, (34, 34))

    # --- pause buttons ---
    resume_btn     = make_button((cx, 420))
    end_game_btn   = make_button((cx, 500))
    pause_home_btn = make_button((cx, 580))

    # --- sprite groups ---
    updatable   = pygame.sprite.Group()
    drawable    = pygame.sprite.Group()
    particles   = pygame.sprite.Group()
    asteroids   = pygame.sprite.Group()
    enemies     = pygame.sprite.Group()
    shots       = pygame.sprite.Group()
    xp_orbs     = pygame.sprite.Group()
    big_xp_orbs = pygame.sprite.Group()
    xp_stars    = pygame.sprite.Group()
    fire_blobs  = pygame.sprite.Group()
    vortexes    = pygame.sprite.Group()
    missiles    = pygame.sprite.Group()
    bosses      = pygame.sprite.Group()
    boss_shots  = pygame.sprite.Group()
    centibombs  = pygame.sprite.Group()
    mines       = pygame.sprite.Group()

    groups = {
        'updatable':   updatable,
        'drawable':    drawable,
        'particles':   particles,
        'asteroids':   asteroids,
        'enemies':     enemies,
        'shots':       shots,
        'xp_orbs':     xp_orbs,
        'big_xp_orbs': big_xp_orbs,
        'xp_stars':    xp_stars,
        'fire_blobs':  fire_blobs,
        'vortexes':    vortexes,
        'missiles':    missiles,
        'bosses':      bosses,
        'boss_shots':  boss_shots,
        'centibombs':  centibombs,
        'mines':       mines,
    }

    # --- containers ---
    Asteroid.containers      = (updatable, drawable, asteroids)
    Enemy.containers         = (updatable, drawable, enemies)
    Player.containers        = (updatable, drawable)
    AsteroidField.containers = (updatable,)
    Shot.containers          = (updatable, drawable, shots)
    XPOrb.containers         = (updatable, drawable, xp_orbs)
    BigXPOrb.containers      = (updatable, drawable, big_xp_orbs)
    XPStar.containers        = (updatable, drawable, xp_stars)
    Particle.containers      = (updatable, particles)
    FireBlob.containers      = (updatable, fire_blobs)
    Vortex.containers        = (updatable, vortexes)
    Missile.containers       = (updatable, missiles)
    Boss.containers          = (bosses,)
    BossShot.containers      = (updatable, drawable, boss_shots)
    Centibomb.containers     = (updatable, drawable, centibombs)
    Mine.containers          = (updatable, mines)
    Shooter.containers       = (updatable, drawable, enemies)

    asteroid_field = AsteroidField()
    player         = Player(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)

    # --- state ---
    state   = GameState()
    paused  = False
    dt      = 0.0

    ui = {
        'cx':             cx,
        'cy':             cy,
        'skull_image':    skull_image,
        'boss_excl_image': boss_excl_image,
        'danger':         surfs['danger'],
    }

    # -----------------------------------------------------------------------
    # Main loop
    # -----------------------------------------------------------------------
    while True:
        log_state()

        pause_action = None
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit", state.score, state.highest_combo
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
            return pause_action, state.score, state.highest_combo

        game_surf.fill("black")

        # --- death animation ---
        if state.death_active and state.death_pos is not None:
            dt = clock.tick(60) / 1000
            draw_death_frame(game_surf, screen, state, groups, surfs, dt)
            pygame.display.flip()
            if state.death_timer >= DEATH_DURATION:
                return "game_over", state.score, state.highest_combo
            continue

        # --- update (skipped while paused) ---
        if not paused:
            dt = clock.tick(60) / 1000
            state.game_time += dt

            handle_boss_trigger(state)
            update_spawn_rates(state, asteroid_field)
            update_timers(state, dt)
            update_particle_trail(state, player, dt)

            handle_pulse(state, player, groups, dt)
            handle_afterburn(state, player, dt)
            handle_vortex(state, player, groups, dt)
            handle_missile_ability(state, player, groups, dt)
            handle_laser_ability(state, player, groups, dt)

            shots_before_update = set(shots)
            resolve_buddy_pre_update(state, player, groups)
            steer_homing(state, player, groups, dt)

            for u in updatable:
                u.update(dt)

            state.plow_timer              = min(state.plow_cooldown, state.plow_timer + dt)
            state.plow_invincibility_timer = max(0.0, state.plow_invincibility_timer - dt)

            append_buddy_history(state, player)
            tag_ricochet(state, player, groups, shots_before_update)
            handle_bolt_dash(state, player, groups)

            handle_boss_intro(state, groups, player, cx, cy, dt)
            if state.boss_active and state.current_boss is not None:
                state.current_boss.update(dt)

            handle_shot_asteroid(state, groups)
            handle_shot_enemy(state, groups)
            handle_shot_centibomb(state, groups)
            handle_shot_boss(state, groups)
            handle_missile_enemies(state, groups)
            handle_missile_boss(state, groups)
            handle_blob_damage(state, groups, dt)
            handle_mine_drop(state, player, groups, dt)
            handle_mine_contact(state, groups)
            handle_plow(state, player, groups)
            handle_shield(state, player, groups)

            handle_enemy_spawn(state, groups, cx, cy, dt)
            handle_centibomb_spawn(state, groups, cx, cy, dt)
            handle_shooter_spawn(state, player, groups, cx, cy, dt)
            handle_xp_star_spawn(state, dt)
            handle_xp_collection(state, player, groups)

        else:
            clock.tick(60)

        # --- draw ---
        draw_frame(game_surf, screen, state, player, groups, surfs, fonts, ui, dt)

        # --- level up ---
        if state.level_up_pending:
            state.level_up_pending = False
            chosen = upgrade.run(screen, clock, font, screen.copy())
            if chosen == "quit":
                return "quit", state.score, state.highest_combo
            apply_upgrade(state, player, chosen)

        if paused:
            draw_pause_overlay(screen, state, big_font, fonts, cx, cy,
                               pause_overlay, resume_btn, end_game_btn, pause_home_btn)

        pygame.display.flip()

        # --- player damage (after flip so last frame stays visible) ---
        if not paused:
            handle_boss_shot_player(state, player, groups)
            handle_player_damage(state, player, groups)
