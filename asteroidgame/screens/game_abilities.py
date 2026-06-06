import random
import pygame

from ..constants import SCREEN_WIDTH, SCREEN_HEIGHT, PLAYER_RADIUS
from ..entities.fireblob import FireBlob
from ..entities.missile import Missile
from ..entities.vortex import Vortex, VORTEX_LIFETIME
from ..entities.shot import Shot

from .game_state import PULSE_RADIUS


# ---------------------------------------------------------------------------
# Bolt dash helpers
# ---------------------------------------------------------------------------

BOLT_RANGE   = 298
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


# ---------------------------------------------------------------------------
# Active abilities
# ---------------------------------------------------------------------------

def handle_pulse(state, player, groups, dt):
    if state.pulse_stacks == 0:
        return
    state.pulse_timer += dt
    if state.pulse_timer >= state.pulse_cooldown:
        state.pulse_timer      = 0.0
        state.pulse_visual_age = 0.0
        from .effects import kill_asteroid, kill_entity, kill_centibomb, combo_kill
        dmg = max(10, 3 * state.level)
        for a in list(groups['asteroids']):
            if a.alive() and a.position.distance_to(player.position) <= PULSE_RADIUS:
                if a.take_damage(dmg): state.score += combo_kill(state, kill_asteroid, a)
        for e in list(groups['enemies']):
            if e.alive() and e.position.distance_to(player.position) <= PULSE_RADIUS:
                if e.take_damage(dmg): state.score += combo_kill(state, kill_entity, e)
        for c in list(groups['centibombs']):
            if c.alive() and c.position.distance_to(player.position) <= PULSE_RADIUS:
                if c.take_damage(dmg): state.score += combo_kill(state, kill_centibomb, c)


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

    from .effects import kill_asteroid, kill_entity, kill_centibomb, combo_kill
    for v in list(groups['vortexes']):
        if not v.is_vortexing:
            TRAVEL_HIT_R = 18
            MIN_TRAVEL_T = 0.7
            if (VORTEX_LIFETIME - v.lifetime) >= MIN_TRAVEL_T:
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
                    if e.take_damage(vdmg): state.score += combo_kill(state, kill_entity, e)
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
        from .effects import kill_asteroid, kill_entity, kill_centibomb, combo_kill, spawn_hit_effect, ray_hits
        state.laser_timer      = 0.0
        state.laser_visual_age = 0.0
        state.laser_origin     = pygame.Vector2(player.position)
        state.laser_direction  = pygame.Vector2(0, 1).rotate(player.rotation).normalize()
        laser_dmg              = max(25, 3 * state.level)
        for a in list(groups['asteroids']):
            if a.alive() and ray_hits(state.laser_origin, state.laser_direction, a.position, a.radius):
                if a.take_damage(laser_dmg): state.score += combo_kill(state, kill_asteroid, a)
                else: spawn_hit_effect(a.position.x, a.position.y)
        for e in list(groups['enemies']):
            if e.alive() and ray_hits(state.laser_origin, state.laser_direction, e.position, e.radius):
                if e.take_damage(laser_dmg): state.score += combo_kill(state, kill_entity, e)
                else: spawn_hit_effect(e.position.x, e.position.y)
        for c in list(groups['centibombs']):
            if c.alive() and ray_hits(state.laser_origin, state.laser_direction, c.position, c.radius):
                if c.take_damage(laser_dmg): state.score += combo_kill(state, kill_centibomb, c)
                else: spawn_hit_effect(c.position.x, c.position.y)


def handle_bolt_dash(state, player, groups):
    if not player.just_dashed or state.bolt_dash_stacks == 0:
        return
    from .effects import kill_asteroid, kill_entity, kill_centibomb, combo_kill, spawn_hit_effect
    from ..entities.centibomb import Centibomb
    from ..entities.asteroid import Asteroid

    bolt_dmg   = max(20, 3 * state.level)
    bolt_count = random.randint(
        1 + (state.bolt_dash_stacks - 1),
        3 + (state.bolt_dash_stacks - 1),
    )
    candidates = sorted(
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
                state.score += combo_kill(state, kill_entity, target)
        else:
            spawn_hit_effect(target.position.x, target.position.y)


# ---------------------------------------------------------------------------
# Buddy / ricochet / homing (shot modifiers)
# ---------------------------------------------------------------------------

def resolve_buddy_pre_update(state, player, groups):
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
        s = Shot(state.buddy_delayed_pos.x, state.buddy_delayed_pos.y,
                 pygame.Vector2(0, 1).rotate(player.rotation), player.shot_radius)
        s.damage        = buddy_dmg
        s.is_buddy      = True
        s.ricochet_limit  = max(1, state.ricochet_stacks  // 3) if state.ricochet_stacks  > 0 else 0
        s.explosive_limit = max(1, state.explosive_stacks // 3) if state.explosive_stacks > 0 else 0
        if s.ricochet_limit > 0:
            s.bounces_left = 1


def append_buddy_history(state, player):
    state.buddy_history.append((state.game_time, pygame.Vector2(player.position), player.rotation))


def tag_ricochet(state, player, groups, shots_before_update):
    if state.ricochet_stacks > 0 and player.just_fired:
        for s in groups['shots']:
            if s not in shots_before_update and not getattr(s, 'is_buddy', False):
                s.bounces_left = 1


def steer_homing(state, player, groups, dt):
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
