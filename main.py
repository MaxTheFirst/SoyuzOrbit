import pygame
import config

from earth import Earth
from orbit import Orbit
from iss import ISS
from rocket import Rocket


pygame.init()
screen = pygame.display.set_mode((config.WIDTH, config.HEIGHT))
pygame.display.set_caption("МКС на орбите Земли")
clock = pygame.time.Clock()


earth = Earth()
orbit = Orbit()
iss = ISS(orbit)
rocket = Rocket(iss)


def main():
    running = True
    while running:
        dt = clock.tick(config.FPS) / 1000  # секунд на кадр

        earth.update(dt)
        iss.update(dt)

        screen.fill((0, 0, 20))
        earth.draw(screen)
        orbit.draw(screen)
        earth.draw_radius(screen)
        iss.draw(screen)
        rocket.update(dt)
        rocket.draw(screen)
        rocket.draw_info(screen)

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        if rocket.docked:
            frame = screen.copy()
            pygame.image.save(frame, "frame.png")
            show_until = pygame.time.get_ticks() + config.ENDING

            while True:
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                        break

                screen.blit(frame, (0, 0))
                pygame.display.flip()
                clock.tick(30)

                # выходим по таймеру или если окно закрыли
                if not running or pygame.time.get_ticks() >= show_until:
                    break
            break

    pygame.quit()


if __name__ == '__main__':
    main()