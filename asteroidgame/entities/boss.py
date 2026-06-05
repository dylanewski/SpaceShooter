import math
import random
import pygame

from ..constants import SCREEN_WIDTH, SCREEN_HEIGHT

BOSS_MAX_HP      = 700
BOSS_HEAD_R      = 49   # +30% from 38
BOSS_BODY_R      = 34   # +30% from 26
SEGMENT_COUNT    = 9
SEGMENT_SPACING  = 58

# Sprite render sizes — larger than collision radii so segments overlap and hide the chain
BOSS_HEAD_SPRITE_D = 220   # px diameter for head sprite
BOSS_BODY_SPRITE_D = 160   # px diameter for body sprites (> SEGMENT_SPACING to overlap)
ENTRY_SPEED      = 160
MOVE1_SPEED      = 300
GAP_DURATION     = 4.0

# Move 2 – spiral
SPIRAL_APPROACH  = 220   # px/s toward center
SPIRAL_SPEED     = 2.2   # rad/s
SPIRAL_GROW_TIME = 2.0   # s to reach full radius
SPIRAL_RADIUS    = 160
SPIRAL_DURATION  = 5.5   # s of spiraling before exit

# Move 3 – zigzag
ZIGZAG_SPEED     = 280   # px/s horizontal
ZIGZAG_SWEEPS    = 4     # direction reversals before exit
ZIGZAG_EDGE_PAD  = 60    # px from edge before reversing

EXIT_SPEED       = 340   # px/s for exit dashes (moves 2 & 3)


class Boss(pygame.sprite.Sprite):
    containers: tuple

    def __init__(self, x, y, target):
        if hasattr(self, "containers"):
            super().__init__(*self.containers)
        else:
            super().__init__()

        self._spawn_x    = x
        self._settled_y  = y * 0.38
        self._player_ref = target

        self.position = pygame.Vector2(x, 0)
        self.radius   = BOSS_HEAD_R
        self.health   = BOSS_MAX_HP

        self._angle       = 0.0
        self._wobble_time = 0.0

        self._move1_dir   = pygame.Vector2(0, 1)

        # exit-detection shared state
        self._exit_edge  = None    # "top" | "bottom" | "left" | "right"
        self._exit_armed = False   # True once head has crossed its exit edge

        # move2 sub-phase
        self._m2_phase    = "approach"
        self._m2_spiral_t = 0.0

        # move3 sub-phase
        self._m3_phase   = "sweep"
        self._m3_dir     = 1       # +1 right, -1 left
        self._m3_sweeps  = 0
        self._m3_exit_v  = pygame.Vector2(0, -1)

        self.current_move    = 0
        self._last_move      = 0
        self._state          = "entering"
        self._timer          = 0.0
        self._exit_check_idx = -1

        self._reset_to_top()
        self._spr_head, self._spr_body = self._load_sprites()

    # ------------------------------------------------------------------ #
    @staticmethod
    def _load_sprites():
        d_head = BOSS_HEAD_R * 2
        d_body = BOSS_BODY_R * 2
        try:
            head = pygame.transform.scale(
                pygame.image.load("assets/images/game/Centipedehead.png").convert_alpha(),
                (BOSS_HEAD_SPRITE_D, BOSS_HEAD_SPRITE_D),
            )
            b1 = pygame.transform.scale(
                pygame.image.load("assets/images/game/centipedebody1.png").convert_alpha(),
                (BOSS_BODY_SPRITE_D, BOSS_BODY_SPRITE_D),
            )
            b2 = pygame.transform.scale(
                pygame.image.load("assets/images/game/centipedebody2.png").convert_alpha(),
                (BOSS_BODY_SPRITE_D, BOSS_BODY_SPRITE_D),
            )
            return head, [b1, b2]
        except Exception:
            return None, [None, None]

    # ------------------------------------------------------------------ #
    def _reset_to_top(self):
        start_y = -BOSS_HEAD_R - 20
        self._head = pygame.Vector2(self._spawn_x, start_y)
        self._body = [
            pygame.Vector2(self._spawn_x, start_y - (i + 1) * SEGMENT_SPACING)
            for i in range(SEGMENT_COUNT)
        ]

    def _enter_gap(self):
        self._state       = "gap"
        self._timer       = 0.0
        self.current_move = 0

    def _pick_next_move(self):
        choices = [m for m in (1, 2, 3) if m != self._last_move]
        self._last_move   = self.current_move
        self.current_move = random.choice(choices)
        self._state       = f"move{self.current_move}"
        self._timer       = 0.0
        self._exit_edge      = None
        self._exit_armed     = False
        self._exit_check_idx = -1

        if self.current_move == 1:
            if self._player_ref and self._player_ref.alive():
                to_p = self._player_ref.position - self._head
                self._move1_dir = to_p.normalize() if to_p.length() > 0 else pygame.Vector2(0, 1)
            else:
                self._move1_dir = pygame.Vector2(0, 1)

        elif self.current_move == 2:
            self._m2_phase    = "approach"
            self._m2_spiral_t = 0.0

        elif self.current_move == 3:
            self._m3_phase  = "sweep"
            self._m3_dir    = 1
            self._m3_sweeps = 0

    # ------------------------------------------------------------------ #
    def _arm_exit(self, margin=150):
        """
        Record which edge the head crossed and snapshot the last body segment
        that was still visually on-screen at that moment.
        Returns True once armed; short-circuits on subsequent calls.
        """
        if self._exit_armed:
            return True
        h = self._head
        if   h.x < -margin:                self._exit_edge = "left"
        elif h.x > SCREEN_WIDTH  + margin: self._exit_edge = "right"
        elif h.y < -margin:                self._exit_edge = "top"
        elif h.y > SCREEN_HEIGHT + margin: self._exit_edge = "bottom"
        else:
            return False
        self._exit_armed = True
        # find the tail-most segment still inside the visible screen
        self._exit_check_idx = -1
        for i in range(len(self._body) - 1, -1, -1):
            s = self._body[i]
            if 0 <= s.x <= SCREEN_WIDTH and 0 <= s.y <= SCREEN_HEIGHT:
                self._exit_check_idx = i
                break
        return True

    def _body_cleared(self, margin=150):
        """
        Wait for the snapshotted tail segment to cross the same edge as the head.
        Returns True immediately if no segment was on-screen when the head exited.
        """
        if self._exit_check_idx < 0:
            return True
        s = self._body[self._exit_check_idx]
        if self._exit_edge == "left":   return s.x < -margin
        if self._exit_edge == "right":  return s.x > SCREEN_WIDTH  + margin
        if self._exit_edge == "top":    return s.y < -margin
        if self._exit_edge == "bottom": return s.y > SCREEN_HEIGHT + margin
        return False

    # ------------------------------------------------------------------ #
    def get_segments(self):
        yield pygame.Vector2(self._head), BOSS_HEAD_R
        for pos in self._body:
            yield pygame.Vector2(pos), BOSS_BODY_R

    def take_damage(self, amount: int) -> bool:
        self.health -= amount
        return self.health <= 0

    # ------------------------------------------------------------------ #
    def update(self, dt: float) -> None:
        self._angle += 40 * dt

        # ---- ENTERING ----
        if self._state == "entering":
            target = pygame.Vector2(self._spawn_x, self._settled_y)
            to_t   = target - self._head
            step   = ENTRY_SPEED * dt
            if to_t.length() <= step:
                self._head = pygame.Vector2(target)
                self._enter_gap()
            else:
                self._head += to_t.normalize() * step

        # ---- GAP (idle wobble) ----
        elif self._state == "gap":
            self._timer       += dt
            self._wobble_time += dt
            ox = math.sin(self._wobble_time * 0.7) * 18
            self._head.x = self._spawn_x + ox
            if self._timer >= GAP_DURATION:
                self._pick_next_move()

        # ---- MOVE 1: dash toward player → off screen → re-enter ----
        elif self._state == "move1":
            self._head += self._move1_dir * MOVE1_SPEED * dt
            if self._arm_exit() and self._body_cleared():
                self._reset_to_top()
                self._state = "entering"

        # ---- MOVE 2: approach center → spiral → fly up → re-enter ----
        elif self._state == "move2":
            self._timer += dt
            cx, cy = SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2

            if self._m2_phase == "approach":
                target = pygame.Vector2(cx, cy)
                to_t   = target - self._head
                step   = SPIRAL_APPROACH * dt
                if to_t.length() <= step:
                    self._head        = pygame.Vector2(target)
                    self._m2_phase    = "spiral"
                    self._m2_spiral_t = 0.0
                else:
                    self._head += to_t.normalize() * step

            elif self._m2_phase == "spiral":
                self._m2_spiral_t += dt
                t     = self._m2_spiral_t
                r     = SPIRAL_RADIUS * min(1.0, t / SPIRAL_GROW_TIME)
                theta = SPIRAL_SPEED * t
                self._head.x = cx + r * math.cos(theta)
                self._head.y = cy + r * math.sin(theta)
                if self._m2_spiral_t >= SPIRAL_DURATION:
                    self._m2_phase       = "exit"
                    self._exit_edge      = None
                    self._exit_armed     = False
                    self._exit_check_idx = -1

            elif self._m2_phase == "exit":
                self._head.y -= EXIT_SPEED * dt
                if self._arm_exit() and self._body_cleared():
                    self._reset_to_top()
                    self._state = "entering"

        # ---- MOVE 3: zigzag across screen → shoot off → re-enter ----
        elif self._state == "move3":
            self._timer += dt

            if self._m3_phase == "sweep":
                self._head.x += self._m3_dir * ZIGZAG_SPEED * dt

                # slow drift toward player's y
                if self._player_ref and self._player_ref.alive():
                    ty = self._player_ref.position.y
                else:
                    ty = SCREEN_HEIGHT / 2
                self._head.y += (ty - self._head.y) * dt * 0.6

                # bounce off edges
                if self._m3_dir > 0 and self._head.x >= SCREEN_WIDTH - ZIGZAG_EDGE_PAD:
                    self._head.x = SCREEN_WIDTH - ZIGZAG_EDGE_PAD
                    self._m3_dir = -1
                    self._m3_sweeps += 1
                elif self._m3_dir < 0 and self._head.x <= ZIGZAG_EDGE_PAD:
                    self._head.x = ZIGZAG_EDGE_PAD
                    self._m3_dir = 1
                    self._m3_sweeps += 1

                if self._m3_sweeps >= ZIGZAG_SWEEPS:
                    self._m3_phase   = "exit"
                    # shoot off in current horizontal direction + slightly up
                    self._m3_exit_v      = pygame.Vector2(self._m3_dir * 0.8, -0.6).normalize()
                    self._exit_edge      = None
                    self._exit_armed     = False
                    self._exit_check_idx = -1

            elif self._m3_phase == "exit":
                self._head += self._m3_exit_v * EXIT_SPEED * dt
                if self._arm_exit() and self._body_cleared():
                    self._reset_to_top()
                    self._state = "entering"

        # ---- chain physics ----
        prev = self._head
        for i in range(len(self._body)):
            to_prev = prev - self._body[i]
            dist    = to_prev.length()
            if dist > SEGMENT_SPACING:
                self._body[i] += to_prev.normalize() * (dist - SEGMENT_SPACING)
            prev = self._body[i]

        self.position = pygame.Vector2(self._head)

    # ------------------------------------------------------------------ #
    @staticmethod
    def _blit_rotated(screen, spr, pos, angle_deg):
        rotated = pygame.transform.rotate(spr, angle_deg)
        rect    = rotated.get_rect(center=(int(pos.x), int(pos.y)))
        screen.blit(rotated, rect)

    def draw(self, screen):
        all_pos = [self._head] + self._body

        # connector lines drawn first (behind all sprites)
        for i in range(len(all_pos) - 1):
            pygame.draw.line(
                screen, (80, 5, 5),
                (int(all_pos[i].x),     int(all_pos[i].y)),
                (int(all_pos[i + 1].x), int(all_pos[i + 1].y)),
                10,
            )

        # body segments — draw tail-first so head-adjacent segments sit on top
        for i in range(len(self._body) - 1, -1, -1):
            pos  = self._body[i]
            prev = self._head if i == 0 else self._body[i - 1]
            d    = prev - pos
            # +90 because sprites are drawn pointing down at 0°
            angle = (math.degrees(math.atan2(-d.y, d.x)) + 90) if d.length() > 0 else 0

            spr = self._spr_body[i % 2]
            if spr:
                self._blit_rotated(screen, spr, pos, angle)
            else:
                cx, cy = int(pos.x), int(pos.y)
                pygame.draw.circle(screen, (120, 8, 8),   (cx, cy), BOSS_BODY_R)
                pygame.draw.circle(screen, (220, 50, 50), (cx, cy), BOSS_BODY_R, 2)

        # head — rotates to face direction of travel.
        # +90 because the sprite is drawn pointing down at 0°.
        d_head = self._head - self._body[0]
        h_angle = (math.degrees(math.atan2(-d_head.y, d_head.x)) + 90) if d_head.length() > 0 else 0
        if self._spr_head:
            self._blit_rotated(screen, self._spr_head, self._head, h_angle)
        else:
            hx, hy = int(self._head.x), int(self._head.y)
            pygame.draw.circle(screen, (160, 10, 10), (hx, hy), BOSS_HEAD_R)
            pygame.draw.circle(screen, (255, 70, 70),  (hx, hy), BOSS_HEAD_R, 3)
