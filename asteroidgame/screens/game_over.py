import pygame
from ..constants import SCREEN_WIDTH, SCREEN_HEIGHT
from ..ui import make_button, draw_button


def run(screen, clock, font, big_font, score) -> str:
    cx, cy = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
    try_again_btn = make_button((cx, cy + 60))
    home_btn = make_button((cx, cy + 140))

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.MOUSEBUTTONDOWN:
                if try_again_btn.collidepoint(event.pos):
                    return "game"
                if home_btn.collidepoint(event.pos):
                    return "home"

        screen.fill("black")
        title = big_font.render("GAME OVER", True, "white")
        final_score = font.render(f"Score: {score}", True, "white")
        screen.blit(title, title.get_rect(center=(cx, cy - 80)))
        screen.blit(final_score, final_score.get_rect(center=(cx, cy - 10)))
        draw_button(screen, font, try_again_btn, "Try Again")
        draw_button(screen, font, home_btn, "Home")
        pygame.display.flip()
        clock.tick(60)
