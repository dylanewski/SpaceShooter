import pygame
from ..asteroid import Asteroid
from ..asteroidfield import AsteroidField
from ..constants import SCREEN_WIDTH, SCREEN_HEIGHT
from ..logger import log_state, log_event
from ..player import Player
from ..shot import Shot
from ..ui import make_button, draw_button


def run(screen, clock, font, big_font) -> tuple[str, int]:
    cx, cy = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2

    pause_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    pause_overlay.fill((0, 0, 0, 160))
    resume_btn   = make_button((cx, cy - 20))
    end_game_btn = make_button((cx, cy + 60))
    pause_home_btn = make_button((cx, cy + 140))

    updatable = pygame.sprite.Group()
    drawable  = pygame.sprite.Group()
    asteroids = pygame.sprite.Group()
    shots     = pygame.sprite.Group()
    Asteroid.containers    = (updatable, drawable, asteroids)
    Player.containers      = (updatable, drawable)
    AsteroidField.containers = (updatable,)
    Shot.containers        = (updatable, drawable, shots)
    AsteroidField()
    player = Player(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)

    score = 0
    score_timer = 0.0
    dt = 0.0
    paused = False

    while True:
        log_state()

        pause_action = None
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit", score
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
            return pause_action, score

        screen.fill("black")

        if not paused:
            dt = clock.tick(60) / 1000
            score_timer += dt
            if score_timer >= 1.0:
                score_timer -= 1.0
                score += 1
            for u in updatable:
                u.update(dt)
            for a in asteroids:
                for s in shots:
                    if a.collides_with(s):
                        log_event("asteroid_shot")
                        a.split()
                        s.kill()
                        score += 1
        else:
            clock.tick(60)

        for d in drawable:
            d.draw(screen)

        score_surface = font.render(f"Score: {score}", True, "white")
        screen.blit(score_surface, (10, 10))

        if paused:
            screen.blit(pause_overlay, (0, 0))
            pause_title = big_font.render("PAUSED", True, "white")
            screen.blit(pause_title, pause_title.get_rect(center=(cx, cy - 100)))
            draw_button(screen, font, resume_btn, "Resume")
            draw_button(screen, font, end_game_btn, "End Game")
            draw_button(screen, font, pause_home_btn, "Home")

        pygame.display.flip()

        if not paused:
            for a in asteroids:
                if a.collides_with(player):
                    log_event("player_hit")
                    return "game_over", score
