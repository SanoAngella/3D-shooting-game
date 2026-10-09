import pygame as pg
import sys
import math
from settings import *
from map import *
from player import *
from raycasting import *
from object_renderer import *
from sprite_object import *
from object_handler import *
from weapon import *
from sound import *
from pathfinding import *
from joystick_controller import JoystickController


class Game:
    def __init__(self):
        pg.init()
        pg.mouse.set_visible(False)
        self.screen = pg.display.set_mode(RES)
        pg.event.set_grab(True)
        self.clock = pg.time.Clock()
        self.delta_time = 1
        self.global_trigger = False
        self.global_event = pg.USEREVENT + 0
        pg.time.set_timer(self.global_event, 40)
        self.show_map = False
        self.joystick = JoystickController(self)
        self.new_game()

    def new_game(self):
        self.map = Map(self)
        self.player = Player(self)
        self.object_renderer = ObjectRenderer(self)
        self.raycasting = RayCasting(self)
        self.object_handler = ObjectHandler(self)
        self.weapon = Weapon(self)
        self.sound = Sound(self)
        self.pathfinding = PathFinding(self)
        pg.mixer.music.play(-1)

    def update(self):
        self.joystick.update()
        self.player.update()
        self.raycasting.update()
        self.object_handler.update()
        self.weapon.update()
        pg.display.flip()
        self.delta_time = self.clock.tick(FPS)
        pg.display.set_caption(f'{self.clock.get_fps() :.1f}')

    def draw_2d_map(self):
        cell_size = 15
        pad = 10
        map_w = self.map.cols * cell_size
        map_h = self.map.rows * cell_size

        map_surf = pg.Surface((map_w + pad * 2, map_h + pad * 2), pg.SRCALPHA)
        map_surf.fill((15, 15, 25, 210))

        # Border
        pg.draw.rect(map_surf, (80, 160, 255), (0, 0, map_w + pad * 2, map_h + pad * 2), 2)

        # Walls
        for (x, y) in self.map.world_map:
            pg.draw.rect(map_surf, (80, 80, 100), (pad + x * cell_size, pad + y * cell_size, cell_size, cell_size))

        # Alive Enemies (red dots)
        for npc in self.object_handler.npc_list:
            if npc.alive:
                ex = pad + int(npc.x * cell_size)
                ey = pad + int(npc.y * cell_size)
                pg.draw.circle(map_surf, (255, 40, 40), (ex, ey), 4)

        # Coins (gold dots with bright core)
        for coin in self.object_handler.coin_list:
            if not coin.is_collected:
                cx = pad + int(coin.x * cell_size)
                cy = pad + int(coin.y * cell_size)
                pg.draw.circle(map_surf, (255, 215, 0), (cx, cy), 4)
                pg.draw.circle(map_surf, (255, 255, 220), (cx, cy), 2)

        # Player (green dot + yellow line for view direction)
        px = pad + int(self.player.x * cell_size)
        py = pad + int(self.player.y * cell_size)
        pg.draw.circle(map_surf, (0, 255, 120), (px, py), 5)
        lx = px + int(math.cos(self.player.angle) * 12)
        ly = py + int(math.sin(self.player.angle) * 12)
        pg.draw.line(map_surf, (255, 230, 0), (px, py), (lx, ly), 2)

        # Render on top-right of screen
        pos_x = WIDTH - map_w - pad * 2 - 20
        pos_y = 20
        self.screen.blit(map_surf, (pos_x, pos_y))

    def draw(self):
        self.object_renderer.draw()
        self.weapon.draw()
        if self.show_map:
            self.draw_2d_map()

    def check_events(self):
        self.global_trigger = False
        for event in pg.event.get():
            if event.type == pg.QUIT or (event.type == pg.KEYDOWN and event.key == pg.K_ESCAPE):
                pg.quit()
                sys.exit()
            elif event.type == pg.KEYDOWN and (event.key == pg.K_m or event.key == pg.K_TAB):
                self.show_map = not self.show_map
            elif event.type == self.global_event:
                self.global_trigger = True
            self.player.single_fire_event(event)

        if self.joystick.check_escape_trigger():
            pg.quit()
            sys.exit()

        if self.joystick.check_map_trigger():
            self.show_map = not self.show_map

    def run(self):
        while True:
            self.check_events()
            self.update()
            self.draw()


if __name__ == '__main__':
    game = Game()
    game.run()