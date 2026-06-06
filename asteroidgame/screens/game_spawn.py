import random
import pygame

from ..constants import SCREEN_WIDTH, SCREEN_HEIGHT
from ..entities.enemy import Enemy, ENEMY_MAX_HEALTH
from ..entities.centibomb import Centibomb, CENTIBOMB_HEALTH
from ..entities.xpstar import XPStar


CENTIBOMB_SPAWN_INTERVAL = 25.0
SHOOTER_SPAWN_INTERVAL   = 35.0


def handle_enemy_spawn(state, groups, cx, cy, dt):
    if state.game_time < 60.0 or state.boss_intro_active or state.boss_active:
        return
    state.enemy_spawn_timer += dt
    if state.enemy_spawn_timer >= state.enemy_spawn_rate:
        state.enemy_spawn_timer = 0.0
        SPAWN_MARGIN = 160
        INNER_PAD    = 100
        edge = random.choice([
            pygame.Vector2(-SPAWN_MARGIN,               random.uniform(0, 1) * SCREEN_HEIGHT),
            pygame.Vector2(SCREEN_WIDTH + SPAWN_MARGIN,  random.uniform(0, 1) * SCREEN_HEIGHT),
            pygame.Vector2(random.uniform(0, 1) * SCREEN_WIDTH, -SPAWN_MARGIN),
            pygame.Vector2(random.uniform(0, 1) * SCREEN_WIDTH,  SCREEN_HEIGHT + SPAWN_MARGIN),
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


def handle_centibomb_spawn(state, groups, cx, cy, dt):
    if state.game_time < 120.0 or state.boss_intro_active or state.boss_active:
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


def handle_shooter_spawn(state, player, groups, cx, cy, dt):
    if state.game_phase < 2 or state.boss_intro_active or state.boss_active:
        return
    if (state.game_time - state.spawn_ramp_offset) < 60.0:
        return
    state.shooter_spawn_timer += dt
    if state.shooter_spawn_timer < SHOOTER_SPAWN_INTERVAL:
        return
    state.shooter_spawn_timer = 0.0
    from ..entities.shooter import Shooter, SHOOTER_MAX_HEALTH
    SPAWN_MARGIN = 160
    edge = random.choice([
        pygame.Vector2(-SPAWN_MARGIN,               random.uniform(0, 1) * SCREEN_HEIGHT),
        pygame.Vector2(SCREEN_WIDTH + SPAWN_MARGIN,  random.uniform(0, 1) * SCREEN_HEIGHT),
        pygame.Vector2(random.uniform(0, 1) * SCREEN_WIDTH, -SPAWN_MARGIN),
        pygame.Vector2(random.uniform(0, 1) * SCREEN_WIDTH,  SCREEN_HEIGHT + SPAWN_MARGIN),
    ])
    s = Shooter(edge.x, edge.y, player)
    s.health = int(SHOOTER_MAX_HEALTH * (1.0 + int(state.game_time // 60) * 0.10))


def handle_mine_drop(state, player, groups, dt):
    if state.mine_stacks == 0:
        return
    state.mine_timer += dt
    if state.mine_timer >= state.mine_cooldown:
        state.mine_timer = 0.0
        from ..entities.mine import Mine
        dmg = int(state.shot_damage * (3.0 + (state.mine_stacks - 1) * 0.5))
        Mine(player.position.x, player.position.y, dmg)
