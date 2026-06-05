import pygame

from ..constants import SCREEN_WIDTH, SCREEN_HEIGHT, INVINCIBILITY_TIME, PLAYER_RADIUS, SHOT_RADIUS
from ..entities.shot import Shot
from ..entities.xporb import XPOrb
from ..entities.bigxporb import BigXPOrb
from ..logger import log_event
from .effects import (
    spawn_explosion, spawn_hit_effect, spawn_boss_explosion, kill_asteroid, kill_enemy,
)
from .game_state import SHAKE_DURATION, RICOCHET_RANGE, EXPLOSION_RADIUS


# ---------------------------------------------------------------------------
# Boss kill
# ---------------------------------------------------------------------------

def kill_boss(state, groups):
    if state.current_boss is None:
        return
    for grp in [groups['asteroids'], groups['enemies'], groups['shots'],
                groups['xp_orbs'], groups['xp_stars']]:
        for sp in list(grp): sp.kill()
    state.missile_queue.clear()

    segs = list(state.current_boss.get_segments())
    hx, hy = segs[0][0].x, segs[0][0].y
    for seg_pos, seg_r in segs:
        spawn_boss_explosion(seg_pos.x, seg_pos.y, seg_r * 2)
    for ring_r in [90, 165, 240]:
        state.explosion_visuals.append([hx, hy, ring_r, 0.0])
    state.shake_timer = 1.5

    for _ in range(10):
        BigXPOrb(hx, hy)

    state.current_boss.kill()
    state.current_boss     = None
    state.boss_active      = False
    state.boss_triggered   = False
    state.game_phase      += 1
    state.spawn_ramp_offset = state.game_time


# ---------------------------------------------------------------------------
# Shot collisions
# ---------------------------------------------------------------------------

def _apply_explosive(state, groups, s_pos, shot_radius):
    bullet_scale = shot_radius / SHOT_RADIUS   # 1.0 at base, grows with Bigger Bullets
    exp_r  = int((EXPLOSION_RADIUS + (state.explosive_stacks - 1) * 20) * bullet_scale)
    splash = max(5, state.shot_damage // 3) * state.explosive_stacks
    spawn_explosion(s_pos.x, s_pos.y, exp_r // 2)
    state.explosion_visuals.append([s_pos.x, s_pos.y, exp_r, 0.0])
    for ta in list(groups['asteroids']):
        if ta.alive() and ta.position.distance_to(s_pos) < exp_r:
            if ta.take_damage(splash): state.score += kill_asteroid(ta)
    for te in list(groups['enemies']):
        if te.alive() and te.position.distance_to(s_pos) < exp_r:
            if te.take_damage(splash): state.score += kill_enemy(te)


def _spawn_ricochets(state, groups, s):
    """Fork up to ricochet_stacks new shots from the impact point, inheriting parent properties."""
    parent_dmg   = s.damage if s.damage else state.shot_damage
    ricochet_dmg = max(1, parent_dmg // 2)

    candidates = sorted(
        [t for t in list(groups['asteroids']) + list(groups['enemies'])
         if t.alive() and t.position.distance_to(s.position) < RICOCHET_RANGE],
        key=lambda t: t.position.distance_to(s.position),
    )

    for target in candidates[:state.ricochet_stacks]:
        d = target.position - s.position
        if d.length() == 0:
            continue
        r = Shot(s.position.x, s.position.y, d.normalize(), s.radius)
        r.damage       = ricochet_dmg
        r.bounces_left = 0      # no further ricocheting
        r.fragment     = False  # can still trigger explosives


def handle_shot_asteroid(state, groups):
    for a in list(groups['asteroids']):
        for s in list(groups['shots']):
            if not (a.alive() and s.alive() and a.collides_with(s)):
                continue
            log_event("asteroid_shot")
            dmg = s.damage or state.shot_damage
            if state.explosive_stacks > 0 and not s.fragment:
                _apply_explosive(state, groups, s.position, s.radius)
            if s.bounces_left > 0:
                _spawn_ricochets(state, groups, s)
            s.kill()
            if a.take_damage(dmg): state.score += kill_asteroid(a)
            else: spawn_hit_effect(a.position.x, a.position.y)


def handle_shot_enemy(state, groups):
    for e in list(groups['enemies']):
        for s in list(groups['shots']):
            if not (e.alive() and s.alive() and e.collides_with(s)):
                continue
            shot_vel = pygame.Vector2(s.velocity)
            dmg      = s.damage or state.shot_damage
            if state.explosive_stacks > 0 and not s.fragment:
                _apply_explosive(state, groups, s.position, s.radius)
            if s.bounces_left > 0:
                _spawn_ricochets(state, groups, s)
            s.kill()
            if e.take_damage(dmg): state.score += kill_enemy(e)
            else: spawn_hit_effect(e.position.x, e.position.y, shot_vel)


def handle_shot_boss(state, groups):
    if not (state.boss_active and state.current_boss is not None):
        return
    for s in list(groups['shots']):
        if not s.alive():
            continue
        for seg_pos, seg_r in state.current_boss.get_segments():
            if seg_pos.distance_to(s.position) < seg_r + s.radius:
                dmg = s.damage or state.shot_damage
                s.kill()
                spawn_hit_effect(int(seg_pos.x), int(seg_pos.y))
                if state.current_boss.take_damage(dmg):
                    kill_boss(state, groups)
                break


# ---------------------------------------------------------------------------
# Missile collisions
# ---------------------------------------------------------------------------

def handle_missile_enemies(state, groups):
    for m in list(groups['missiles']):
        for a in list(groups['asteroids']):
            if m.alive() and a.alive() and m.position.distance_to(a.position) < m.radius + a.radius:
                dmg = max(7, (max(20, 4 * state.level) + (state.missile_stacks - 1) * 5) // 3)
                if a.take_damage(dmg): state.score += kill_asteroid(a)
                spawn_explosion(m.position.x, m.position.y, 15)
                m.kill()
                break
        for e in list(groups['enemies']):
            if m.alive() and e.alive() and m.position.distance_to(e.position) < m.radius + e.radius:
                dmg = max(7, (max(20, 4 * state.level) + (state.missile_stacks - 1) * 5) // 3)
                if e.take_damage(dmg): state.score += kill_enemy(e)
                spawn_explosion(m.position.x, m.position.y, 15)
                m.kill()
                break


def handle_missile_boss(state, groups):
    if not (state.boss_active and state.current_boss is not None):
        return
    for m in list(groups['missiles']):
        if not m.alive():
            continue
        for seg_pos, seg_r in state.current_boss.get_segments():
            if seg_pos.distance_to(m.position) < seg_r + m.radius:
                dmg = max(7, (max(20, 4 * state.level) + (state.missile_stacks - 1) * 5) // 3)
                spawn_explosion(m.position.x, m.position.y, 15)
                m.kill()
                if state.current_boss.take_damage(dmg):
                    kill_boss(state, groups)
                break


# ---------------------------------------------------------------------------
# Area damage (blobs, plow)
# ---------------------------------------------------------------------------

def handle_blob_damage(state, groups, dt):
    BLOB_HIT_COOLDOWN = 0.5
    for blob in list(groups['fire_blobs']):
        if blob.damage_timer >= 1.0:
            blob.damage_timer -= 1.0
            bdmg = int(blob.damage_per_second)
            for a in list(groups['asteroids']):
                if blob.alive() and a.alive() and blob.position.distance_to(a.position) < blob.radius + a.radius:
                    if state.game_time - state.blob_damage_cooldowns.get(id(a), -999) >= BLOB_HIT_COOLDOWN:
                        state.blob_damage_cooldowns[id(a)] = state.game_time
                        if a.take_damage(bdmg): state.score += kill_asteroid(a)
            for e in list(groups['enemies']):
                if blob.alive() and e.alive() and blob.position.distance_to(e.position) < blob.radius + e.radius:
                    if state.game_time - state.blob_damage_cooldowns.get(id(e), -999) >= BLOB_HIT_COOLDOWN:
                        state.blob_damage_cooldowns[id(e)] = state.game_time
                        if e.take_damage(bdmg): state.score += kill_enemy(e)


def handle_plow(state, player, groups):
    # plow_timer and plow_invincibility_timer are incremented in the main loop
    if state.plow_stacks == 0 or state.plow_timer < state.plow_cooldown:
        return
    forward  = pygame.Vector2(0, 1).rotate(player.rotation)
    nose     = player.position + forward * (PLAYER_RADIUS * 0.9)
    PLOW_R   = 30
    plow_dmg = max(35, state.plow_stacks * 5 * state.level)
    plow_hit = False
    for a in list(groups['asteroids']):
        if a.alive() and not plow_hit and nose.distance_to(a.position) < PLOW_R + a.radius:
            state.plow_timer = 0.0
            plow_hit = True
            state.plow_invincibility_timer = 0.5
            if a.take_damage(plow_dmg): state.score += kill_asteroid(a)
            else: spawn_hit_effect(nose.x, nose.y)
    for e in list(groups['enemies']):
        if e.alive() and not plow_hit and nose.distance_to(e.position) < PLOW_R + e.radius:
            state.plow_timer = 0.0
            plow_hit = True
            state.plow_invincibility_timer = 0.5
            if e.take_damage(plow_dmg): state.score += kill_enemy(e)
            else: spawn_hit_effect(nose.x, nose.y)


# ---------------------------------------------------------------------------
# Defensive collisions (shield, player damage)
# ---------------------------------------------------------------------------

def handle_shield(state, player, groups):
    if not state.shield_active:
        return
    SHIELD_R = PLAYER_RADIUS + 10
    for a in list(groups['asteroids']):
        if a.alive() and a.position.distance_to(player.position) < SHIELD_R + a._full_radius:
            spawn_explosion(a.position.x, a.position.y, a._full_radius)
            XPOrb(a.position.x, a.position.y)
            a.kill()
            state.shield_active        = False
            state.shield_age           = 0.0
            state.shield_recharge_timer = 0.0
            break


def _take_player_hit(state, player):
    """Deduct a life or consume shield. Returns True if player died."""
    log_event("player_hit")
    if state.shield_active:
        state.shield_active        = False
        state.shield_age           = 0.0
        state.shield_recharge_timer = 0.0
        return False
    state.lives           -= 1
    state.life_regen_timer = 0.0
    state.shake_timer      = SHAKE_DURATION
    if state.lives <= 0:
        state.death_active = True
        state.death_timer  = 0.0
        state.death_pos    = pygame.Vector2(player.position)
        player.kill()
        spawn_explosion(state.death_pos.x, state.death_pos.y, 60)
        return True
    player.invincibility_timer = INVINCIBILITY_TIME
    return False


def handle_player_damage(state, player, groups):
    if player.invincibility_timer > 0 or state.plow_invincibility_timer > 0:
        return

    # boss touch
    if state.boss_active and state.current_boss is not None:
        touching = any(
            seg_pos.distance_to(player.position) < seg_r + player.radius
            for seg_pos, seg_r in state.current_boss.get_segments()
        )
        if touching:
            _take_player_hit(state, player)
            return

    # asteroid / enemy touch
    for a in list(groups['asteroids']) + list(groups['enemies']):
        if a.collides_with(player):
            _take_player_hit(state, player)
            break
