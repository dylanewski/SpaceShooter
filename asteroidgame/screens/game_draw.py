import math
import random
import pygame

from ..constants import SCREEN_WIDTH, SCREEN_HEIGHT, PLAYER_RADIUS
from ..ui import draw_xp_bar, draw_lives, draw_button
from ..entities.boss import BOSS_MAX_HP
from .game_state import SHAKE_DURATION, SHAKE_INTENSITY, PULSE_RADIUS

_combo_font = None

def _get_combo_font():
    global _combo_font
    if _combo_font is None:
        _combo_font = pygame.font.Font("assets/fonts/Pixelout Personal Use Only.ttf", 52)
    return _combo_font


# ---------------------------------------------------------------------------
# Main draw entry point
# ---------------------------------------------------------------------------

def draw_frame(game_surf, screen, state, player, groups, surfs, fonts, ui, dt):
    """Draw everything for one frame onto game_surf, then composite to screen."""
    game_surf.fill("black")

    _draw_missiles_vortexes_blobs(game_surf, groups)
    _draw_particles_and_sprites(game_surf, groups)
    _draw_player_attachments(game_surf, state, player)
    _draw_boss(game_surf, state)
    _draw_shield(game_surf, state, player, surfs['shield'])
    _draw_explosion_rings(game_surf, state, surfs['exp'], dt)
    _draw_pulse_ring(game_surf, state, player, surfs['pulse'], dt)
    _draw_laser_beam(game_surf, state, surfs['laser'], dt)
    _draw_bolt_visuals(game_surf, state, dt)
    _draw_boss_ui(game_surf, state, ui['cx'], fonts['main'], ui['boss_excl_image'], dt)
    _draw_hud(game_surf, state, player, fonts, ui)

    if state.shake_timer > 0:
        state.shake_timer = max(0.0, state.shake_timer - dt)
        intensity = int(SHAKE_INTENSITY * state.shake_timer / SHAKE_DURATION)
        ox, oy    = random.randint(-intensity, intensity), random.randint(-intensity, intensity)
    else:
        ox, oy = 0, 0

    screen.fill("black")
    screen.blit(game_surf, (ox, oy))


def draw_death_frame(game_surf, screen, state, groups, surfs, dt):
    """Draw the death animation (replaces normal frame during death sequence)."""
    from ..entities.particle import Particle
    game_surf.fill("black")
    state.death_timer += dt
    for p in list(groups['particles']):
        p.update(dt)
    for d in groups['drawable']:
        d.draw(game_surf)
    for p in groups['particles']:
        p.draw(game_surf)
    for delay, max_r, color in [
        (0.00, 130, (255,  60,   0)),
        (0.12,  90, (255, 180,   0)),
        (0.25,  55, (255, 255, 180)),
    ]:
        ring_t = max(0.0, state.death_timer - delay)
        if ring_t > 0:
            rt    = min(1.0, ring_t / 0.55)
            r     = max(1, int(max_r * rt))
            alpha = int(255 * (1 - rt))
            surfs['exp'].fill((0, 0, 0, 0))
            pygame.draw.circle(surfs['exp'], (*color, alpha),
                               (int(state.death_pos.x), int(state.death_pos.y)), r, 4)
            game_surf.blit(surfs['exp'], (0, 0))
    screen.fill("black")
    screen.blit(game_surf, (0, 0))


# ---------------------------------------------------------------------------
# Entity layers
# ---------------------------------------------------------------------------

def _draw_missiles_vortexes_blobs(surf, groups):
    for m in groups['missiles']:
        m.draw(surf)
    for v in groups['vortexes']:
        v.draw(surf)
    for blob in groups['fire_blobs']:
        blob.draw(surf)


def _draw_particles_and_sprites(surf, groups):
    for p in groups['particles']:
        p.draw(surf)
    for d in groups['drawable']:
        d.draw(surf)


def _draw_player_attachments(surf, state, player):
    if state.plow_stacks > 0 and state.plow_image is not None:
        forward      = pygame.Vector2(0, 1).rotate(player.rotation)
        nose         = player.position + forward * (PLAYER_RADIUS * 0.9)
        rotated_plow = pygame.transform.rotate(state.plow_image, -player.rotation + 180)
        if state.plow_timer < state.plow_cooldown:
            mask = pygame.Surface(rotated_plow.get_size(), pygame.SRCALPHA)
            mask.fill((255, 255, 255, 80))
            rotated_plow.blit(mask, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        surf.blit(rotated_plow, rotated_plow.get_rect(center=(int(nose.x), int(nose.y))))

    if state.buddy_stacks > 0 and state.buddy_image is not None and state.buddy_delayed_pos is not None:
        rotated_buddy = pygame.transform.rotate(state.buddy_image, -state.buddy_delayed_rot + 180)
        surf.blit(rotated_buddy, rotated_buddy.get_rect(
            center=(int(state.buddy_delayed_pos.x), int(state.buddy_delayed_pos.y))))


def _draw_boss(surf, state):
    if state.boss_active and state.current_boss is not None:
        state.current_boss.draw(surf)


def _draw_shield(surf, state, player, shield_surf):
    if not state.shield_active:
        return
    SHIELD_R = PLAYER_RADIUS + 10
    sz       = SHIELD_R * 2 + 6
    center   = (sz // 2, sz // 2)
    alpha    = int(abs(math.sin(state.shield_age * 3)) * 255)
    shield_surf.fill((0, 0, 0, 0))
    pygame.draw.circle(shield_surf, (100, 150, 255, alpha), center, SHIELD_R, 3)
    surf.blit(shield_surf, shield_surf.get_rect(center=(int(player.position.x), int(player.position.y))))


def _draw_explosion_rings(surf, state, exp_surf, dt):
    next_exp = []
    for ev in state.explosion_visuals:
        ev[3] += dt
        if ev[3] < 0.35:
            next_exp.append(ev)
            t     = ev[3] / 0.35
            r     = max(1, int(ev[2] * t))
            alpha = int(230 * (1 - t))
            exp_surf.fill((0, 0, 0, 0))
            pygame.draw.circle(exp_surf, (255, 130, 0, alpha),          (int(ev[0]), int(ev[1])), r, 4)
            pygame.draw.circle(exp_surf, (255, 230, 80, min(255, alpha + 50)), (int(ev[0]), int(ev[1])), max(1, r - 5), 2)
            surf.blit(exp_surf, (0, 0))
    state.explosion_visuals[:] = next_exp


def _draw_pulse_ring(surf, state, player, pulse_surf, dt):
    if state.pulse_visual_age >= 1.0:
        return
    state.pulse_visual_age += dt / 0.5
    t     = min(1.0, state.pulse_visual_age)
    alpha = int(220 * (1 - t))
    pulse_surf.fill((0, 0, 0, 0))
    pygame.draw.circle(pulse_surf, (100, 180, 255, alpha),
                       (int(player.position.x), int(player.position.y)), int(PULSE_RADIUS * t), 4)
    surf.blit(pulse_surf, (0, 0))


def _draw_laser_beam(surf, state, laser_surf, dt):
    if state.laser_visual_age >= 1.0 or state.laser_origin is None:
        return
    state.laser_visual_age += dt / 0.25
    t     = min(1.0, state.laser_visual_age)
    alpha = int(220 * (1 - t))
    end   = state.laser_origin + state.laser_direction * 2000
    beam_w = 2 + state.laser_stacks * 2
    core_w = state.laser_stacks
    laser_surf.fill((0, 0, 0, 0))
    pygame.draw.line(laser_surf, (180, 220, 255, alpha),
                     (int(state.laser_origin.x), int(state.laser_origin.y)),
                     (int(end.x), int(end.y)), beam_w)
    pygame.draw.line(laser_surf, (255, 255, 255, min(255, alpha + 60)),
                     (int(state.laser_origin.x), int(state.laser_origin.y)),
                     (int(end.x), int(end.y)), core_w)
    surf.blit(laser_surf, (0, 0))


def _draw_bolt_visuals(surf, state, dt):
    next_bolts = []
    for bv in state.bolt_visuals:
        bv['age'] += dt
        if bv['age'] < bv['max_age']:
            next_bolts.append(bv)
            t    = 1.0 - bv['age'] / bv['max_age']
            pts  = [(int(x), int(y)) for x, y in bv['pts']]
            glow = (int(40 * t), int(100 * t), int(255 * t))
            core = (int(200 * t), int(230 * t), int(255 * t))
            for i in range(len(pts) - 1):
                pygame.draw.line(surf, glow, pts[i], pts[i + 1], 4)
            for i in range(len(pts) - 1):
                pygame.draw.line(surf, core, pts[i], pts[i + 1], 2)
    state.bolt_visuals[:] = next_bolts


# ---------------------------------------------------------------------------
# HUD elements
# ---------------------------------------------------------------------------

def _draw_boss_ui(surf, state, cx, font, boss_excl_image, dt):
    if state.boss_active and state.current_boss is not None:
        hp_frac = max(0.0, state.current_boss.health / BOSS_MAX_HP)

        # ghost bar lags behind real HP — drains slowly so the gap is visible
        if state.boss_hp_visual > hp_frac:
            state.boss_hp_visual = max(hp_frac, state.boss_hp_visual - dt * 0.12)
        else:
            state.boss_hp_visual = hp_frac

        BAR_W, BAR_H = 420, 18
        bx = cx - BAR_W // 2
        by = SCREEN_HEIGHT - 50

        pygame.draw.rect(surf, (20, 0, 0),    (bx, by, BAR_W, BAR_H))                             # background
        pygame.draw.rect(surf, (230, 80, 80), (bx, by, int(BAR_W * state.boss_hp_visual), BAR_H))  # ghost (light salmon — visible gap)
        pygame.draw.rect(surf, (200, 20, 20), (bx, by, int(BAR_W * hp_frac), BAR_H))              # real HP (deep vivid red)
        pygame.draw.rect(surf, (220, 30, 30), (bx, by, BAR_W, BAR_H), 2)                           # border

        _BOSS_NAMES = {1: "Mechipede"}
        boss_name = _BOSS_NAMES.get(state.game_phase, "BOSS")
        blbl = font.render(boss_name, True, (220, 30, 30))
        surf.blit(blbl, blbl.get_rect(midbottom=(cx, by - 4)))

    if state.boss_intro_active and int(state.boss_intro_timer * 2) % 2 == 0:
        if boss_excl_image is not None:
            surf.blit(boss_excl_image, boss_excl_image.get_rect(center=(cx, SCREEN_HEIGHT // 2)))


def _draw_hud(surf, state, player, fonts, ui):
    font      = fonts['main']
    icon_font = fonts['icon']
    cx        = ui['cx']
    skull_img = ui['skull_image']
    dt        = ui.get('dt', 0.016)

    # danger border when low health
    if state.lives == 1:
        pulse = (math.sin(state.game_time * 2.5) + 1) / 2
        bw    = 22
        da    = int(40 + pulse * 130)
        danger_surf = ui['danger']
        danger_surf.fill((0, 0, 0, 0))
        pygame.draw.rect(danger_surf, (220, 0, 0, da), (0, 0, SCREEN_WIDTH, bw))
        pygame.draw.rect(danger_surf, (220, 0, 0, da), (0, SCREEN_HEIGHT - bw, SCREEN_WIDTH, bw))
        pygame.draw.rect(danger_surf, (220, 0, 0, da), (0, 0, bw, SCREEN_HEIGHT))
        pygame.draw.rect(danger_surf, (220, 0, 0, da), (SCREEN_WIDTH - bw, 0, bw, SCREEN_HEIGHT))
        surf.blit(danger_surf, (0, 0))
        if int(state.game_time * 2) % 2 == 0:
            dtxt = fonts['danger'].render("DANGER", True, (220, 0, 0))
            surf.blit(dtxt, dtxt.get_rect(center=(cx, 72)))

    surf.blit(font.render(f"{state.score}", True, "white"), (10, 10))
    draw_xp_bar(surf, font, cx, state.level, state.xp, state.xp_to_next, state.xp_visual)
    draw_lives(surf, state.lives, state.life_regen_timer / state.life_regen_time)

    # ability icons
    icon_items = []
    if state.pulse_stacks > 0:
        icon_items.append(("PW", state.pulse_timer >= state.pulse_cooldown,
                            min(1.0, state.pulse_timer / state.pulse_cooldown)))
    if state.shield_stacks > 0:
        frac = 1.0 if state.shield_active else min(1.0, state.shield_recharge_timer / state.shield_recharge_time)
        icon_items.append(("SH", state.shield_active, frac))
    if state.vortex_stacks > 0:
        icon_items.append(("VF", state.vortex_timer >= state.vortex_cooldown,
                            min(1.0, state.vortex_timer / state.vortex_cooldown)))
    if state.missile_stacks > 0:
        m_ready = state.missile_timer >= state.missile_cooldown and len(state.missile_queue) == 0
        icon_items.append(("MS", m_ready, min(1.0, state.missile_timer / state.missile_cooldown)))
    if state.laser_stacks > 0:
        icon_items.append(("LZ", state.laser_timer >= state.laser_cooldown,
                            min(1.0, state.laser_timer / state.laser_cooldown)))
    if state.plow_stacks > 0:
        icon_items.append(("PL", state.plow_timer >= state.plow_cooldown,
                            min(1.0, state.plow_timer / state.plow_cooldown)))

    iw, ih, igap = 34, 34, 6
    ix, iy = 12, 55
    for lbl, ready, frac in icon_items:
        fg = (210, 210, 210) if ready else (65, 65, 65)
        pygame.draw.rect(surf, (20, 20, 20), (ix, iy, iw, ih))
        if not ready:
            fill_h = int(ih * frac)
            pygame.draw.rect(surf, (50, 50, 50), (ix, iy + ih - fill_h, iw, fill_h))
        pygame.draw.rect(surf, fg, (ix, iy, iw, ih), 2)
        t = icon_font.render(lbl, True, fg)
        surf.blit(t, t.get_rect(center=(ix + iw // 2, iy + ih // 2)))
        iy += ih + igap

    # boss countdown bar
    bar_w   = 14
    bar_x   = SCREEN_WIDTH - 22
    bar_top = int(SCREEN_HEIGHT * 0.2)
    bar_h   = int((SCREEN_HEIGHT - 30) * 0.7)
    bar_bot = bar_top + bar_h
    if state.boss_active or state.boss_intro_active:
        fill_frac = 1.0
        bar_color = (220, 30, 30)
    else:
        fill_frac = min(1.0, (state.game_time - state.spawn_ramp_offset) / 240.0)
        bar_color = (255, 255, 255)
    fill_h  = int(bar_h * fill_frac)
    skull_x = bar_x + bar_w // 2 - skull_img.get_width() // 2
    skull_y = bar_top - skull_img.get_height() - 2
    surf.blit(skull_img, (skull_x, skull_y))
    pygame.draw.rect(surf, (45, 45, 45),  (bar_x, bar_top, bar_w, bar_h))
    pygame.draw.rect(surf, bar_color,     (bar_x, bar_bot - fill_h, bar_w, fill_h))
    pygame.draw.rect(surf, (120, 120, 120), (bar_x, bar_top, bar_w, bar_h), 1)

    if state.combo_count > 0:
        t     = min(1.0, state.combo_count / 100.0)
        color = (255, int(255 - 35 * t), int(255 * (1 - t)))
        ox, oy = 0, 0
        if state.combo_shake_timer > 0:
            mag = int(7 * state.combo_shake_timer / 0.25)
            ox  = random.randint(-mag, mag)
            oy  = random.randint(-mag, mag)
        combo_txt = _get_combo_font().render(str(state.combo_count), True, color)
        surf.blit(combo_txt, combo_txt.get_rect(
            bottomright=(SCREEN_WIDTH - 20 + ox, SCREEN_HEIGHT - 20 + oy)))


def draw_pause_overlay(screen, state, big_font, fonts, cx, cy, pause_overlay,
                        resume_btn, end_game_btn, pause_home_btn):
    screen.blit(pause_overlay, (0, 0))
    lbl = big_font.render("PAUSED", True, "white")
    screen.blit(lbl, lbl.get_rect(center=(cx, cy - 100)))
    draw_button(screen, fonts['main'], resume_btn,     "Resume")
    draw_button(screen, fonts['main'], end_game_btn,   "End Game")
    draw_button(screen, fonts['main'], pause_home_btn, "Home")
