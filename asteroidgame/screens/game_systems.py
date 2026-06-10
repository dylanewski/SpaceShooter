import pygame

from ..constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    ASTEROID_SPAWN_RATE_SECONDS, PLAYER_RADIUS,
    XP_ORB_PICKUP_RADIUS, PLAYER_MAX_HP,
    BACKUP_ENGINE_COOLDOWN_BASE, BACKUP_ENGINE_COOLDOWN_STEP,
)
from ..entities.enemy import ENEMY_SPAWN_RATE_START, ENEMY_SPAWN_RATE_MIN
from ..entities.xpstar import XP_STAR_VALUE
from ..entities.bigxporb import BIG_XP_VALUE


# ---------------------------------------------------------------------------
# Timers and passive regen
# ---------------------------------------------------------------------------

def update_timers(state, dt):
    state.score_timer += dt
    if state.score_timer >= 1.0:
        state.score_timer -= 1.0
        state.score += 1

    target_frac = min(1.0, state.xp / state.xp_to_next)
    if state.xp_visual > target_frac + 0.05:
        state.xp_visual = 0.0
    state.xp_visual = min(target_frac, state.xp_visual + dt * 0.6)

    if state.combo_timer > 0:
        state.combo_timer = max(0.0, state.combo_timer - dt)
        if state.combo_timer == 0.0:
            state.combo_display_count = state.combo_count
            state.combo_count         = 0
            state.combo_fade_timer    = 0.5
    if state.combo_fade_timer > 0:
        state.combo_fade_timer = max(0.0, state.combo_fade_timer - dt)
    if state.combo_shake_timer > 0:
        state.combo_shake_timer = max(0.0, state.combo_shake_timer - dt)

    if state.hp < PLAYER_MAX_HP:
        state.hp = min(PLAYER_MAX_HP, state.hp + state.hp_regen_rate * dt)

    if state.backup_engine_stacks > 0:
        state.backup_engine_timer = min(state.backup_engine_cooldown,
                                        state.backup_engine_timer + dt)

    if state.shield_active:
        state.shield_age += dt
    elif state.shield_stacks > 0:
        state.shield_recharge_timer += dt
        if state.shield_recharge_timer >= state.shield_recharge_time:
            state.shield_hp             = state.shield_hp_max
            state.shield_active         = True
            state.shield_age            = 0.0
            state.shield_recharge_timer = 0.0


def update_particle_trail(state, player, dt):
    state.particle_timer += dt
    if state.particle_timer >= 0.03:
        state.particle_timer = 0.0
        from ..entities.particle import Particle
        backward = pygame.Vector2(0, 1).rotate(player.rotation + 180)
        exhaust  = player.position + backward * (PLAYER_RADIUS * 0.5)
        Particle(exhaust.x, exhaust.y, backward * player.speed)


# ---------------------------------------------------------------------------
# Boss trigger & spawn rates
# ---------------------------------------------------------------------------

def handle_boss_trigger(state):
    trigger = 240.0 if state.game_phase == 1 else 180.0
    if (not state.boss_triggered
            and not state.boss_intro_active
            and not state.boss_active
            and (state.game_time - state.spawn_ramp_offset) >= trigger):
        state.boss_intro_active = True
        state.boss_intro_timer  = 0.0
        state.boss_triggered    = True


def update_spawn_rates(state, asteroid_field):
    if state.boss_intro_active or state.boss_active:
        asteroid_field.spawn_rate = 9999.0
        return
    if state.game_phase == 1:
        _ramp   = 240.0
        _ast_hi = ASTEROID_SPAWN_RATE_SECONDS * 8
        _ast_lo = ASTEROID_SPAWN_RATE_SECONDS / 2
        _enm_lo = ENEMY_SPAWN_RATE_MIN * 1.6    # junk cap at 3.2s — dashers fill the gap
    else:
        _ramp   = 90.0                           # faster pressure build than phase 1
        _ast_hi = ASTEROID_SPAWN_RATE_SECONDS * 8
        _ast_lo = ASTEROID_SPAWN_RATE_SECONDS    # cap at 0.8s (denser than phase 1)
        _enm_lo = ENEMY_SPAWN_RATE_MIN * 1.8    # junk cap at 3.6s — shooters + dashers fill the gap
    _t = min(1.0, (state.game_time - state.spawn_ramp_offset) / _ramp)
    asteroid_field.spawn_rate = _ast_hi + (_ast_lo - _ast_hi) * _t
    state.enemy_spawn_rate    = ENEMY_SPAWN_RATE_START + (_enm_lo - ENEMY_SPAWN_RATE_START) * _t


def handle_boss_intro(state, groups, player, cx, cy, dt):
    from ..entities.boss  import Boss
    from ..entities.boss2 import Boss2
    if not state.boss_intro_active:
        return
    state.boss_intro_timer += dt
    FLEE_SPEED = 200
    OFFSCREEN  = 150
    center     = pygame.Vector2(cx, cy)
    for a in list(groups['asteroids']):
        if a.alive():
            d = a.position - center
            a.velocity = (d.normalize() if d.length() > 0 else pygame.Vector2(1, 0)) * FLEE_SPEED
            if (a.position.x < -OFFSCREEN or a.position.x > SCREEN_WIDTH + OFFSCREEN or
                    a.position.y < -OFFSCREEN or a.position.y > SCREEN_HEIGHT + OFFSCREEN):
                a.kill()
    for e in list(groups['enemies']):
        if e.alive():
            d = e.position - center
            e.velocity = (d.normalize() if d.length() > 0 else pygame.Vector2(1, 0)) * FLEE_SPEED
            if (e.position.x < -OFFSCREEN or e.position.x > SCREEN_WIDTH + OFFSCREEN or
                    e.position.y < -OFFSCREEN or e.position.y > SCREEN_HEIGHT + OFFSCREEN):
                e.kill()
    for c in list(groups['centibombs']):
        if c.alive():
            d = c.position - center
            c.velocity = (d.normalize() if d.length() > 0 else pygame.Vector2(1, 0)) * FLEE_SPEED
            if (c.position.x < -OFFSCREEN or c.position.x > SCREEN_WIDTH + OFFSCREEN or
                    c.position.y < -OFFSCREEN or c.position.y > SCREEN_HEIGHT + OFFSCREEN):
                c.kill()
    if state.boss_intro_timer >= 5.0:
        state.boss_intro_active = False
        state.boss_active       = True
        if state.game_phase == 2:
            state.current_boss = Boss2(cx, cy, player)
        else:
            state.current_boss = Boss(cx, cy, player)
        state.boss_hp_visual    = 1.0
        for a in list(groups['asteroids']): a.kill()
        for e in list(groups['enemies']):   e.kill()


# ---------------------------------------------------------------------------
# XP collection
# ---------------------------------------------------------------------------

def handle_xp_collection(state, player, groups):
    for star in list(groups['xp_stars']):
        if star.position.distance_to(player.position) < player.radius + star.pickup_radius:
            star.kill()
            state.award_xp(30 if state.game_phase >= 2 else XP_STAR_VALUE)

    for orb in list(groups['xp_orbs']):
        dist = orb.position.distance_to(player.position)
        if dist < XP_ORB_PICKUP_RADIUS and dist > 0:
            orb.velocity = (player.position - orb.position).normalize() * (100 + (1 - dist / XP_ORB_PICKUP_RADIUS) * 400)
        if dist < player.radius + orb.radius:
            orb.kill()
            state.award_xp()

    for orb in list(groups['big_xp_orbs']):
        dist = orb.position.distance_to(player.position)
        if dist < XP_ORB_PICKUP_RADIUS and dist > 0:
            orb.velocity = (player.position - orb.position).normalize() * (100 + (1 - dist / XP_ORB_PICKUP_RADIUS) * 400)
        if dist < player.radius + orb.radius:
            orb.kill()
            state.award_xp(BIG_XP_VALUE)


# ---------------------------------------------------------------------------
# Upgrade application
# ---------------------------------------------------------------------------

def apply_upgrade(state, player, name):
    if name == "Rapid Fire":
        player.shot_cooldown_time *= 0.9
        state.rapid_fire_stacks += 1
    elif name == "Higher Caliber Rounds":
        state.shot_damage += 6
        state.caliber_stacks += 1
    elif name == "Shield":
        state.shield_stacks       += 1
        state.shield_hp_max        = 35 + (state.shield_stacks - 1) * 20
        state.shield_recharge_time = max(10.0, 25.0 - (state.shield_stacks - 1) * 7.0)
        state.shield_hp            = state.shield_hp_max
        state.shield_active        = True
        state.shield_age           = 0.0
    elif name == "Armor":
        state.armor_stacks += 1
    elif name == "XP Generator":
        state.xp_multiplier *= 1.1
        state.xp_gen_stacks += 1
    elif name == "Bigger Bullets":
        state.bigger_bullets_stacks += 1
        mult = 1.5 if state.bigger_bullets_stacks == 1 else (1 + 1/3)
        player.shot_radius = int(player.shot_radius * mult)
        state.shot_damage  = int(state.shot_damage * 1.05)
    elif name == "Speed Boost":
        player.speed *= 1.2
        state.speed_stacks += 1
    elif name == "Quick Regen":
        state.hp_regen_rate      += 1.0
        state.quick_regen_stacks += 1
    elif name == "Pulse Wave":
        state.pulse_stacks  += 1
        state.pulse_cooldown = max(2.0, 5.0 - (state.pulse_stacks - 1) * 0.5)
    elif name == "Afterburn":
        state.afterburn_stacks += 1
    elif name == "Homing Shots":
        state.homing_strength += 1
    elif name == "Ricochet":
        state.ricochet_stacks += 1
    elif name == "Explosive Rounds":
        state.explosive_stacks += 1
        state.shot_damage = int(state.shot_damage * 1.05)
    elif name == "Plow":
        state.plow_stacks   += 1
        state.plow_cooldown *= 0.9
        if state.plow_image is None:
            raw = pygame.image.load("assets/images/game/plow.png").convert_alpha()
            target = PLAYER_RADIUS * 2
            scale  = target / max(raw.get_width(), raw.get_height())
            state.plow_image = pygame.transform.scale(raw, (int(raw.get_width() * scale), int(raw.get_height() * scale)))
    elif name == "Little Buddy":
        state.buddy_stacks += 1
        if state.buddy_image is None:
            raw    = pygame.image.load("assets/images/game/lilbuddy.png").convert_alpha()
            target = PLAYER_RADIUS * 2 * 0.65
            scale  = target / max(raw.get_width(), raw.get_height())
            state.buddy_image = pygame.transform.scale(raw, (int(raw.get_width() * scale), int(raw.get_height() * scale)))
    elif name == "Vortex Field":
        state.vortex_stacks  += 1
        state.vortex_cooldown = max(10.0, 15.0 - (state.vortex_stacks - 1) * 5)
    elif name == "Bolt Dash":
        state.bolt_dash_stacks    += 1
        player.dash_cooldown_time  = max(1.5, player.dash_cooldown_time - 0.4)
    elif name == "Missile Salvo":
        state.missile_stacks += 1
    elif name == "Laser Beam":
        state.laser_stacks  += 1
        state.laser_cooldown = max(4.0, 6.4 - (state.laser_stacks - 1) * 0.5)
    elif name == "Mines":
        state.mine_stacks += 1
        state.mine_cooldown = 3.6 * (0.8 ** (state.mine_stacks - 1))
    elif name == "Crit Chance Up":
        state.crit_chance += 10
    elif name == "Syphon Bullets":
        state.syphon_stacks += 1
    elif name == "Backup Engine":
        state.backup_engine_stacks   += 1
        state.backup_engine_cooldown  = max(
            60.0,
            BACKUP_ENGINE_COOLDOWN_BASE - (state.backup_engine_stacks - 1) * BACKUP_ENGINE_COOLDOWN_STEP,
        )
        state.backup_engine_timer = state.backup_engine_cooldown  # start ready after pickup
