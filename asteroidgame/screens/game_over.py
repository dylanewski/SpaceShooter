import pygame
from ..constants import SCREEN_WIDTH, SCREEN_HEIGHT
from ..ui import make_button, draw_button


def run(screen, clock, font, big_font, score, highest_combo=0) -> str:
    cx, cy = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
    ui_font = pygame.font.Font("assets/fonts/Symtext.ttf", 36)
    try_again_btn = make_button((cx, cy + 120))
    home_btn      = make_button((cx, cy + 200))

    fade_surf  = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
    fade_surf.fill((0, 0, 0))
    fade_alpha = 255.0

    # pre-render static text
    title_surf  = big_font.render("GAME OVER", True, "white")
    slbl_surf   = ui_font.render("SCORE", True, (160, 160, 160))
    score_surf  = ui_font.render(str(score), True, "white")
    clbl_surf   = ui_font.render("BEST COMBO", True, (160, 160, 160))
    cval_surf   = ui_font.render(f"{highest_combo}x", True, (255, 220, 0))

    while True:
        dt = clock.tick(60) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.MOUSEBUTTONDOWN:
                if try_again_btn.collidepoint(event.pos):
                    return "game"
                if home_btn.collidepoint(event.pos):
                    return "home"

        screen.fill("black")
        screen.blit(title_surf,  title_surf.get_rect(center=(cx, cy - 120)))
        screen.blit(slbl_surf,   slbl_surf.get_rect(center=(cx, cy - 60)))
        screen.blit(score_surf,  score_surf.get_rect(center=(cx, cy - 25)))
        screen.blit(clbl_surf,   clbl_surf.get_rect(center=(cx, cy + 20)))
        screen.blit(cval_surf,   cval_surf.get_rect(center=(cx, cy + 55)))
        draw_button(screen, ui_font, try_again_btn, "Try Again")
        draw_button(screen, ui_font, home_btn, "Home")

        if fade_alpha > 0:
            fade_alpha = max(0.0, fade_alpha - dt * (255 / 0.8))
            fade_surf.set_alpha(int(fade_alpha))
            screen.blit(fade_surf, (0, 0))

        pygame.display.flip()
