from collections import deque

from ..constants import MAX_LIVES, LIFE_REGEN_TIME
from ..entities.enemy import ENEMY_SPAWN_RATE_START

# ---------------------------------------------------------------------------
# Shared game-loop constants (formerly scattered locals in run())
# ---------------------------------------------------------------------------
PULSE_RADIUS    = 150
SHAKE_DURATION  = 0.3
SHAKE_INTENSITY = 8
RICOCHET_RANGE  = 200
EXPLOSION_RADIUS = 67
DEATH_DURATION  = 1.6
BUDDY_DISTANCE  = 65


class GameState:
    """All mutable state for one game session."""

    def __init__(self):
        # ---- core timing ----
        self.score          = 0
        self.score_timer    = 0.0
        self.game_time      = 0.0
        self.game_phase     = 1
        self.spawn_ramp_offset = 0.0
        self.shake_timer    = 0.0

        # ---- death sequence ----
        self.death_active = False
        self.death_timer  = 0.0
        self.death_pos    = None

        # ---- boss flow ----
        self.boss_intro_active = False
        self.boss_intro_timer  = 0.0
        self.boss_active       = False
        self.boss_triggered    = False
        self.current_boss      = None
        self.boss_hp_visual    = 1.0   # ghost bar — lags behind real HP

        # ---- player progression ----
        self.xp               = 0
        self.level            = 1
        self.xp_to_next       = 7
        self.level_up_pending = False
        self.xp_visual        = 0.0
        self.lives            = MAX_LIVES
        self.life_regen_time  = LIFE_REGEN_TIME
        self.life_regen_timer = 0.0

        # ---- combo ----
        self.highest_combo      = 0
        self.combo_count        = 0
        self.combo_timer        = 0.0
        self.combo_shake_timer  = 0.0
        self.combo_fade_timer   = 0.0
        self.combo_display_count = 0
        self.combo_hud_particles = []
        self.combo_particle_acc  = 0.0

        # ---- base stats ----
        self.shot_damage   = 10
        self.xp_multiplier = 1.0
        self.crit_chance   = 3

        # ---- upgrade display stacks (no other runtime use) ----
        self.rapid_fire_stacks  = 0
        self.caliber_stacks     = 0
        self.speed_stacks       = 0
        self.quick_regen_stacks = 0
        self.xp_gen_stacks      = 0

        # ---- shield ----
        self.shield_stacks        = 0
        self.shield_active        = False
        self.shield_age           = 0.0
        self.shield_recharge_time  = 30.0
        self.shield_recharge_timer = 0.0

        # ---- pulse wave ----
        self.pulse_stacks    = 0
        self.pulse_cooldown  = 5.0
        self.pulse_timer     = 0.0
        self.pulse_visual_age = 1.0

        # ---- afterburn ----
        self.afterburn_stacks      = 0
        self.afterburn_timer       = 0.0
        self.blob_damage_cooldowns = {}

        # ---- combat modifiers ----
        self.homing_strength        = 0
        self.ricochet_stacks        = 0
        self.explosive_stacks       = 0
        self.bigger_bullets_stacks  = 0
        self.explosion_visuals = []   # list of [x, y, max_r, age]

        # ---- bolt dash ----
        self.bolt_dash_stacks = 0
        self.bolt_visuals     = []   # [{'pts': [...], 'age': float, 'max_age': float}]

        # ---- plow ----
        self.plow_stacks             = 0
        self.plow_cooldown           = 2.0
        self.plow_timer              = 0.0
        self.plow_invincibility_timer = 0.0
        self.plow_image              = None

        # ---- buddy ----
        self.buddy_stacks      = 0
        self.buddy_image       = None
        self.buddy_history     = deque()
        self.buddy_delayed_pos = None
        self.buddy_delayed_rot = 0.0

        # ---- vortex ----
        self.vortex_stacks  = 0
        self.vortex_cooldown = 15.0
        self.vortex_timer   = 0.0

        # ---- missile ----
        self.missile_stacks       = 0
        self.missile_cooldown     = 6.0
        self.missile_timer        = 0.0
        self.missile_queue        = []
        self.missile_launch_timer = 0.0

        # ---- laser ----
        self.laser_stacks    = 0
        self.laser_cooldown  = 8.0
        self.laser_timer     = 0.0
        self.laser_visual_age = 1.0
        self.laser_origin    = None
        self.laser_direction = None

        # ---- mines ----
        self.mine_stacks   = 0
        self.mine_cooldown = 3.6
        self.mine_timer    = 0.0

        # ---- spawn timers ----
        self.particle_timer    = 0.0
        self.enemy_spawn_rate      = ENEMY_SPAWN_RATE_START
        self.enemy_spawn_timer     = 0.0
        self.centibomb_spawn_timer = 0.0
        self.shooter_spawn_timer   = 0.0
        self.xp_star_timer         = 0.0

    # -----------------------------------------------------------------------
    def award_xp(self, amount=1):
        self.xp += max(1, int(amount * self.xp_multiplier))
        if self.xp >= self.xp_to_next:
            self.xp -= self.xp_to_next
            self.level += 1
            self.xp_to_next       = int(self.xp_to_next * 1.2)
            self.level_up_pending = True
