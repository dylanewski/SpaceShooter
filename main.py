import pygame
from asteroidgame.constants import SCREEN_WIDTH, SCREEN_HEIGHT
from asteroidgame.screens import home, game, game_over


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pygame.time.Clock()
    font = pygame.font.Font("assets/fonts/Pixelout Personal Use Only.ttf", 36)
    big_font = pygame.font.Font("assets/fonts/Pixelout Personal Use Only.ttf", 72)

    state = "home"
    score = 0

    while True:
        if state == "home":
            state = home.run(screen, clock)
        elif state == "game":
            state, score = game.run(screen, clock, font, big_font)
        elif state == "game_over":
            state = game_over.run(screen, clock, font, big_font, score)
        elif state == "quit":
            return


if __name__ == "__main__":
    main()
