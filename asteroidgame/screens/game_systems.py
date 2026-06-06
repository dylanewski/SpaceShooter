import random
import pygame

from ..constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT,
    ASTEROID_SPAWN_RATE_SECONDS, PLAYER_RADIUS,
    XP_ORB_PICKUP_RADIUS, INVINCIBILITY_TIME, MAX_LIVES,
)
from ..entities.enemy import Enemy, ENEMY_SPAWN_RATE_START, ENEMY_SPAWN_RATE_MIN, ENEMY_MAX_HEALTH
from ..entities.centibomb import Centibomb, CENTIBOMB_HEALTH
from ..entities.fireblob import FireBlob
from ..entities.missile import Missile
from ..entities.vortex import Vortex, VORTEX_LIFETIME
from ..entities.shot import Shot
from ..entities.xpstar import XPStar, XP_STAR_VALUE
from ..entities.bigxporb import BIG_XP_VALUE

from .game_state import PULSE_RADIUS, SHAKE_DURATION


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

    if state.lives < MAX_LIVES:
        state.life_regen_timer += dt
        if state.life_regen_timer >= state.life_regen_time:
            state.lives += 1
            state.life_regen_timer = 0.0

    if state.shield_active:
        state.shield_age += dt
    elif state.shield_stacks > 0:
        state.shield_recharge_timer += dt
        if state.shield_recharge_timer >= state.shield_recharge_time:
            state.shield_active        = True
            state.shield_age           = 0.0
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
    if (not state.boss_triggered
            and not state.boss_intro_active
            and not state.boss_active
            and (state.game_time - state.spawn_ramp_offset) >= 240.0):
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
        _enm_lo = ENEMY_SPAWN_RATE_MIN
    else:
        _ramp   = 200.0
        _ast_hi = ASTEROID_SPAWN_RATE_SECONDS * 8
        _ast_lo = ASTEROID_SPAWN_RATE_SECONDS * 1.5
        _enm_lo = ENEMY_SPAWN_RATE_MIN * 1.5
    _t = min(1.0, (state.game_time - state.spawn_ramp_offset) / _ramp)
    asteroid_field.spawn_rate = _ast_hi + (_ast_lo - _ast_hi) * _t
    state.enemy_spawn_rate    = ENEMY_SPAWN_RATE_START + (_enm_lo - ENEMY_SPAWN_RATE_START) * _t


def handle_boss_intro(state, groups, player, cx, cy, dt):
    from ..entities.boss import Boss
    if not state.boss_intro_active:
        return
    state.boss_intro_timer += dt
    FLEE_SPEED = 250
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
    if state.boss_intro_timer >= 3.0:
        state.boss_intro_active = False
        state.boss_active       = True
        state.current_boss      = Boss(cx, cy, player)
        state.boss_hp_visual    = 1.0
        for a in list(groups['asteroids']): a.kill()
        for e in list(groups['enemies']):   e.kill()


def handle_enemy_spawn(state, groups, cx, cy, dt):
    if state.level < 2 or state.boss_intro_active or state.boss_active:
        return
    state.enemy_spawn_timer += dt
    if state.enemy_spawn_timer >= state.enemy_spawn_rate:
        state.enemy_spawn_timer = 0.0
        SPAWN_MARGIN = 160   # well off screen — no flash on entry
        INNER_PAD    = 100   # target stays away from screen edges
        edge = random.choice([
            pygame.Vector2(-SPAWN_MARGIN,              random.uniform(0, 1) * SCREEN_HEIGHT),
            pygame.Vector2(SCREEN_WIDTH + SPAWN_MARGIN, random.uniform(0, 1) * SCREEN_HEIGHT),
            pygame.Vector2(random.uniform(0, 1) * SCREEN_WIDTH, -SPAWN_MARGIN),
            pygame.Vector2(random.uniform(0, 1) * SCREEN_WIDTH, SCREEN_HEIGHT + SPAWN_MARGIN),
        ])
        target = pygame.Vector2(
            random.uniform(INNER_PAD, SCREEN_WIDTH  - INNER_PAD),
            random.uniform(INNER_PAD, SCREEN_HEIGHT - INNER_PAD),
        )
        e = Enemy(edge.x, edge.y)
        e.health = int(ENEMY_MAX_HEALTH * (1.0 + int(state.game_time // 60) * 0.10))
        to_target = target - edge
        if to_target.length() > 0:
            e.velocity = to_target.normalize() * e.velocity.length()


def handle_xp_star_spawn(state, dt):
    if state.boss_intro_active or state.boss_active:
        return
    state.xp_star_timer += dt
    if state.xp_star_timer >= 10.0:
        state.xp_star_timer = 0.0
        if random.random() < 0.5:
            XPStar()


CENTIBOMB_SPAWN_INTERVAL = 25.0

BOLT_RANGE   = 350
BOLT_MAX_AGE = 0.35


def _gen_bolt_pts(x1, y1, x2, y2, segments=8):
    dx = x2 - x1
    dy = y2 - y1
    length = (dx * dx + dy * dy) ** 0.5
    pts = [(x1, y1)]
    for i in range(1, segments):
        t  = i / segments
        bx = x1 + dx * t
        by = y1 + dy * t
        if length > 0:
            perp_x = -dy / length
            perp_y =  dx / length
            offset = random.uniform(-length * 0.12, length * 0.12)
            bx += perp_x * offset
            by += perp_y * offset
        pts.append((bx, by))
    pts.append((x2, y2))
    return pts


def handle_bolt_dash(state, player, groups):
    if not player.just_dashed or state.bolt_dash_stacks == 0:
        return
    from .effects import kill_asteroid, kill_enemy, kill_centibomb, combo_kill, spawn_hit_effect
    from ..entities.centibomb import Centibomb
    from ..entities.asteroid import Asteroid

    bolt_dmg   = max(20, 3 * state.level)
    bolt_min   = 1 + (state.bolt_dash_stacks - 1)
    bolt_max   = 3 + (state.bolt_dash_stacks - 1)
    bolt_count = random.randint(bolt_min, bolt_max)
    candidates  = sorted(
        [t for t in list(groups['asteroids']) + list(groups['enemies']) + list(groups['centibombs'])
         if t.alive() and t.position.distance_to(player.position) <= BOLT_RANGE],
        key=lambda t: t.position.distance_to(player.position),
    )
    for target in candidates[:bolt_count]:
        pts = _gen_bolt_pts(player.position.x, player.position.y,
                            target.position.x, target.position.y)
        state.bolt_visuals.append({'pts': pts, 'age': 0.0, 'max_age': BOLT_MAX_AGE})
        if target.take_damage(bolt_dmg):
            if isinstance(target, Centibomb):
                state.score += combo_kill(state, kill_centibomb, target)
            elif isinstance(target, Asteroid):
                state.score += combo_kill(state, kill_asteroid, target)
            else:
                state.score += combo_kill(state, kill_enemy, target)
        else:
            spawn_hit_effect(target.position.x, target.position.y)


def handle_centibomb_spawn(state, groups, cx, cy, dt):
    if state.level < 3 or state.boss_intro_active or state.boss_active:
        return
    state.centibomb_spawn_timer += dt
    if state.centibomb_spawn_timer < CENTIBOMB_SPAWN_INTERVAL:
        return
    state.centibomb_spawn_timer = 0.0
    SPAWN_MARGIN = 160
    edge = random.choice([
        pygame.Vector2(-SPAWN_MARGIN,               random.uniform(0, 1) * SCREEN_HEIGHT),
        pygame.Vector2(SCREEN_WIDTH + SPAWN_MARGIN,  random.uniform(0, 1) * SCREEN_HEIGHT),
        pygame.Vector2(random.uniform(0, 1) * SCREEN_WIDTH, -SPAWN_MARGIN),
        pygame.Vector2(random.uniform(0, 1) * SCREEN_WIDTH,  SCREEN_HEIGHT + SPAWN_MARGIN),
    ])
    c = Centibomb(edge.x, edge.y)
    c.health = int(CENTIBOMB_HEALTH * (1.0 + int(state.game_time // 60) * 0.10))


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
# Abilities
# ---------------------------------------------------------------------------

def handle_pulse(state, player, groups, dt):
    if state.pulse_stacks == 0:
        return
    state.pulse_timer += dt
    if state.pulse_timer >= state.pulse_cooldown:
        state.pulse_timer     = 0.0
        state.pulse_visual_age = 0.0
        from .effects import kill_asteroid, kill_enemy, kill_centibomb, combo_kill
        dmg = max(10, 3 * state.level)
        for a in list(groups['asteroids']):
            if a.alive() and a.position.distance_to(player.position) <= PULSE_RADIUS:
                if a.take_damage(dmg):
                    state.score += combo_kill(state, kill_asteroid, a)
        for e in list(groups['enemies']):
            if e.alive() and e.position.distance_to(player.position) <= PULSE_RADIUS:
                if e.take_damage(dmg):
                    state.score += combo_kill(state, kill_enemy, e)
        for c in list(groups['centibombs']):
            if c.alive() and c.position.distance_to(player.position) <= PULSE_RADIUS:
                if c.take_damage(dmg):
                    state.score += combo_kill(state, kill_centibomb, c)


def handle_afterburn(state, player, dt):
    if state.afterburn_stacks == 0:
        return
    if player.velocity.length() >= player.speed * 0.95:
        state.afterburn_timer += dt
        if state.afterburn_timer >= 0.1:
            state.afterburn_timer = 0.0
            FireBlob(player.position.x, player.position.y,
                     state.afterburn_stacks * state.level, 4.5)
    else:
        state.afterburn_timer = 0.0


def handle_vortex(state, player, groups, dt):
    if state.vortex_stacks > 0:
        state.vortex_timer += dt
        if state.vortex_timer >= state.vortex_cooldown and pygame.key.get_pressed()[pygame.K_SPACE]:
            state.vortex_timer = 0.0
            Vortex(player.position.x, player.position.y,
                   pygame.Vector2(0, 1).rotate(player.rotation), max(5, state.level))

    from .effects import kill_asteroid, kill_enemy, kill_centibomb, combo_kill
    for v in list(groups['vortexes']):
        if not v.is_vortexing:
            TRAVEL_HIT_R  = 18
            MIN_TRAVEL_T  = 0.7
            has_traveled  = (VORTEX_LIFETIME - v.lifetime) >= MIN_TRAVEL_T
            if has_traveled:
                for a in list(groups['asteroids']):
                    if a.alive() and v.position.distance_to(a.position) < a.radius + TRAVEL_HIT_R:
                        v.anchor(); break
                if not v.is_vortexing:
                    for e in list(groups['enemies']):
                        if e.alive() and v.position.distance_to(e.position) < e.radius + TRAVEL_HIT_R:
                            v.anchor(); break
                if not v.is_vortexing:
                    for c in list(groups['centibombs']):
                        if c.alive() and v.position.distance_to(c.position) < c.radius + TRAVEL_HIT_R:
                            v.anchor(); break
        if not v.is_vortexing:
            continue
        for a in list(groups['asteroids']):
            if a.alive():
                dist = a.position.distance_to(v.position)
                if 0 < dist < v.pull_radius:
                    a.velocity += (v.position - a.position).normalize() * (1 - dist / v.pull_radius) * 280 * dt
        for e in list(groups['enemies']):
            if e.alive():
                dist = e.position.distance_to(v.position)
                if 0 < dist < v.pull_radius:
                    e.velocity += (v.position - e.position).normalize() * (1 - dist / v.pull_radius) * 280 * dt
        for c in list(groups['centibombs']):
            if c.alive():
                dist = c.position.distance_to(v.position)
                if 0 < dist < v.pull_radius:
                    c.velocity += (v.position - c.position).normalize() * (1 - dist / v.pull_radius) * 280 * dt
        for orb in list(groups['xp_orbs']) + list(groups['big_xp_orbs']):
            if orb.alive():
                dist = orb.position.distance_to(v.position)
                if 0 < dist < v.pull_radius:
                    orb.velocity += (v.position - orb.position).normalize() * (1 - dist / v.pull_radius) * 320 * dt
        for star in list(groups['xp_stars']):
            if star.alive():
                dist = star.position.distance_to(v.position)
                if 0 < dist < v.pull_radius:
                    star.position += (v.position - star.position).normalize() * (1 - dist / v.pull_radius) * 160 * dt
        if v.damage_timer >= 1.0:
            v.damage_timer -= 1.0
            vdmg = int(v.damage_per_second)
            for a in list(groups['asteroids']):
                if a.alive() and a.position.distance_to(v.position) < v.pull_radius:
                    if a.take_damage(vdmg): state.score += combo_kill(state, kill_asteroid, a)
            for e in list(groups['enemies']):
                if e.alive() and e.position.distance_to(v.position) < v.pull_radius:
                    if e.take_damage(vdmg): state.score += combo_kill(state, kill_enemy, e)
            for c in list(groups['centibombs']):
                if c.alive() and c.position.distance_to(v.position) < v.pull_radius:
                    if c.take_damage(vdmg): state.score += combo_kill(state, kill_centibomb, c)


def handle_missile_ability(state, player, groups, dt):
    if state.missile_stacks > 0:
        state.missile_timer += dt
        if state.missile_timer >= state.missile_cooldown and pygame.key.get_pressed()[pygame.K_SPACE]:
            state.missile_timer = 0.0
            missile_count = state.missile_stacks * 3
            targets = sorted(
                [t for t in list(groups['asteroids']) + list(groups['enemies']) + list(groups['centibombs'])
                 if t.alive() and 0 <= t.position.x <= SCREEN_WIDTH and 0 <= t.position.y <= SCREEN_HEIGHT],
                key=lambda t: t.position.distance_to(player.position),
            )
            side = random.choice([-1, 1])
            state.missile_queue.clear()
            if targets:
                nearest = targets[0]
                for _ in range(missile_count):
                    state.missile_queue.append((side, nearest))
                    side = -side
            state.missile_launch_timer = 0.0

    if state.missile_queue:
        state.missile_launch_timer -= dt
        if state.missile_launch_timer <= 0:
            ms, tgt = state.missile_queue.pop(0)
            if tgt.alive():
                forward = pygame.Vector2(0, 1).rotate(player.rotation)
                wing    = pygame.Vector2(0, 1).rotate(player.rotation + 90)
                spawn   = player.position + wing * (ms * 18)
                Missile(spawn.x, spawn.y, tgt, launch_dir=forward, boost_time=0.4)
            state.missile_launch_timer = 0.1


def handle_laser_ability(state, player, groups, dt):
    if state.laser_stacks == 0:
        return
    state.laser_timer += dt
    if state.laser_timer >= state.laser_cooldown and pygame.key.get_pressed()[pygame.K_SPACE]:
        from .effects import kill_asteroid, kill_enemy, kill_centibomb, combo_kill, spawn_hit_effect
        state.laser_timer     = 0.0
        state.laser_visual_age = 0.0
        state.laser_origin    = pygame.Vector2(player.position)
        state.laser_direction = pygame.Vector2(0, 1).rotate(player.rotation).normalize()
        laser_dmg             = max(25, 3 * state.level)
        from .effects import ray_hits
        for a in list(groups['asteroids']):
            if a.alive() and ray_hits(state.laser_origin, state.laser_direction, a.position, a.radius):
                if a.take_damage(laser_dmg): state.score += combo_kill(state, kill_asteroid, a)
                else: spawn_hit_effect(a.position.x, a.position.y)
        for e in list(groups['enemies']):
            if e.alive() and ray_hits(state.laser_origin, state.laser_direction, e.position, e.radius):
                if e.take_damage(laser_dmg): state.score += combo_kill(state, kill_enemy, e)
                else: spawn_hit_effect(e.position.x, e.position.y)
        for c in list(groups['centibombs']):
            if c.alive() and ray_hits(state.laser_origin, state.laser_direction, c.position, c.radius):
                if c.take_damage(laser_dmg): state.score += combo_kill(state, kill_centibomb, c)
                else: spawn_hit_effect(c.position.x, c.position.y)


def resolve_buddy_pre_update(state, player, groups):
    """Called BEFORE updatable.update() — uses last frame's just_fired."""
    while state.buddy_history and state.game_time - state.buddy_history[0][0] > 0.8:
        state.buddy_history.popleft()

    BUDDY_LAG = 0.5
    target_t  = state.game_time - BUDDY_LAG
    state.buddy_delayed_pos = pygame.Vector2(player.position)
    state.buddy_delayed_rot = player.rotation
    for entry in reversed(state.buddy_history):
        if entry[0] <= target_t:
            state.buddy_delayed_pos = pygame.Vector2(entry[1])
            state.buddy_delayed_rot = entry[2]
            break

    if state.buddy_stacks > 0 and player.just_fired:
        buddy_dmg = max(1, int(state.shot_damage * (1/3 + (state.buddy_stacks - 1) * 0.07)))
        s         = Shot(state.buddy_delayed_pos.x, state.buddy_delayed_pos.y,
                         pygame.Vector2(0, 1).rotate(player.rotation), player.shot_radius)
        s.damage        = buddy_dmg
        s.is_buddy      = True
        s.ricochet_limit  = max(1, state.ricochet_stacks  // 3) if state.ricochet_stacks  > 0 else 0
        s.explosive_limit = max(1, state.explosive_stacks // 3) if state.explosive_stacks > 0 else 0
        if s.ricochet_limit > 0:
            s.bounces_left = 1

    if state.homing_strength > 0:
        TURN_SPEED   = state.homing_strength * 15
        HOMING_RANGE = 380
        for s in groups['shots']:
            if s.velocity.length() == 0:
                continue
            nearest, nearest_dist = None, float('inf')
            for target in list(groups['asteroids']) + list(groups['enemies']):
                if target.alive():
                    d = s.position.distance_to(target.position)
                    if d < nearest_dist:
                        nearest_dist, nearest = d, target
            if nearest and nearest_dist < HOMING_RANGE:
                to_target = nearest.position - s.position
                if to_target.length() > 0:
                    from .game_state import SHAKE_DURATION  # re-use dt from caller
                    pass  # dt steering happens inline in caller via homing dt


def append_buddy_history(state, player):
    """Called AFTER updatable.update() — records this frame's position."""
    state.buddy_history.append((state.game_time, pygame.Vector2(player.position), player.rotation))


def tag_ricochet(state, player, groups, shots_before_update):
    """Called AFTER updatable.update() — uses this frame's just_fired."""
    if state.ricochet_stacks > 0 and player.just_fired:
        for s in groups['shots']:
            if s not in shots_before_update and not getattr(s, 'is_buddy', False):
                s.bounces_left = 1  # flag: spawn ricochets on hit (count = state.ricochet_stacks)


def steer_homing(state, player, groups, dt):
    """Homing shot steering — call before updatable update."""
    if state.homing_strength == 0:
        return
    TURN_SPEED   = state.homing_strength * 15
    HOMING_RANGE = 380
    for s in groups['shots']:
        if s.velocity.length() == 0:
            continue
        nearest, nearest_dist = None, float('inf')
        for target in list(groups['asteroids']) + list(groups['enemies']) + list(groups['centibombs']):
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
        state.shield_stacks += 1
        state.shield_recharge_time = 30.0 * (0.7 ** (state.shield_stacks - 1))
        state.shield_active = True
        state.shield_age    = 0.0
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
        state.life_regen_time *= 0.75
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
    elif name == "Crit Chance Up":
        state.crit_chance += 10
