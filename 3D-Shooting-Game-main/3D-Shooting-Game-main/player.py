from settings import *
import pygame as pg
import math


class Player:
    def __init__(self, game):
        self.game = game
        self.x, self.y = PLAYER_POS
        self.angle = PLAYER_ANGLE
        self.shot = False
        self.health = PLAYER_MAX_HEALTH
        self.rel = 0
        self.health_recovery_delay = 1000
        self.time_prev = pg.time.get_ticks()
        # diagonal movement correction
        self.diag_move_corr = 1 / math.sqrt(2)
        # coin pickup & heal tracking
        self.coins = 0
        self.heal_notification = 0
        self.heal_flash = 0

    def add_coin(self, amount=1, heal=150):
        self.coins += amount
        self.health = min(PLAYER_MAX_HEALTH, self.health + heal)
        now = pg.time.get_ticks()
        self.heal_notification = now + 1500
        self.heal_flash = now + 200

    def recover_health(self):
        if self.check_health_recovery_delay() and self.health < PLAYER_MAX_HEALTH:
            self.health += 10

    def check_health_recovery_delay(self):
        time_now = pg.time.get_ticks()
        if time_now - self.time_prev > self.health_recovery_delay:
            self.time_prev = time_now
            return True

    def check_game_over(self):
        if self.health < 1:
            self.game.object_renderer.game_over()
            pg.display.flip()
            pg.time.delay(1500)
            self.game.new_game()

    def get_damage(self, damage):
        self.health -= damage
        self.game.object_renderer.player_damage()
        self.game.sound.player_pain.play()
        self.check_game_over()

    def check_joystick_fire(self):
        if self.game.joystick.check_shoot_trigger() and not self.shot and not self.game.weapon.reloading:
            self.game.sound.shotgun.play()
            self.shot = True
            self.game.weapon.reloading = True

    def single_fire_event(self, event):
        is_left_click = event.type == pg.MOUSEBUTTONDOWN and event.button == 1
        is_spacebar = event.type == pg.KEYDOWN and event.key == pg.K_SPACE
        if (is_left_click or is_spacebar) and not self.shot and not self.game.weapon.reloading:
            self.game.sound.shotgun.play()
            self.shot = True
            self.game.weapon.reloading = True

    def movement(self):
        sin_a = math.sin(self.angle)
        cos_a = math.cos(self.angle)
        dx, dy = 0, 0
        speed = PLAYER_SPEED * self.game.delta_time
        speed_sin = speed * sin_a
        speed_cos = speed * cos_a

        keys = pg.key.get_pressed()
        num_key_pressed = -1
        if keys[pg.K_w]:
            num_key_pressed += 1
            dx += speed_cos
            dy += speed_sin
        if keys[pg.K_s]:
            num_key_pressed += 1
            dx += -speed_cos
            dy += -speed_sin
        if keys[pg.K_a]:
            num_key_pressed += 1
            dx += speed_sin
            dy += -speed_cos
        if keys[pg.K_d]:
            num_key_pressed += 1
            dx += -speed_sin
            dy += speed_cos

        # diag move correction
        if num_key_pressed:
            dx *= self.diag_move_corr
            dy *= self.diag_move_corr

        # Joystick analog movement
        if hasattr(self.game, 'joystick'):
            joy_x, joy_y = self.game.joystick.get_movement()
            if joy_x != 0 or joy_y != 0:
                dx += (speed_cos * joy_y - speed_sin * joy_x)
                dy += (speed_sin * joy_y + speed_cos * joy_x)

        self.check_wall_collision(dx, dy)

        # if keys[pg.K_LEFT]:
        #     self.angle -= PLAYER_ROT_SPEED * self.game.delta_time
        # if keys[pg.K_RIGHT]:
        #     self.angle += PLAYER_ROT_SPEED * self.game.delta_time
        self.angle %= math.tau

    def check_wall(self, x, y):
        # Prevent leaving map boundaries into void
        if not (0 <= x < self.game.map.cols and 0 <= y < self.game.map.rows):
            return False
        return (x, y) not in self.game.map.world_map

    def check_wall_collision(self, dx, dy):
        # Robust collision with fixed player radius margin to prevent tunneling on lag spikes
        margin_x = 0.25 if dx > 0 else (-0.25 if dx < 0 else 0)
        margin_y = 0.25 if dy > 0 else (-0.25 if dy < 0 else 0)
        if self.check_wall(int(self.x + dx + margin_x), int(self.y)):
            self.x += dx
        if self.check_wall(int(self.x), int(self.y + dy + margin_y)):
            self.y += dy

    def draw(self):
        pg.draw.line(self.game.screen, 'yellow', (self.x * 100, self.y * 100),
                    (self.x * 100 + WIDTH * math.cos(self.angle),
                     self.y * 100 + WIDTH * math. sin(self.angle)), 2)
        pg.draw.circle(self.game.screen, 'green', (self.x * 100, self.y * 100), 15)

    def mouse_control(self):
        mx, my = pg.mouse.get_pos()
        if mx < MOUSE_BORDER_LEFT or mx > MOUSE_BORDER_RIGHT:
            pg.mouse.set_pos([HALF_WIDTH, HALF_HEIGHT])
        self.rel = pg.mouse.get_rel()[0]
        self.rel = max(-MOUSE_MAX_REL, min(MOUSE_MAX_REL, self.rel))
        self.angle += self.rel * MOUSE_SENSITIVITY * self.game.delta_time

        # Joystick camera rotation
        if hasattr(self.game, 'joystick'):
            joy_look = self.game.joystick.get_look()
            if joy_look != 0:
                self.angle += joy_look * PLAYER_ROT_SPEED * 1.5 * self.game.delta_time

    def update(self):
        self.check_joystick_fire()
        self.movement()
        self.mouse_control()
        self.recover_health()

    @property
    def pos(self):
        return self.x, self.y

    @property
    def map_pos(self):
        return int(self.x), int(self.y)