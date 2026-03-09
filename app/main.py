from __future__ import annotations

import random
from dataclasses import dataclass

import pygame

SCREEN_WIDTH = 960
SCREEN_HEIGHT = 640
TILE = 32
SWARM_SIZE = 50
GRAVITY = 1800.0
MOVE_SPEED = 120.0
JUMP_VEL = -520.0
FPS = 60

MAP = [
    "##############################",
    "#............................#",
    "#...............###..........#",
    "#............................#",
    "#.....#####..................#",
    "#............................#",
    "#.................####.......#",
    "#............................#",
    "#..........###...............#",
    "#............................#",
    "#....####....................#",
    "#............................#",
    "#.................###........#",
    "#............................#",
    "#............................#",
    "##############################",
]


@dataclass
class Agent:
    x: float
    y: float
    vx: float
    vy: float
    facing: int
    on_ground: bool
    jump_cooldown: float
    think_timer: float


def solid_at(px: float, py: float) -> bool:
    tx = int(px // TILE)
    ty = int(py // TILE)
    if ty < 0 or ty >= len(MAP) or tx < 0 or tx >= len(MAP[0]):
        return True
    return MAP[ty][tx] == "#"


def rect_collides(x: float, y: float, w: int, h: int) -> bool:
    points = [
        (x, y),
        (x + w - 1, y),
        (x, y + h - 1),
        (x + w - 1, y + h - 1),
    ]
    return any(solid_at(px, py) for px, py in points)


def spawn_agents() -> list[Agent]:
    agents: list[Agent] = []
    for i in range(SWARM_SIZE):
        agents.append(
            Agent(
                x=64 + (i % 10) * 18,
                y=SCREEN_HEIGHT - 120 - (i // 10) * 8,
                vx=0.0,
                vy=0.0,
                facing=1 if i % 2 == 0 else -1,
                on_ground=False,
                jump_cooldown=random.uniform(0.1, 0.7),
                think_timer=random.uniform(0.05, 0.3),
            )
        )
    return agents


def ai_step(a: Agent, dt: float) -> None:
    a.think_timer -= dt
    a.jump_cooldown -= dt

    if a.think_timer <= 0:
        a.think_timer = random.uniform(0.08, 0.25)
        if random.random() < 0.07:
            a.facing *= -1

    a.vx = a.facing * MOVE_SPEED

    look_x = a.x + (20 if a.facing > 0 else -2)
    ahead_blocked = solid_at(look_x, a.y + 14)
    no_floor_ahead = not solid_at(look_x, a.y + 36)

    if a.on_ground and a.jump_cooldown <= 0 and (ahead_blocked or no_floor_ahead):
        a.vy = JUMP_VEL
        a.on_ground = False
        a.jump_cooldown = random.uniform(0.25, 0.9)


def physics_step(a: Agent, dt: float) -> None:
    width, height = 14, 22

    a.vy += GRAVITY * dt

    nx = a.x + a.vx * dt
    if not rect_collides(nx, a.y, width, height):
        a.x = nx
    else:
        a.facing *= -1
        a.vx = a.facing * MOVE_SPEED

    ny = a.y + a.vy * dt
    if not rect_collides(a.x, ny, width, height):
        a.y = ny
        a.on_ground = False
    else:
        if a.vy > 0:
            a.on_ground = True
        a.vy = 0.0


def draw_map(screen: pygame.Surface) -> None:
    wall_color = (35, 45, 65)
    for y, row in enumerate(MAP):
        for x, t in enumerate(row):
            if t == "#":
                pygame.draw.rect(screen, wall_color, (x * TILE, y * TILE, TILE, TILE))


def main() -> None:
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("50-Agent Platformer Swarm Prototype")
    clock = pygame.time.Clock()

    mario_sprite = pygame.Surface((14, 22), pygame.SRCALPHA)
    mario_sprite.fill((225, 60, 60))

    agents = spawn_agents()
    running = True
    paused = False

    while running:
        dt = min(clock.tick(FPS) / 1000.0, 0.033)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_r:
                    agents = spawn_agents()
                elif event.key == pygame.K_p:
                    paused = not paused

        if not paused:
            for a in agents:
                ai_step(a, dt)
                physics_step(a, dt)

        screen.fill((18, 22, 34))
        draw_map(screen)

        for a in agents:
            screen.blit(mario_sprite, (a.x, a.y))

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
