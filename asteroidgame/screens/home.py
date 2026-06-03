import pygame
from ..constants import SCREEN_WIDTH, SCREEN_HEIGHT

_images = None


def _load():
    global _images
    if _images is not None:
        return _images

    _images = {
        "bg":    pygame.image.load("assets/images/home/background.png").convert_alpha(),
        "moon":  pygame.image.load("assets/images/home/moon.png").convert_alpha(),
        "ast_l": pygame.image.load("assets/images/home/asteroid_left.png").convert_alpha(),
        "ast_m": pygame.image.load("assets/images/home/asteroid_middle.png").convert_alpha(),
        "ast_r": pygame.image.load("assets/images/home/asteroid_right.png").convert_alpha(),
        "ship":  pygame.image.load("assets/images/home/ship.png").convert_alpha(),
        "title": pygame.image.load("assets/images/home/title.png").convert_alpha(),
        "start": pygame.image.load("assets/images/home/start_button.png").convert_alpha(),
    }

    start_hover = _images["start"].copy()
    bright = pygame.Surface(start_hover.get_size(), pygame.SRCALPHA)
    bright.fill((60, 60, 60, 0))
    start_hover.blit(bright, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
    _images["start_hover"] = start_hover

    return _images


def run(screen, clock) -> str:
    imgs = _load()
    cx, cy = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2

    def blit_parallax(img, rate):
        screen.blit(img, ((mouse_x - cx) * rate, (mouse_y - cy) * rate))

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return "quit"
            if event.type == pygame.MOUSEBUTTONDOWN:
                x, y = event.pos
                if imgs["start"].get_at((x, y))[3] > 128:
                    return "game"

        mouse_x, mouse_y = pygame.mouse.get_pos()
        hovering = imgs["start"].get_at((mouse_x, mouse_y))[3] > 128

        screen.fill("black")
        screen.blit(imgs["bg"], (0, 0))
        screen.blit(imgs["moon"], (0, 0))
        blit_parallax(imgs["ast_l"], 0.02)
        blit_parallax(imgs["ast_m"], 0.05)
        blit_parallax(imgs["ast_r"], 0.035)
        blit_parallax(imgs["ship"], 0.03)
        screen.blit(imgs["title"], (0, 0))
        screen.blit(imgs["start_hover"] if hovering else imgs["start"], (0, 0))
        pygame.display.flip()
        clock.tick(60)
