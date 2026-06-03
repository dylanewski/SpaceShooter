import pygame
from asteroidgame.asteroid import Asteroid
from asteroidgame.constants import SCREEN_WIDTH, SCREEN_HEIGHT, LINE_WIDTH
from asteroidgame.logger import log_state, log_event
from asteroidgame.player import Player
from asteroidgame.asteroidfield import AsteroidField
from asteroidgame.shot import Shot


def make_button(center, width=220, height=60):
    rect = pygame.Rect(0, 0, width, height)
    rect.center = center
    return rect


def draw_button(screen, font, rect, label):
    pygame.draw.rect(screen, "white", rect, LINE_WIDTH)
    text = font.render(label, True, "white")
    screen.blit(text, text.get_rect(center=rect.center))


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pygame.time.Clock()
    font = pygame.font.Font("assets/fonts/8-bitanco.ttf", 36)
    big_font = pygame.font.Font("assets/fonts/8-bitanco.ttf", 72)

    cx, cy = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2

    home_ship_img = pygame.image.load("assets/images/Transparent Background.png").convert_alpha()
    home_moon_img = pygame.image.load("assets/images/Moon Homescreen.png").convert_alpha()

    pause_overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
    pause_overlay.fill((0, 0, 0, 160))
    resume_btn = make_button((cx, cy - 20))
    end_game_btn = make_button((cx, cy + 60))
    pause_home_btn = make_button((cx, cy + 140))

    while True:
        # HOME SCREEN
        play_btn = make_button((cx, cy + 120))

        while True:
            clicked = False
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if play_btn.collidepoint(event.pos):
                        clicked = True
            if clicked:
                break

            mouse_x, mouse_y = pygame.mouse.get_pos()
            ship_x = cx + (mouse_x - cx) * 0.03
            ship_y = cy + (mouse_y - cy) * 0.03

            screen.fill("black")
            screen.blit(home_moon_img, home_moon_img.get_rect(bottomright=(SCREEN_WIDTH, SCREEN_HEIGHT)))
            screen.blit(home_ship_img, home_ship_img.get_rect(center=(ship_x, ship_y)))
            title = big_font.render("ASTEROIDS", True, "white")
            screen.blit(title, title.get_rect(center=(cx, cy - 130)))
            draw_button(screen, font, play_btn, "Play")
            pygame.display.flip()
            clock.tick(60)

        # RETRY LOOP — iterates on "Try Again", breaks on "Home"
        while True:
            score = 0
            score_timer = 0.0
            dt = 0.0
            paused = False

            updatable = pygame.sprite.Group()
            drawable = pygame.sprite.Group()
            asteroids = pygame.sprite.Group()
            shots = pygame.sprite.Group()
            Asteroid.containers = (updatable, drawable, asteroids)
            Player.containers = (updatable, drawable)
            AsteroidField.containers = (updatable,)
            Shot.containers = (updatable, drawable, shots)
            AsteroidField()
            player = Player(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2)

            # GAME LOOP
            go_home = False
            player_died = False
            while True:
                log_state()

                pause_action = None
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        return
                    if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                        paused = not paused
                    if paused and event.type == pygame.MOUSEBUTTONDOWN:
                        if resume_btn.collidepoint(event.pos):
                            paused = False
                        elif end_game_btn.collidepoint(event.pos):
                            pause_action = "quit"
                        elif pause_home_btn.collidepoint(event.pos):
                            pause_action = "home"

                if pause_action == "quit":
                    return
                if pause_action == "home":
                    go_home = True
                    break

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
                            player_died = True
                            break
                    if player_died:
                        break

            if go_home:
                break  # skip game over, return to home screen

            # GAME OVER SCREEN
            try_again_btn = make_button((cx, cy + 60))
            home_btn = make_button((cx, cy + 140))

            while True:
                clicked = None
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        return
                    if event.type == pygame.MOUSEBUTTONDOWN:
                        if try_again_btn.collidepoint(event.pos):
                            clicked = "retry"
                        elif home_btn.collidepoint(event.pos):
                            clicked = "home"
                if clicked:
                    go_home = clicked == "home"
                    break

                screen.fill("black")
                title = big_font.render("GAME OVER", True, "white")
                final_score = font.render(f"Score: {score}", True, "white")
                screen.blit(title, title.get_rect(center=(cx, cy - 80)))
                screen.blit(final_score, final_score.get_rect(center=(cx, cy - 10)))
                draw_button(screen, font, try_again_btn, "Try Again")
                draw_button(screen, font, home_btn, "Home")
                pygame.display.flip()
                clock.tick(60)

            if go_home:
                break  # exits retry loop → app loop iterates → home screen


if __name__ == "__main__":
    main()
