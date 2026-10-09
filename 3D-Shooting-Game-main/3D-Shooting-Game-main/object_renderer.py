import pygame as pg
from settings import *


class ObjectRenderer:
    def __init__(self, game):
        self.game = game
        self.screen = game.screen
        self.wall_textures = self.load_wall_textures()
        self.sky_image = self.get_texture('resources/textures/sky.png', (WIDTH, HALF_HEIGHT))
        self.sky_offset = 0
        self.blood_screen = self.get_texture('resources/textures/blood_screen.png', RES)
        self.digit_size = 90
        self.digit_images = [self.get_texture(f'resources/textures/digits/{i}.png', [self.digit_size] * 2)
                             for i in range(11)]
        self.digits = dict(zip(map(str, range(11)), self.digit_images))
        self.game_over_image = self.get_texture('resources/textures/game_over.png', RES)
        self.win_image = self.get_texture('resources/textures/win.png', RES)
        pg.font.init()
        self.hud_font = pg.font.SysFont('arial', 22, bold=True)
        self.notify_font = pg.font.SysFont('arial', 20, bold=True)
        self.heal_surface = pg.Surface(RES, pg.SRCALPHA)
        self.heal_surface.fill((0, 255, 120, 35))

    def draw(self):
        self.draw_background()
        self.render_game_objects()
        self.draw_player_health()
        self.draw_coin_hud()
        self.draw_heal_effect()

    def win(self):
        self.screen.blit(self.win_image, (0, 0))

    def game_over(self):
        self.screen.blit(self.game_over_image, (0, 0))

    def draw_player_health(self):
        health = str(max(0, self.game.player.health))
        for i, char in enumerate(health):
            self.screen.blit(self.digits[char], (i * self.digit_size, 0))
        self.screen.blit(self.digits['10'], ((i + 1) * self.digit_size, 0))

    def draw_coin_hud(self):
        hud_w, hud_h = 165, 42
        hud_x, hud_y = 20, 105
        hud_surf = pg.Surface((hud_w, hud_h), pg.SRCALPHA)
        hud_surf.fill((15, 15, 25, 215))
        pg.draw.rect(hud_surf, (255, 215, 0), (0, 0, hud_w, hud_h), 2, border_radius=8)

        # 2D Gold coin icon
        icon_cx, icon_cy = 22, hud_h // 2
        pg.draw.circle(hud_surf, (255, 215, 0), (icon_cx, icon_cy), 11)
        pg.draw.circle(hud_surf, (255, 245, 160), (icon_cx, icon_cy), 8)
        pg.draw.circle(hud_surf, (200, 150, 20), (icon_cx, icon_cy), 4)

        # Text: COINS: X
        text = self.hud_font.render(f'COINS: {self.game.player.coins}', True, (255, 235, 120))
        hud_surf.blit(text, (42, 9))
        self.screen.blit(hud_surf, (hud_x, hud_y))

        # Floating pickup notification: "+150 HP! 🪙"
        now = pg.time.get_ticks()
        if now < self.game.player.heal_notification:
            notify_surf = pg.Surface((140, 36), pg.SRCALPHA)
            notify_surf.fill((20, 50, 25, 220))
            pg.draw.rect(notify_surf, (0, 255, 120), (0, 0, 140, 36), 2, border_radius=6)
            notify_text = self.notify_font.render('+150 HP! 🪙', True, (120, 255, 160))
            notify_surf.blit(notify_text, (12, 6))
            self.screen.blit(notify_surf, (hud_x + hud_w + 12, hud_y + 3))

    def draw_heal_effect(self):
        if pg.time.get_ticks() < self.game.player.heal_flash:
            self.screen.blit(self.heal_surface, (0, 0))

    def player_damage(self):
        self.screen.blit(self.blood_screen, (0, 0))

    def draw_background(self):
        self.sky_offset = (self.sky_offset + 0.1 * self.game.player.rel) % WIDTH #sky image line adjustment 
        self.screen.blit(self.sky_image, (-self.sky_offset, 0))
        self.screen.blit(self.sky_image, (-self.sky_offset + WIDTH, 0))
        # floor
        pg.draw.rect(self.screen, FLOOR_COLOR, (0, HALF_HEIGHT, WIDTH, HEIGHT))

    def render_game_objects(self):
        list_objects = sorted(self.game.raycasting.objects_to_render, key=lambda t: t[0], reverse=True)
        for depth, image, pos in list_objects:
            self.screen.blit(image, pos)

    @staticmethod
    def get_texture(path, res=(TEXTURE_SIZE, TEXTURE_SIZE)):
        texture = pg.image.load(path).convert_alpha()
        return pg.transform.scale(texture, res)

    def load_wall_textures(self):
        textures = {
            1: self.get_texture('resources/textures/1.png'),
            2: self.get_texture('resources/textures/2.png'),
            3: self.get_texture('resources/textures/3.png'),
            4: self.get_texture('resources/textures/4.png'),
            5: self.get_texture('resources/textures/5.png'),
        }
        textures[6] = textures[2]
        textures[8] = textures[1]
        textures[9] = textures[3]
        return textures