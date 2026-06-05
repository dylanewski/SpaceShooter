import random
import pygame

from ..constants import SCREEN_WIDTH, SCREEN_HEIGHT, INVINCIBILITY_TIME, PLAYER_RADIUS, SHOT_RADIUS
from ..entities.shot import Shot
from ..entities.xporb import XPOrb
from ..entities.bigxporb import BigXPOrb
from ..logger import log_event
from .effects import (
    spawn_explosion, spawn_hit_effect, spawn_boss_explosion,
    kill_asteroid, kill_enemy, kill_centibomb, combo_kill,
)
from .game_state import SHAKE_DURATION, RICOCHET_RANGE, EXPLOSION_RADIUS


CRIT_FLASH_DURATION = 0.12


def _roll_crit(crit_chance: int) -> bool:
    return random.randint(1, 100) <= crit_chance


# ---------------------------------------------------------------------------
# Boss kill
# ---------------------------------------------------------------------------

def kill_boss(state, groups):
    if state.current_boss is None:
        return
    for grp in [groups['asteroids'], groups['enemies'], groups['shots'],
                groups['xp_orbs'], groups['xp_stars'], groups['boss_shots']]:
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
            if te.take_damage(splash): state.score += combo_kill(state, kill_enemy, te)
    for tc in list(groups['centibombs']):
        if tc.alive() and tc.position.distance_to(s_pos) < exp_r:
            if tc.take_damage(splash): state.score += combo_kill(state, kill_centibomb, tc)


def _spawn_ricochets(state, groups, s):
    """Fork up to ricochet_stacks new shots from the impact point, inheriting parent properties."""
    parent_dmg   = s.damage if s.damage else state.shot_damage
    ricochet_dmg = max(1, parent_dmg // 2)

    candidates = sorted(
        [t for t in list(groups['asteroids']) + list(groups['enemies']) + list(groups['centibombs'])
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
            is_crit = _roll_crit(state.crit_chance)
            dmg     = (s.damage or state.shot_damage) * (2 if is_crit else 1)
            if is_crit:
                a.crit_flash_timer = CRIT_FLASH_DURATION
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
            is_crit  = _roll_crit(state.crit_chance)
            dmg      = (s.damage or state.shot_damage) * (2 if is_crit else 1)
            if is_crit:
                e.crit_flash_timer = CRIT_FLASH_DURATION
            if state.explosive_stacks > 0 and not s.fragment:
                _apply_explosive(state, groups, s.position, s.radius)
            if s.bounces_left > 0:
                _spawn_ricochets(state, groups, s)
            s.kill()
            if e.take_damage(dmg): state.score += combo_kill(state, kill_enemy, e)
            else: spawn_hit_effect(e.position.x, e.position.y, shot_vel)


def handle_shot_centibomb(state, groups):
    for c in list(groups['centibombs']):
        for s in list(groups['shots']):
            if not (c.alive() and s.alive() and c.collides_with(s)):
                continue
            shot_vel = pygame.Vector2(s.velocity)
            is_crit  = _roll_crit(state.crit_chance)
            dmg      = (s.damage or state.shot_damage) * (2 if is_crit else 1)
            if is_crit:
                c.crit_flash_timer = CRIT_FLASH_DURATION
            if state.explosive_stacks > 0 and not s.fragment:
                _apply_explosive(state, groups, s.position, s.radius)
            if s.bounces_left > 0:
                _spawn_ricochets(state, groups, s)
            s.kill()
            if c.take_damage(dmg): state.score += combo_kill(state, kill_centibomb, c)
            else: spawn_hit_effect(c.position.x, c.position.y, shot_vel)


def handle_shot_boss(state, groups):
    if not (state.boss_active and state.current_boss is not None):
        return
    for s in list(groups['shots']):
        if not s.alive():
            continue
        for seg_pos, seg_r in state.current_boss.get_segments():
            if seg_pos.distance_to(s.position) < seg_r + s.radius:
                is_crit = _roll_crit(state.crit_chance)
                dmg     = (s.damage or state.shot_damage) * (2 if is_crit else 1)
                if is_crit:
                    state.current_boss.crit_flash_timer = CRIT_FLASH_DURATION
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
                if e.take_damage(dmg): state.score += combo_kill(state, kill_enemy, e)
                spawn_explosion(m.position.x, m.position.y, 15)
                m.kill()
                break
        for c in list(groups['centibombs']):
            if m.alive() and c.alive() and m.position.distance_to(c.position) < m.radius + c.radius:
                dmg = max(7, (max(20, 4 * state.level) + (state.missile_stacks - 1) * 5) // 3)
                if c.take_damage(dmg): state.score += combo_kill(state, kill_centibomb, c)
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
    BLOB_TICK = 1.0
    blobs = [b for b in groups['fire_blobs'] if b.alive()]
    if not blobs:
        return

    def _touching(pos, radius):
        for b in blobs:
            if b.position.distance_to(pos) < b.radius + radius:
                return b
        return None

    for a in list(groups['asteroids']):
        if not a.alive(): continue
        b = _touching(a.position, a.radius)
        if b and state.game_time - state.blob_damage_cooldowns.get(id(a), -999) >= BLOB_TICK:
            state.blob_damage_cooldowns[id(a)] = state.game_time
            if a.take_damage(int(b.damage_per_second)): state.score += kill_asteroid(a)

    for e in list(groups['enemies']):
        if not e.alive(): continue
        b = _touching(e.position, e.radius)
        if b and state.game_time - state.blob_damage_cooldowns.get(id(e), -999) >= BLOB_TICK:
            state.blob_damage_cooldowns[id(e)] = state.game_time
            if e.take_damage(int(b.damage_per_second)): state.score += combo_kill(state, kill_enemy, e)

    for c in list(groups['centibombs']):
        if not c.alive(): continue
        b = _touching(c.position, c.radius)
        if b and state.game_time - state.blob_damage_cooldowns.get(id(c), -999) >= BLOB_TICK:
            state.blob_damage_cooldowns[id(c)] = state.game_time
            if c.take_damage(int(b.damage_per_second)): state.score += combo_kill(state, kill_centibomb, c)

    if state.boss_active and state.current_boss is not None:
        boss_key = id(state.current_boss)
        if state.game_time - state.blob_damage_cooldowns.get(boss_key, -999) >= BLOB_TICK:
            for seg_pos, seg_r in state.current_boss.get_segments():
                b = _touching(seg_pos, seg_r)
                if b:
                    state.blob_damage_cooldowns[boss_key] = state.game_time
                    if state.current_boss.take_damage(int(b.damage_per_second)):
                        kill_boss(state, groups)
                    break


def handle_plow(state, player, groups):
    # plow_timer and plow_invincibility_timer are incremented in the main loop
    if state.plow_stacks == 0 or state.plow_timer < state.plow_cooldown:
        return
    forward = pygame.Vector2(0, 1).rotate(player.rotation)
    nose    = player.position + forward * (PLAYER_RADIUS * 0.9)
    PLOW_R  = 30

    # Damage scales with current speed — dash synergy
    vel_factor = max(1.0, player.velocity.length() / max(1.0, player.speed))
    plow_dmg   = int(max(35, state.plow_stacks * 5 * state.level) * vel_factor)

    hit_pos  = None
    plow_hit = False
    for a in list(groups['asteroids']):
        if a.alive() and not plow_hit and nose.distance_to(a.position) < PLOW_R + a.radius:
            state.plow_timer = 0.0
            plow_hit = True
            hit_pos  = pygame.Vector2(a.position)
            state.plow_invincibility_timer = 0.5
            if a.take_damage(plow_dmg): state.score += kill_asteroid(a)
            else: spawn_hit_effect(nose.x, nose.y)
    for e in list(groups['enemies']):
        if e.alive() and not plow_hit and nose.distance_to(e.position) < PLOW_R + e.radius:
            state.plow_timer = 0.0
            plow_hit = True
            hit_pos  = pygame.Vector2(e.position)
            state.plow_invincibility_timer = 0.5
            if e.take_damage(plow_dmg): state.score += combo_kill(state, kill_enemy, e)
            else: spawn_hit_effect(nose.x, nose.y)
    for c in list(groups['centibombs']):
        if c.alive() and not plow_hit and nose.distance_to(c.position) < PLOW_R + c.radius:
            state.plow_timer = 0.0
            plow_hit = True
            hit_pos  = pygame.Vector2(c.position)
            state.plow_invincibility_timer = 0.5
            if c.take_damage(plow_dmg): state.score += combo_kill(state, kill_centibomb, c)
            else: spawn_hit_effect(nose.x, nose.y)

    if plow_hit and hit_pos is not None:
        # Bounce the ship away from the hit object
        away = player.position - hit_pos
        bounce_dir = away.normalize() if away.length() > 0 else -forward
        player.velocity = bounce_dir * (player.speed * 0.65)


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


def handle_boss_shot_player(state, player, groups):
    if player.invincibility_timer > 0 or state.plow_invincibility_timer > 0:
        return
    for s in list(groups['boss_shots']):
        if s.alive() and s.position.distance_to(player.position) < s.radius + player.radius:
            s.kill()
            _take_player_hit(state, player)
            return  # one hit per frame


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
    for a in list(groups['asteroids']) + list(groups['enemies']) + list(groups['centibombs']):
        if a.collides_with(player):
            _take_player_hit(state, player)
            break
