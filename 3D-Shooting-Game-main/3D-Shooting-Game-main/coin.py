import os
import math
import wave
import struct
from collections import deque
import pygame as pg
from sprite_object import AnimatedSprite


def ensure_coin_assets():
    """Generates coin sprite frames and coin pickup sound if they don't already exist."""
    if not pg.get_init():
        pg.init()
    coin_dir = os.path.join('resources', 'sprites', 'animated_sprites', 'coin')
    os.makedirs(coin_dir, exist_ok=True)

    # 1. Generate 8 frames of a 3D rotating gold coin
    if not os.path.exists(os.path.join(coin_dir, '0.png')):
        num_frames = 8
        size = 128
        center = size // 2
        radius = 42

        for i in range(num_frames):
            angle = i * (2 * math.pi / num_frames)
            cos_a = math.cos(angle)

            surf = pg.Surface((size, size), pg.SRCALPHA)

            # Horizontal radius compressed by cos to simulate 3D rotation
            rx = max(4, int(radius * abs(cos_a)))
            ry = radius

            # Soft golden outer glow
            glow_surf = pg.Surface((size, size), pg.SRCALPHA)
            pg.draw.ellipse(
                glow_surf,
                (255, 220, 80, 45),
                (center - rx - 8, center - ry - 6, (rx + 8) * 2, (ry + 6) * 2),
            )
            surf.blit(glow_surf, (0, 0))

            # 3D side edge / rim thickness when angled
            if abs(cos_a) < 0.95:
                thickness = max(3, int(8 * (1.0 - abs(cos_a))))
                rim_x = center - rx - (thickness if cos_a >= 0 else 0)
                rim_rect = (rim_x, center - ry, rx * 2 + thickness, ry * 2)
                pg.draw.ellipse(surf, (160, 110, 20), rim_rect)

            # Outer dark gold rim
            pg.draw.ellipse(
                surf, (190, 140, 25), (center - rx, center - ry, rx * 2, ry * 2)
            )

            # Inner bright gold face
            inner_rx = max(2, rx - 4)
            inner_ry = max(4, ry - 4)
            pg.draw.ellipse(
                surf,
                (255, 215, 0),
                (center - inner_rx, center - inner_ry, inner_rx * 2, inner_ry * 2),
            )

            # Embossed star / diamond emblem
            if rx > 10:
                star_rx = int(inner_rx * 0.5)
                star_ry = int(inner_ry * 0.5)
                pts = [
                    (center, center - star_ry),
                    (center + star_rx, center),
                    (center, center + star_ry),
                    (center - star_rx, center),
                ]
                pg.draw.polygon(surf, (220, 170, 20), pts)
                pg.draw.polygon(surf, (255, 245, 170), pts, 2)

            # Specular light gleam on top-left
            if rx > 6:
                gleam_x = center - int(inner_rx * 0.4)
                gleam_y = center - int(inner_ry * 0.4)
                gleam_r = max(2, int(6 * abs(cos_a)))
                pg.draw.circle(
                    surf, (255, 255, 240, 220), (gleam_x, gleam_y), gleam_r
                )

            frame_path = os.path.join(coin_dir, f'{i}.png')
            pg.image.save(surf, frame_path)

    # 2. Generate retro arcade coin chime WAV sound if not present
    sound_dir = os.path.join('resources', 'sound')
    os.makedirs(sound_dir, exist_ok=True)
    sound_path = os.path.join(sound_dir, 'coin.wav')
    if not os.path.exists(sound_path):
        sample_rate = 44100
        # Two-tone chime: B5 (988 Hz for 0.07s) -> E6 (1319 Hz for 0.22s with decay)
        dur1 = 0.07
        dur2 = 0.22
        freq1 = 987.77
        freq2 = 1318.51

        frames = bytearray()

        # Tone 1
        n1 = int(sample_rate * dur1)
        for s in range(n1):
            t = s / sample_rate
            env = min(1.0, s / (sample_rate * 0.005)) * (1.0 - 0.2 * (s / n1))
            val = math.sin(2 * math.pi * freq1 * t) * env * 0.6
            ival = int(max(-32767, min(32767, val * 32767)))
            frames.extend(struct.pack('<h', ival))

        # Tone 2
        n2 = int(sample_rate * dur2)
        for s in range(n2):
            t = s / sample_rate
            env = math.exp(-4.5 * t)
            val = (
                math.sin(2 * math.pi * freq2 * t)
                + 0.25 * math.sin(4 * math.pi * freq2 * t)
            ) * env * 0.7
            ival = int(max(-32767, min(32767, val * 32767)))
            frames.extend(struct.pack('<h', ival))

        with wave.open(sound_path, 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(frames)


class Coin(AnimatedSprite):
    def __init__(self, game, pos=(1.5, 1.5)):
        ensure_coin_assets()
        coin_path = 'resources/sprites/animated_sprites/coin/0.png'
        super().__init__(
            game, path=coin_path, pos=pos, scale=0.42, shift=0.60, animation_time=90
        )
        self.base_shift = 0.60
        self.is_collected = False

    def get_images(self, path):
        images = deque()
        file_names = sorted(
            os.listdir(path),
            key=lambda x: int(os.path.splitext(x)[0])
            if os.path.splitext(x)[0].isdigit()
            else x,
        )
        for file_name in file_names:
            full_path = os.path.join(path, file_name)
            if os.path.isfile(full_path):
                img = pg.image.load(full_path).convert_alpha()
                images.append(img)
        return images

    def update(self):
        if self.is_collected:
            return
        # Bobbing floating motion
        self.SPRITE_HEIGHT_SHIFT = self.base_shift + math.sin(
            pg.time.get_ticks() * 0.005
        ) * 0.06
        super().update()
        self.check_collection()

    def check_collection(self):
        dist = math.hypot(self.x - self.player.x, self.y - self.player.y)
        if dist < 0.65:
            self.collect()

    def collect(self):
        self.is_collected = True
        self.player.add_coin(amount=1, heal=150)
        if (
            hasattr(self.game, 'sound')
            and hasattr(self.game.sound, 'coin')
            and self.game.sound.coin
        ):
            self.game.sound.coin.play()
