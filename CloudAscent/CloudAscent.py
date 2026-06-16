import pygame
import random
import sys
import os
import ctypes
import argparse
import hashlib
import calendar
import time
import json
import math
import requests

# ── 工作目录：统一以 exe / 脚本所在目录为根，打包后图片路径不丢 ───────────────
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)

# ── 调试开关 ──────────────────────────────────────────────────────────────────
DEBUG = True

def log(msg):
    if DEBUG:
        print(f'[DBG] {msg}', flush=True)

# ── 命令行参数 ────────────────────────────────────────────────────────────────
def _parse_args():
    parser = argparse.ArgumentParser(description="云端冲天")
    parser.add_argument("--nAccountID",  default="0",  help="账号ID")
    parser.add_argument("--role_id",     default="0",  help="角色ID")
    parser.add_argument("--role_name",   default="",   help="角色名")
    parser.add_argument("--nWorldID",    default="0",  help="服务器ID")
    parser.add_argument("--level",       default="0",  help="角色等级")
    parser.add_argument("--vip_lv",      default="0",  help="VIP等级")
    return parser.parse_args()

_args = _parse_args()

# 校验：role_id 为 0 或空则拒绝启动
if not _args.role_id or _args.role_id == "0":
    try:
        import tkinter as tk
        from tkinter import messagebox
        _root = tk.Tk(); _root.withdraw()
        messagebox.showerror("启动失败", "启动失败，请通过游戏内启动。")
        _root.destroy()
    except Exception:
        pass
    sys.exit(1)

PLAYER_NAME  = _args.role_name or "未知角色"
PLAYER_ID    = _args.role_id
PLAYER_LEVEL = int(_args.level)  if _args.level.isdigit()  else 0
PLAYER_VIP   = int(_args.vip_lv) if _args.vip_lv.isdigit() else 0
nAccountID   = _args.nAccountID
WORLD_ID     = _args.nWorldID

# ── 成绩上报接口 ──────────────────────────────────────────────────────────────
_SUBMIT_URL = "https://gameapi.q1.com/api/Game/SubmitMinGameResult"
_APPID      = 2       # 云端冲天 appid=2
_GAME_ID    = 6
_SECRET_KEY = "4c9fa5bbbc8342c5a015b3036c6bdf7e"


def submit_game_result(nAccountID, role_id, nWorldID, score, play_seconds):
    """上报游戏结果，返回 (success: bool, message: str)"""
    timestamp  = calendar.timegm(time.gmtime())
    result_str = json.dumps(
        {"play_seconds": play_seconds},
        separators=(',', ':'), ensure_ascii=False
    )
    sign_raw = (
        f"{_APPID}{_GAME_ID}{nAccountID}{role_id}{nWorldID}"
        f"{result_str}{score}{timestamp}{_SECRET_KEY}"
    )
    sign = hashlib.md5(sign_raw.encode()).hexdigest()
    payload = {
        "appid":      _APPID,
        "game_id":    _GAME_ID,
        "nAccountID": int(nAccountID),
        "role_id":    int(role_id),
        "nWorldID":   int(nWorldID),
        "result":     result_str,
        "score":      int(score),
        "timestamp":  timestamp,
        "sign":       sign,
    }
    try:
        res  = requests.post(_SUBMIT_URL, json=payload, timeout=10)
        data = res.json()
        if data.get("code") == 1:
            return True, data.get("msg", "奖励已匹配，等待发放")
        else:
            return False, data.get("msg", "奖励发放失败，请联系GM")
    except Exception as e:
        return False, f"上报失败，请联系GM\n({e})"

# ── 常量 ──────────────────────────────────────────────────────────────────────
SCREEN_W, SCREEN_H = 600, 720
FPS = 60

GRAVITY          = 0.55
JUMP_SPEED       = -14.0
MOVE_SPEED       = 5.5
CLOUD_W          = 90
CLOUD_H          = 90
CLOUD_ANIM_SPEED = 10

PLANK_W_MIN   = 80
PLANK_W_MAX   = 170
MOVING_W_MIN  = 55
MOVING_W_MAX  = 90
PLANK_H       = 30
PLANK_GAP_MIN = 110
PLANK_GAP_MAX = 155

MAX_HORIZ_REACH = 125

# 木板类型
TYPE_BEIGE    = 'beige'
TYPE_PURPLE   = 'purple'
TYPE_MOVING   = 'moving'
TYPE_FRAGILE  = 'fragile'
TYPE_SPRING   = 'spring'    # 新增：弹簧板
TYPE_ICE      = 'ice'       # 新增：冰板

PURPLE_CHANCE  = 0.10
FRAGILE_CHANCE = 0.12
SPRING_CHANCE  = 0.06       # 弹簧板概率
ICE_CHANCE     = 0.06       # 冰板概率

MOVING_SPEED_MIN = 1.2
MOVING_SPEED_MAX = 2.8
FRAGILE_STAND_FRAMES = FPS

IMG_DIR   = os.path.join(BASE_DIR, 'img')
SOUND_DIR = os.path.join(BASE_DIR, 'Sound')
DATA_DIR  = os.path.join(BASE_DIR, 'data')

BTN_W, BTN_H = 180, 50
BTN_RADIUS   = 12

# ── 游戏状态 ──────────────────────────────────────────────────────────────────
ST_MENU      = "menu"
ST_PLAYING   = "playing"
ST_PAUSED    = "paused"
ST_OVER      = "over"
ST_SETTINGS  = "settings"
ST_CONFIRM   = "confirm"
ST_SUBMIT_RESULT = "submit_result"

# ── 浮空实体定义表 ────────────────────────────────────────────────────────────
ENTITY_DEFS = {
    'pet_star_cloud': {
        'img_dir':      'pet_star_cloud',
        'frame_count':  4,
        'size':         70,
        'score_delta':  +100,
        'speed_min':    0.5,
        'speed_max':    1.5,
        'spawn_chance': 0.003,
        'max_count':    2,
        'anim_speed':   8,
        'margin':       10,
    },
    'monster1': {
        'img_dir':      'monster1',
        'frame_count':  6,
        'size':         75,
        'score_delta':  -50,
        'speed':        2.2,
        'spawn_chance': 0.003,
        'max_count':    2,
        'anim_speed':   5,
        'margin':       12,
        'behavior':     'chase',
    },
    'monster2': {
        'img_dir':      'thunder_cloud',
        'frame_files':  [
            'thunder_cloud_smile.png',
            'thunder_cloud_happy.png',
            'thunder_cloud_surprise.png',
            'thunder_cloud_angry.png',
            'thunder_cloud_shy.png',
            'thunder_cloud_fight.png',
        ],
        'frame_count':  6,
        'size':         80,
        'score_delta':  -500,
        'speed_min':    0.8,
        'speed_max':    2.0,
        'spawn_chance': 0.0015,
        'max_count':    2,
        'anim_speed':   7,
        'margin':       10,
    },
}

# ── 道具定义表 ────────────────────────────────────────────────────────────────
ITEM_DEFS = {
    'shield': {
        'color':    (255, 215, 0),
        'name':     '护盾',
        'desc':     '免疫一次怪物伤害',
        'duration': -1,  # 单次触发
        'icon_char': 'S',
    },
    'magnet': {
        'color':    (255, 80, 80),
        'name':     '磁铁',
        'desc':     '自动吸附附近星云宠物',
        'duration': 480,  # 8 秒
        'icon_char': 'M',
    },
    'rocket_shoes': {
        'color':    (255, 140, 0),
        'name':     '火箭鞋',
        'desc':     '弹跳+50% 速度+30%',
        'duration': 600,  # 10 秒
        'icon_char': 'R',
    },
    'clock': {
        'color':    (255, 255, 100),
        'name':     '时钟',
        'desc':     '减慢敌人速度50%',
        'duration': 360,  # 6 秒
        'icon_char': 'T',
    },
    'shrink': {
        'color':    (180, 100, 255),
        'name':     '缩小药水',
        'desc':     '碰撞体积缩小50%',
        'duration': 480,  # 8 秒
        'icon_char': 'P',
    },
}

# ── 天气阶段定义 ──────────────────────────────────────────────────────────────
WEATHER_PHASES = [
    {'name': '晴天',   'height_min': 0,     'height_max': 2000,  'wind': False, 'lightning': False},
    {'name': '多云',   'height_min': 2000,  'height_max': 5000,  'wind': False, 'lightning': False},
    {'name': '暴风',   'height_min': 5000,  'height_max': 8000,  'wind': True,  'lightning': False},
    {'name': '雷暴',   'height_min': 8000,  'height_max': 12000, 'wind': True,  'lightning': True},
    {'name': '星空',   'height_min': 12000, 'height_max': 18000, 'wind': False, 'lightning': False},
    {'name': '极光',   'height_min': 18000, 'height_max': 99999, 'wind': False, 'lightning': False},
]


# ── 字体 ──────────────────────────────────────────────────────────────────────
def _font(size, bold=False):
    for path in [
        "C:/Windows/Fonts/msyh.ttc",
        "C:/Windows/Fonts/msyhbd.ttc",
        "C:/Windows/Fonts/simhei.ttf",
        "C:/Windows/Fonts/simsun.ttc",
    ]:
        try:
            return pygame.font.Font(path, size)
        except Exception:
            pass
    return pygame.font.SysFont("microsoftyahei,arial", size, bold=bold)


# ── 本地数据持久化 ──────────────────────────────────────────────────────────────
def _ensure_data_dir():
    os.makedirs(DATA_DIR, exist_ok=True)

def _load_json(filename, default):
    _ensure_data_dir()
    path = os.path.join(DATA_DIR, filename)
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default

def _save_json(filename, data):
    _ensure_data_dir()
    path = os.path.join(DATA_DIR, filename)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ── 工具 ──────────────────────────────────────────────────────────────────────
def load_img(path, w, h):
    img = pygame.image.load(path).convert_alpha()
    return pygame.transform.smoothscale(img, (w, h))


def lerp_color(c1, c2, t):
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


# ── 粒子系统 ──────────────────────────────────────────────────────────────────
class Particle:
    def __init__(self, x, y, vx, vy, color, life=30, size=4, gravity=0.1):
        self.x = float(x)
        self.y = float(y)
        self.vx = vx
        self.vy = vy
        self.color = color
        self.life = life
        self.max_life = life
        self.size = size
        self.gravity = gravity

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.vy += self.gravity
        self.life -= 1

    @property
    def alive(self):
        return self.life > 0

    def draw(self, surf):
        alpha = int(255 * self.life / self.max_life)
        s = max(1, int(self.size * self.life / self.max_life))
        ps = pygame.Surface((s * 2, s * 2), pygame.SRCALPHA)
        pygame.draw.circle(ps, (*self.color, alpha), (s, s), s)
        surf.blit(ps, (int(self.x) - s, int(self.y) - s))


class ParticleSystem:
    def __init__(self):
        self.particles = []

    def emit_burst(self, x, y, color, count=8, speed=3.0, life=25, size=4):
        for _ in range(count):
            angle = random.uniform(0, math.pi * 2)
            spd = random.uniform(speed * 0.5, speed)
            vx = math.cos(angle) * spd
            vy = math.sin(angle) * spd - 1.0
            self.particles.append(Particle(
                x + random.uniform(-5, 5),
                y + random.uniform(-5, 5),
                vx, vy, color, life,
                size=random.uniform(size * 0.5, size)
            ))

    def emit_jump(self, x, y):
        self.emit_burst(x, y, (200, 220, 255), count=6, speed=2.0, life=20, size=3)

    def emit_boost_jump(self, x, y):
        for c in [(180, 100, 255), (220, 150, 255), (255, 200, 255)]:
            self.emit_burst(x, y, c, count=5, speed=3.5, life=30, size=5)

    def emit_collect(self, x, y):
        for c in [(255, 215, 0), (255, 255, 100), (255, 180, 0)]:
            self.emit_burst(x, y, c, count=10, speed=4.0, life=35, size=5)

    def emit_monster_hit(self, x, y):
        for c in [(255, 50, 50), (255, 100, 50), (255, 150, 50)]:
            self.emit_burst(x, y, c, count=12, speed=5.0, life=25, size=4)

    def emit_shield_block(self, x, y):
        for c in [(255, 255, 100), (255, 215, 0), (255, 255, 255)]:
            self.emit_burst(x, y, c, count=15, speed=6.0, life=30, size=4)

    def update(self):
        for p in self.particles:
            p.update()
        self.particles = [p for p in self.particles if p.alive]

    def draw(self, surf):
        for p in self.particles:
            p.draw(surf)


# ── 视差背景系统 ──────────────────────────────────────────────────────────────
class ParallaxBackground:
    """多层视差滚动云层 + 动态天空渐变"""

    def __init__(self):
        self.cloud_layers = []
        self._generate_layers()
        self.stars = []
        self._generate_stars()
        self.flash_alpha = 0         # 闪电全屏闪烁
        self.flash_color = (255, 255, 255)

    def _generate_layers(self):
        # 3 层云层：远(慢)、中、近(快)
        configs = [
            {'count': 8,  'y_range': (0, SCREEN_H), 'speed': 0.15, 'size_range': (60, 120), 'alpha': 40},
            {'count': 6,  'y_range': (0, SCREEN_H), 'speed': 0.35, 'size_range': (40, 90),  'alpha': 55},
            {'count': 5,  'y_range': (0, SCREEN_H), 'speed': 0.6,  'size_range': (30, 70),  'alpha': 30},
        ]
        for cfg in configs:
            layer = []
            for _ in range(cfg['count']):
                w = random.randint(*cfg['size_range'])
                h = int(w * 0.5)
                x = random.uniform(0, SCREEN_W)
                y = random.uniform(*cfg['y_range'])
                vx = random.uniform(cfg['speed'] * 0.5, cfg['speed'])
                if random.random() < 0.5:
                    vx = -vx
                layer.append({'x': x, 'y': y, 'w': w, 'h': h, 'vx': vx, 'alpha': cfg['alpha']})
            self.cloud_layers.append(layer)

    def _generate_stars(self):
        for _ in range(60):
            self.stars.append({
                'x': random.randint(0, SCREEN_W),
                'y': random.randint(0, SCREEN_H),
                'size': random.choice([1, 1, 1, 2]),
                'twinkle_speed': random.uniform(0.02, 0.08),
                'twinkle_offset': random.uniform(0, math.pi * 2),
                'base_alpha': random.randint(100, 220),
            })

    def trigger_flash(self, color=(255, 255, 255), alpha=180):
        self.flash_alpha = alpha
        self.flash_color = color

    def update(self, scroll_speed=0, weather_phase=0):
        # 云层滚动
        for layer in self.cloud_layers:
            for cloud in layer:
                cloud['x'] += cloud['vx']
                if cloud['x'] > SCREEN_W + cloud['w']:
                    cloud['x'] = -cloud['w']
                elif cloud['x'] < -cloud['w']:
                    cloud['x'] = SCREEN_W + cloud['w']

        # 闪电衰减
        if self.flash_alpha > 0:
            self.flash_alpha = max(0, self.flash_alpha - 12)

    def draw(self, surf, score_height=0, weather_phase=0, frame_count=0):
        # 动态天空渐变（根据高度/天气变化）
        phase = self._get_weather_phase(score_height)

        if phase <= 1:  # 晴天/多云
            top_colors = [(100, 170, 245), (140, 180, 240)]
            bot_colors = [(180, 210, 250), (170, 200, 235)]
            idx = min(phase, len(top_colors) - 1)
            sky_top = top_colors[idx]
            sky_bot = bot_colors[idx]
        elif phase == 2:  # 暴风
            sky_top = (80, 90, 120)
            sky_bot = (60, 70, 100)
        elif phase == 3:  # 雷暴
            sky_top = (50, 50, 80)
            sky_bot = (30, 30, 60)
        elif phase == 4:  # 星空
            sky_top = (10, 10, 40)
            sky_bot = (20, 15, 60)
        else:  # 极光
            sky_top = (5, 10, 35)
            sky_bot = (15, 20, 50)

        for y in range(SCREEN_H):
            t = y / (SCREEN_H - 1)
            c = lerp_color(sky_top, sky_bot, t)
            pygame.draw.line(surf, c, (0, y), (SCREEN_W, y))

        # 星空/极光显示星星
        if phase >= 4:
            for star in self.stars:
                twinkle = math.sin(frame_count * star['twinkle_speed'] + star['twinkle_offset'])
                alpha = int(star['base_alpha'] * (0.5 + 0.5 * twinkle))
                alpha = max(0, min(255, alpha))
                ss = pygame.Surface((star['size'] * 2, star['size'] * 2), pygame.SRCALPHA)
                pygame.draw.circle(ss, (255, 255, 255, alpha), (star['size'], star['size']), star['size'])
                surf.blit(ss, (star['x'] - star['size'], star['y'] - star['size']))

        # 极光效果
        if phase >= 5:
            self._draw_aurora(surf, frame_count)

        # 云层
        cloud_alpha_mult = 1.0
        if phase >= 3:
            cloud_alpha_mult = 0.4
        elif phase >= 2:
            cloud_alpha_mult = 0.7

        for layer in self.cloud_layers:
            for cloud in layer:
                cs = pygame.Surface((cloud['w'], cloud['h']), pygame.SRCALPHA)
                alpha = int(cloud['alpha'] * cloud_alpha_mult)
                pygame.draw.ellipse(cs, (255, 255, 255, alpha), cs.get_rect())
                surf.blit(cs, (int(cloud['x']), int(cloud['y'])))

        # 雨滴（暴风/雷暴）
        if phase >= 2:
            self._draw_rain(surf, frame_count, phase)

        # 全屏闪烁（闪电）
        if self.flash_alpha > 0:
            flash_surf = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
            flash_surf.fill((*self.flash_color, int(self.flash_alpha)))
            surf.blit(flash_surf, (0, 0))

    def _get_weather_phase(self, score_height):
        for i, wp in enumerate(WEATHER_PHASES):
            if wp['height_min'] <= score_height < wp['height_max']:
                return i
        return len(WEATHER_PHASES) - 1

    def _draw_aurora(self, surf, frame):
        aurora_surf = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        for i in range(3):
            points = []
            base_y = 80 + i * 40
            for x in range(0, SCREEN_W + 20, 20):
                y = base_y + math.sin(x * 0.01 + frame * 0.02 + i) * 30
                points.append((x, y))
            if len(points) < 2:
                continue
            # 极光颜色
            colors = [(50, 255, 150, 25), (100, 150, 255, 20), (200, 100, 255, 15)]
            for j in range(len(points) - 1):
                pygame.draw.line(aurora_surf, colors[i], points[j], points[j+1], 8)
        surf.blit(aurora_surf, (0, 0))

    def _draw_rain(self, surf, frame, phase):
        rain_surf = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        intensity = 30 if phase == 2 else 50
        for _ in range(intensity):
            rx = random.randint(0, SCREEN_W)
            ry = random.randint(0, SCREEN_H)
            length = random.randint(8, 18)
            alpha = random.randint(30, 80)
            pygame.draw.line(rain_surf, (180, 200, 255, alpha), (rx, ry), (rx - 1, ry + length), 1)
        surf.blit(rain_surf, (0, 0))


# ── 音频管理器（增强版） ────────────────────────────────────────────────────────
class AudioManager:
    def __init__(self):
        self.muted = False
        self.music_volume = 1.0
        self.sfx_volume = 1.0
        pygame.mixer.init()

        bg_path = os.path.join(SOUND_DIR, 'bg_music.mp3')
        self._bg_loaded = False
        if os.path.exists(bg_path):
            try:
                pygame.mixer.music.load(bg_path)
                self._bg_loaded = True
                log('背景音乐加载成功')
            except Exception as e:
                log(f'背景音乐加载失败: {e}')
        else:
            log(f'背景音乐文件不存在: {bg_path}')

        # 音效映射表
        sfx_files = {
            'game_over':   'game-over.wav',
            'jump_normal': 'sfx_jump_normal.wav',
            'jump_boost':  'sfx_jump_boost.wav',
            'land':        'sfx_land.wav',
            'score_up':    'sfx_score_up.wav',
            'score_down':  'sfx_score_down.wav',
            'item_collect':'sfx_item_collect.wav',
            'shield_hit':  'sfx_shield_hit.wav',
            'combo':       'sfx_combo.wav',
            'thunder':     'sfx_thunder.wav',
            'click':       'sfx_click.wav',
        }
        self.sfx = {}
        for key, fname in sfx_files.items():
            path = os.path.join(SOUND_DIR, fname)
            if os.path.exists(path):
                try:
                    self.sfx[key] = pygame.mixer.Sound(path)
                    if key != 'game_over':
                        self.sfx[key].set_volume(0.5)
                    log(f'音效加载成功: {key}')
                except Exception as e:
                    log(f'音效加载失败 {key}: {e}')
            else:
                log(f'音效文件不存在: {path}')

    def play_bg(self):
        if not self._bg_loaded:
            return
        pygame.mixer.music.play(-1)
        vol = 0.0 if self.muted else self.music_volume
        pygame.mixer.music.set_volume(vol)

    def stop_bg(self):
        pygame.mixer.music.stop()

    def play_sfx(self, key):
        if self.muted:
            return
        sfx = self.sfx.get(key)
        if sfx:
            vol = self.sfx_volume
            sfx.set_volume(vol)
            sfx.play()

    def toggle_mute(self):
        self.muted = not self.muted
        vol = 0.0 if self.muted else self.music_volume
        pygame.mixer.music.set_volume(vol)
        log(f'静音: {self.muted}')
        return self.muted

    def set_music_volume(self, v):
        self.music_volume = max(0.0, min(1.0, v))
        if not self.muted:
            pygame.mixer.music.set_volume(self.music_volume)

    def set_sfx_volume(self, v):
        self.sfx_volume = max(0.0, min(1.0, v))


# ── 木板基类 ──────────────────────────────────────────────────────────────────
class Plank:
    def __init__(self, x, y, ptype, w, image):
        self.x     = float(x)
        self.y     = float(y)
        self.type  = ptype
        self.w     = w
        self.image = image
        self.alive = True

    def update(self):
        pass

    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, PLANK_H)

    def draw(self, surf):
        surf.blit(self.image, (int(self.x), int(self.y)))


class PlankNormal(Plank):
    pass


class PlankMoving(Plank):
    def __init__(self, x, y, w, image):
        super().__init__(x, y, TYPE_MOVING, w, image)
        speed = random.uniform(MOVING_SPEED_MIN, MOVING_SPEED_MAX)
        self.vx = speed if random.random() < 0.5 else -speed

    def update(self):
        self.x += self.vx
        if self.x < 0:
            self.x = 0
            self.vx = abs(self.vx)
        elif self.x + self.w > SCREEN_W:
            self.x = SCREEN_W - self.w
            self.vx = -abs(self.vx)


class PlankFragile(Plank):
    def __init__(self, x, y, w, image):
        super().__init__(x, y, TYPE_FRAGILE, w, image)
        self.stand_timer = 0
        self.cracking    = False
        self._flash      = 0

    def start_crack(self):
        self.cracking = True

    def update(self):
        if self.cracking:
            self.stand_timer += 1
            self._flash += 1
            if self.stand_timer >= FRAGILE_STAND_FRAMES:
                self.alive = False
        else:
            self.stand_timer = 0
            self._flash = 0

    def draw(self, surf):
        remaining = FRAGILE_STAND_FRAMES - self.stand_timer
        if self.cracking and remaining < FPS // 2:
            if (self._flash // 4) % 2 == 0:
                return
        surf.blit(self.image, (int(self.x), int(self.y)))


class PlankSpring(Plank):
    """弹簧板：弹跳高度 ×2.5"""
    def __init__(self, x, y, w, image):
        super().__init__(x, y, TYPE_SPRING, w, image)
        self.spring_anim = 0  # 弹簧动画帧

    def trigger_spring(self):
        self.spring_anim = 15

    def update(self):
        if self.spring_anim > 0:
            self.spring_anim -= 1

    def draw(self, surf):
        surf.blit(self.image, (int(self.x), int(self.y)))
        # 弹簧动画 - 在板上方画压缩效果
        if self.spring_anim > 0:
            compress = int(self.spring_anim * 0.8)
            spring_s = pygame.Surface((self.w, compress), pygame.SRCALPHA)
            pygame.draw.rect(spring_s, (255, 165, 0, 150), spring_s.get_rect(), border_radius=4)
            surf.blit(spring_s, (int(self.x), int(self.y) - compress))


class PlankIce(Plank):
    """冰板：落地后强制水平滑行"""
    def __init__(self, x, y, w, image):
        super().__init__(x, y, TYPE_ICE, w, image)
        self.slip_timer = 0
        self.slip_dir = 0

    def trigger_slip(self, facing_left):
        self.slip_timer = int(0.8 * FPS)  # 0.8 秒
        self.slip_dir = -1 if facing_left else 1

    def update(self):
        if self.slip_timer > 0:
            self.slip_timer -= 1

    @property
    def is_slipping(self):
        return self.slip_timer > 0


# ── 浮空实体 ──────────────────────────────────────────────────────────────────
class FloatingEntity:
    def __init__(self, kind, frames, x, y, vx, size, score_delta, anim_speed, margin):
        self.kind        = kind
        self.frames      = frames
        self.x           = float(x)
        self.y           = float(y)
        self.vx          = vx
        self.size        = size
        self.score_delta = score_delta
        self.anim_speed  = anim_speed
        self.margin      = margin
        self.frame_idx   = 0
        self.frame_timer = 0
        self.alive       = True

    def update(self, target_x=None, target_y=None, speed_mult=1.0):
        self.x += self.vx * speed_mult
        if self.x + self.size < 0 or self.x > SCREEN_W:
            self.alive = False
            return
        self.frame_timer += 1
        if self.frame_timer >= self.anim_speed:
            self.frame_timer = 0
            self.frame_idx = (self.frame_idx + 1) % len(self.frames)

    def draw(self, surf):
        surf.blit(self.frames[self.frame_idx], (int(self.x), int(self.y)))

    def rect(self):
        m = self.margin
        return pygame.Rect(int(self.x) + m, int(self.y) + m,
                           self.size - m * 2, self.size - m * 2)


class ChasingEntity(FloatingEntity):
    def __init__(self, kind, frames, x, y, speed, size, score_delta, anim_speed, margin):
        super().__init__(kind, frames, x, y, 0, size, score_delta, anim_speed, margin)
        self.speed = speed
        self.vy = 0.0

    def update(self, target_x=None, target_y=None, speed_mult=1.0):
        if target_x is None or target_y is None:
            self.alive = False
            return

        cx = self.x + self.size / 2
        cy = self.y + self.size / 2
        dx = target_x - cx
        dy = target_y - cy
        dist = (dx**2 + dy**2) ** 0.5

        if dist < 5:
            self.vx = self.vy = 0
        else:
            self.vx = (dx / dist) * self.speed * speed_mult
            self.vy = (dy / dist) * self.speed * speed_mult

        self.x += self.vx
        self.y += self.vy

        if (self.x + self.size < -50 or self.x > SCREEN_W + 50 or
                self.y + self.size < -50 or self.y > SCREEN_H + 50):
            self.alive = False
            return

        self.frame_timer += 1
        if self.frame_timer >= self.anim_speed:
            self.frame_timer = 0
            self.frame_idx = (self.frame_idx + 1) % len(self.frames)


# ── 道具实体 ──────────────────────────────────────────────────────────────────
class ItemEntity:
    def __init__(self, item_type, x, y):
        self.item_type = item_type
        self.x = float(x)
        self.y = float(y)
        self.vy = 0.5  # 缓缓飘下
        self.size = 36
        self.alive = True
        self.timer = 0
        self.defn = ITEM_DEFS[item_type]

    def update(self):
        self.y += self.vy
        self.timer += 1
        if self.y > SCREEN_H + 50:
            self.alive = False

    def draw(self, surf, frame):
        # 画一个发光的圆球
        cx = int(self.x) + self.size // 2
        cy = int(self.y) + self.size // 2
        # 外圈发光
        pulse = 1.0 + 0.2 * math.sin(frame * 0.1)
        glow_r = int(self.size * 0.8 * pulse)
        glow_s = pygame.Surface((glow_r * 2, glow_r * 2), pygame.SRCALPHA)
        pygame.draw.circle(glow_s, (*self.defn['color'], 40), (glow_r, glow_r), glow_r)
        surf.blit(glow_s, (cx - glow_r, cy - glow_r))
        # 主体
        pygame.draw.circle(surf, self.defn['color'], (cx, cy), self.size // 2)
        pygame.draw.circle(surf, (255, 255, 255), (cx, cy), self.size // 2, 2)
        # 字母图标
        font_s = _font(18, bold=True)
        icon = font_s.render(self.defn['icon_char'], True, (255, 255, 255))
        surf.blit(icon, (cx - icon.get_width() // 2, cy - icon.get_height() // 2))

    def rect(self):
        m = 5
        return pygame.Rect(int(self.x) + m, int(self.y) + m,
                           self.size - m * 2, self.size - m * 2)


# ── 分数弹出文字 ──────────────────────────────────────────────────────────────
class ScorePopup:
    DURATION = 55

    def __init__(self, x, y, delta, font):
        self.x     = float(x)
        self.y     = float(y)
        self.delta = delta
        self.font  = font
        self.timer = 0
        self.color = (80, 255, 100) if delta > 0 else (255, 80, 80)
        self.text  = f'+{delta}' if delta > 0 else str(delta)

    def update(self):
        self.y     -= 1.4
        self.timer += 1

    @property
    def alive(self):
        return self.timer < self.DURATION

    def draw(self, surf):
        alpha = max(0, 255 - int(255 * self.timer / self.DURATION))
        s = self.font.render(self.text, True, self.color)
        s.set_alpha(alpha)
        surf.blit(s, (int(self.x) - s.get_width() // 2, int(self.y)))


# ── 成就通知 ──────────────────────────────────────────────────────────────────
class AchievementPopup:
    DURATION = 180  # 3 秒

    def __init__(self, name, font):
        self.name = name
        self.font = font
        self.timer = 0
        self.y_offset = -60  # 从屏幕上方滑入

    def update(self):
        self.timer += 1
        if self.timer < 20:
            self.y_offset = int(-60 + 60 * (self.timer / 20))
        elif self.timer > self.DURATION - 20:
            self.y_offset = int(-60 * ((self.timer - (self.DURATION - 20)) / 20))

    @property
    def alive(self):
        return self.timer < self.DURATION

    def draw(self, surf):
        dw, dh = 340, 45
        dx = (SCREEN_W - dw) // 2
        dy = 10 + self.y_offset

        # 背景框
        bg = pygame.Surface((dw, dh), pygame.SRCALPHA)
        pygame.draw.rect(bg, (40, 30, 10, 200), bg.get_rect(), border_radius=10)
        pygame.draw.rect(bg, (255, 215, 0), bg.get_rect(), 2, border_radius=10)
        surf.blit(bg, (dx, dy))

        # 图标
        icon = self.font.render('★', True, (255, 215, 0))
        surf.blit(icon, (dx + 10, dy + dh // 2 - icon.get_height() // 2))

        # 文字
        text = self.font.render(f'成就解锁: {self.name}', True, (255, 215, 0))
        surf.blit(text, (dx + 40, dy + dh // 2 - text.get_height() // 2))


# ── 玩家提示 ──────────────────────────────────────────────────────────────────
class TipPopup:
    """底部中央弹出的提示气泡，告知玩家游戏机制"""
    DURATION = 210  # 3.5 秒

    def __init__(self, text, icon='i', color=(200, 230, 255)):
        self.text = text
        self.icon = icon
        self.color = color
        self.timer = 0
        self.y_offset = 50  # 从下方滑入

    def update(self):
        self.timer += 1
        if self.timer < 15:
            self.y_offset = int(50 - 50 * (self.timer / 15))
        elif self.timer > self.DURATION - 20:
            self.y_offset = int(50 * ((self.timer - (self.DURATION - 20)) / 20))

    @property
    def alive(self):
        return self.timer < self.DURATION

    def draw(self, surf, font_main, font_icon):
        text_surf = font_main.render(self.text, True, (255, 255, 255))
        tw, th = text_surf.get_size()
        iw = 30
        dw = tw + iw + 24
        dh = th + 16
        dx = (SCREEN_W - dw) // 2
        dy = SCREEN_H - 70 + self.y_offset

        # 背景框
        bg = pygame.Surface((dw, dh), pygame.SRCALPHA)
        pygame.draw.rect(bg, (20, 40, 80, 200), bg.get_rect(), border_radius=10)
        pygame.draw.rect(bg, (*self.color, 180), bg.get_rect(), 2, border_radius=10)
        surf.blit(bg, (dx, dy))

        # 图标
        icon_surf = font_icon.render(self.icon, True, self.color)
        surf.blit(icon_surf, (dx + 8, dy + dh // 2 - icon_surf.get_height() // 2))

        # 文字
        surf.blit(text_surf, (dx + iw + 4, dy + 8))


# ── 主角 ──────────────────────────────────────────────────────────────────────
class Cloud:
    SCROLL_THRESHOLD = SCREEN_H * 0.38

    def __init__(self, frames):
        self.frames_right = frames
        self.frames_left  = [pygame.transform.flip(f, True, False) for f in frames]
        self.frame_idx    = 0
        self.frame_timer  = 0
        self.facing_left  = False
        self.image        = frames[0]

        self.x = float(SCREEN_W // 2 - CLOUD_W // 2)
        self.y = float(SCREEN_H - 160)
        self.vx = 0.0
        self.vy = 0.0
        self.going_up = False
        self.falling  = False

        # 道具效果状态
        self.shield_active = False
        self.magnet_active = False
        self.rocket_shoes_active = False
        self.clock_active = False
        self.shrink_active = False
        self.item_timers = {}
        self.item_trail_color = None

    def do_jump(self, boosted=False):
        spd = JUMP_SPEED * (2.0 if boosted else 1.0)
        if self.rocket_shoes_active:
            spd *= 1.5
        self.vy = spd
        self.vx = 0.0
        self.going_up = True
        self.falling  = False

    def activate_item(self, item_type):
        if item_type == 'shield':
            self.shield_active = True
        elif item_type == 'magnet':
            self.magnet_active = True
            self.item_timers['magnet'] = ITEM_DEFS['magnet']['duration']
        elif item_type == 'rocket_shoes':
            self.rocket_shoes_active = True
            self.item_timers['rocket_shoes'] = ITEM_DEFS['rocket_shoes']['duration']
            self.item_trail_color = ITEM_DEFS['rocket_shoes']['color']
        elif item_type == 'clock':
            self.clock_active = True
            self.item_timers['clock'] = ITEM_DEFS['clock']['duration']
        elif item_type == 'shrink':
            self.shrink_active = True
            self.item_timers['shrink'] = ITEM_DEFS['shrink']['duration']

    def update_item_timers(self):
        expired = []
        for key in self.item_timers:
            self.item_timers[key] -= 1
            if self.item_timers[key] <= 0:
                expired.append(key)
        for key in expired:
            del self.item_timers[key]
            if key == 'magnet':
                self.magnet_active = False
            elif key == 'rocket_shoes':
                self.rocket_shoes_active = False
                self.item_trail_color = None
            elif key == 'clock':
                self.clock_active = False
            elif key == 'shrink':
                self.shrink_active = False

    def update(self, keys, wind_force=0.0, ice_slip=False, ice_slip_dir=0):
        move_mult = 1.3 if self.rocket_shoes_active else 1.0
        actual_speed = MOVE_SPEED * move_mult

        if self.going_up:
            if not ice_slip:
                if keys[pygame.K_LEFT]:
                    self.vx = max(self.vx - 1.2, -actual_speed)
                    self.facing_left = True
                elif keys[pygame.K_RIGHT]:
                    self.vx = min(self.vx + 1.2, actual_speed)
                    self.facing_left = False
                else:
                    self.vx *= 0.82
            else:
                # 冰面滑行：强制水平移动
                self.vx = ice_slip_dir * actual_speed * 0.8
                self.facing_left = ice_slip_dir < 0

        # (风力已移除，保留天气视觉效果)

        self.x += self.vx

        # 边界墙壁：允许半个身子探出，但不穿屏
        half = CLOUD_W // 2
        if self.x < -half:
            self.x = -half
            self.vx = max(self.vx, 0)
        elif self.x + CLOUD_W > SCREEN_W + half:
            self.x = SCREEN_W + half - CLOUD_W
            self.vx = min(self.vx, 0)

        self.vy += GRAVITY
        self.y  += self.vy

        if self.vy >= 0 and self.going_up:
            self.going_up = False
            self.falling  = True

        self.frame_timer += 1
        if self.frame_timer >= CLOUD_ANIM_SPEED:
            self.frame_timer = 0
            self.frame_idx = (self.frame_idx + 1) % len(self.frames_right)
        frames = self.frames_left if self.facing_left else self.frames_right
        self.image = frames[self.frame_idx]

    def rect(self):
        if self.shrink_active:
            shrink = CLOUD_W // 4
            return pygame.Rect(int(self.x) + shrink, int(self.y) + shrink,
                               CLOUD_W - shrink * 2, CLOUD_H - shrink * 2)
        return pygame.Rect(int(self.x), int(self.y), CLOUD_W, CLOUD_H)


# ── UI 按钮（增强版） ──────────────────────────────────────────────────────────
class UIButton:
    def __init__(self, rect, text, color_top, color_bot, text_color=(255, 255, 255), icon=None):
        self.rect = rect
        self.text = text
        self.color_top = color_top
        self.color_bot = color_bot
        self.text_color = text_color
        self.icon = icon
        self.hover_scale = 1.0
        self.pressed = False

    def draw(self, surf, mouse_pos, font):
        hover = self.rect.collidepoint(mouse_pos)
        target_scale = 1.05 if hover else 1.0
        self.hover_scale += (target_scale - self.hover_scale) * 0.2

        if self.pressed:
            scale = 0.95
        else:
            scale = self.hover_scale

        # 计算缩放后的矩形
        w = int(self.rect.w * scale)
        h = int(self.rect.h * scale)
        x = self.rect.centerx - w // 2
        y = self.rect.centery - h // 2
        draw_rect = pygame.Rect(x, y, w, h)

        # 阴影
        shadow_rect = draw_rect.move(3, 3)
        shadow_s = pygame.Surface((shadow_rect.w, shadow_rect.h), pygame.SRCALPHA)
        pygame.draw.rect(shadow_s, (0, 0, 0, 50), shadow_s.get_rect(), border_radius=BTN_RADIUS)
        surf.blit(shadow_s, shadow_rect.topleft)

        # 渐变按钮主体
        btn_surf = pygame.Surface((draw_rect.w, draw_rect.h), pygame.SRCALPHA)
        for row in range(draw_rect.h):
            t = row / max(1, draw_rect.h - 1)
            c = lerp_color(self.color_top, self.color_bot, t)
            if hover:
                c = tuple(min(255, int(v * 1.15)) for v in c)
            pygame.draw.line(btn_surf, c, (0, row), (draw_rect.w, row))
        surf.blit(btn_surf, draw_rect.topleft)

        # 圆角遮罩
        mask = pygame.Surface((draw_rect.w, draw_rect.h), pygame.SRCALPHA)
        pygame.draw.rect(mask, (255, 255, 255, 255), mask.get_rect(), border_radius=BTN_RADIUS)

        # 顶部高光线
        pygame.draw.line(surf, (255, 255, 255, 80) if hover else (255, 255, 255, 40),
                        (draw_rect.x + 8, draw_rect.y + 1), (draw_rect.right - 8, draw_rect.y + 1), 1)

        # 边框
        border_c = tuple(min(255, int(v * 1.3)) for v in self.color_top)
        pygame.draw.rect(surf, border_c, draw_rect, 2, border_radius=BTN_RADIUS)

        # 文字
        display_text = self.text
        if self.icon:
            display_text = f'{self.icon} {self.text}'
        text_surf = font.render(display_text, True, self.text_color)
        text_surf.set_alpha(255)
        surf.blit(text_surf, (draw_rect.centerx - text_surf.get_width() // 2,
                               draw_rect.centery - text_surf.get_height() // 2))

    def collidepoint(self, pos):
        return self.rect.collidepoint(pos)


# ── 游戏主体 ──────────────────────────────────────────────────────────────────
class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption('鬼谷无双云端冲天')
        self.clock  = pygame.time.Clock()

        try:
            hwnd = pygame.display.get_wm_info()['window']
            ctypes.windll.user32.SetForegroundWindow(hwnd)
            ctypes.windll.user32.SetFocus(hwnd)
            log('窗口强制前置成功')
        except Exception as e:
            log(f'窗口前置失败: {e}')

        self.font_title = _font(48, bold=True)
        self.font_big   = _font(30)
        self.font_small = _font(20)
        self.font_btn   = _font(22)
        self.font_popup = _font(26)
        self.font_icon  = _font(22)
        self.font_tiny  = _font(16)
        self.font_achieve = _font(18)

        self.audio = AudioManager()
        self._load_settings()
        self._load_highscore()
        self._load_achievements()
        self._load_assets()

        self._over_overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        self._over_overlay.fill((0, 0, 0, 160))

        # 粒子系统
        self.particles = ParticleSystem()

        # 视差背景
        self.bg_system = ParallaxBackground()

        # 游戏状态
        self.state = ST_MENU
        self.frame_count = 0

        # 游戏数据
        self.total_scroll = 0
        self.entity_bonus = 0
        self.game_over = False
        self.play_seconds = 0.0
        self.submit_success = False
        self.submit_message = ""
        self.combo = 0
        self.max_combo = 0
        self.combo_score_bonus = 0
        self.new_record = False

        # 风力
        self.wind_force = 0.0
        self.wind_timer = 0
        self.wind_direction = 1

        # 提示系统
        self.tips = []                # 当前活跃的提示气泡
        self._tip_shown = set()       # 已触发过的提示 key（不重复显示）

        # 道具实体
        self.items = []
        self.item_spawn_counter = 0

        # 成就通知
        self.achieve_popups = []

        # 角色和平台
        self.cloud = None
        self.planks = []
        self.entities = []
        self.popups = []

        # 初始化按钮
        self._init_menu_buttons()
        self.btn_mute = pygame.Rect(SCREEN_W - 55, 10, 45, 45)
        self.btn_settings_play = pygame.Rect(SCREEN_W - 55, 60, 45, 45)

        # 确认弹窗按钮
        self.btn_confirm = None
        self.btn_cancel = None
        self.btn_submit_ok = None

        # 设置页面滑块
        self._init_settings_ui()

        # 冰板状态
        self.ice_slip_active = False
        self.ice_slip_dir = 0

    # ── 设置持久化 ──────────────────────────────────────────────────────────
    def _load_settings(self):
        data = _load_json('settings.json', {
            'music_volume': 1.0,
            'sfx_volume': 1.0,
            'particles': True,
            'difficulty': 'normal',
        })
        self.music_volume = data.get('music_volume', 1.0)
        self.sfx_volume = data.get('sfx_volume', 1.0)
        self.particles_enabled = data.get('particles', True)
        self.difficulty = data.get('difficulty', 'normal')

    def _save_settings(self):
        _save_json('settings.json', {
            'music_volume': self.music_volume,
            'sfx_volume': self.sfx_volume,
            'particles': self.particles_enabled,
            'difficulty': self.difficulty,
        })

    def _load_highscore(self):
        # 按 role_id 分别记录每个角色的最高分
        all_hs = _load_json('highscore.json', {})
        role_data = all_hs.get(PLAYER_ID, {'score': 0, 'combo': 0, 'games': 0, 'total_score': 0})
        self.highscore = role_data.get('score', 0)
        self.highscore_combo = role_data.get('combo', 0)
        self.role_games_played = role_data.get('games', 0)
        self.role_total_score = role_data.get('total_score', 0)

    def _save_highscore(self):
        all_hs = _load_json('highscore.json', {})
        role_data = all_hs.get(PLAYER_ID, {'score': 0, 'combo': 0, 'games': 0, 'total_score': 0})
        if self.score > role_data.get('score', 0):
            role_data['score'] = self.score
            self.new_record = True
        if self.max_combo > role_data.get('combo', 0):
            role_data['combo'] = self.max_combo
        role_data['games'] = role_data.get('games', 0) + 1
        role_data['total_score'] = role_data.get('total_score', 0) + self.score
        all_hs[PLAYER_ID] = role_data
        _save_json('highscore.json', all_hs)

    def _load_achievements(self):
        data = _load_json('achievements.json', {})
        self.unlocked_achievements = data

    def _unlock_achievement(self, name):
        if name not in self.unlocked_achievements:
            self.unlocked_achievements[name] = True
            self.achieve_popups.append(AchievementPopup(name, self.font_achieve))
            self.audio.play_sfx('combo')
            _save_json('achievements.json', self.unlocked_achievements)

    def _apply_settings_to_audio(self):
        self.audio.set_music_volume(self.music_volume)
        self.audio.set_sfx_volume(self.sfx_volume)

    # ── 资源加载 ──────────────────────────────────────────────────────────────
    def _load_assets(self):
        pl = os.path.join(IMG_DIR, 'plank')

        aq = os.path.join(IMG_DIR, 'Aquafluff')
        self.cloud_frames = [
            load_img(os.path.join(aq, f'{i}.png'), CLOUD_W, CLOUD_H)
            for i in range(1, 5)
        ]

        purple_path = os.path.join(pl, 'plank_purple.png')
        if not os.path.exists(purple_path):
            purple_path = os.path.join(pl, 'e25020e35571a32027123e80514d8158_16.png')

        self.plank_src = {
            TYPE_BEIGE:   pygame.image.load(os.path.join(pl, 'plank_beige.png')).convert_alpha(),
            TYPE_PURPLE:  pygame.image.load(purple_path).convert_alpha(),
            TYPE_MOVING:  pygame.image.load(os.path.join(pl, 'plank_cyan.png')).convert_alpha(),
            TYPE_FRAGILE: pygame.image.load(os.path.join(pl, 'plank_darkbrown.png')).convert_alpha(),
            TYPE_SPRING:  pygame.image.load(os.path.join(pl, 'plank_beige.png')).convert_alpha(),  # 复用beige
            TYPE_ICE:     pygame.image.load(os.path.join(pl, 'plank_cyan.png')).convert_alpha(),     # 复用cyan
        }

        self.entity_frames = {}
        for kind, cfg in ENTITY_DEFS.items():
            d = os.path.join(IMG_DIR, cfg['img_dir'])
            files = cfg.get('frame_files') or [f'{i}.png' for i in range(1, cfg['frame_count'] + 1)]
            self.entity_frames[kind] = [
                load_img(os.path.join(d, f), cfg['size'], cfg['size'])
                for f in files
            ]
            log(f'加载 {kind} 共 {len(files)} 帧')

    # ── 按钮初始化 ──────────────────────────────────────────────────────────
    def _init_menu_buttons(self):
        cx = SCREEN_W // 2
        self.btn_start = UIButton(
            pygame.Rect(cx - BTN_W // 2, 350, BTN_W, BTN_H),
            '开始游戏', (60, 180, 120), (40, 140, 90)
        )
        self.btn_menu_settings = UIButton(
            pygame.Rect(cx - BTN_W // 2, 420, BTN_W, BTN_H),
            '设置', (80, 100, 180), (60, 80, 150)
        )

        # 游戏结束按钮
        gap = 20
        total = BTN_W * 2 + gap
        left_x = (SCREEN_W - total) // 2
        btn_y = SCREEN_H // 2 + 60
        self.btn_retry = UIButton(
            pygame.Rect(left_x, btn_y, BTN_W, BTN_H),
            '再玩一次', (60, 180, 100), (40, 150, 80)
        )
        self.btn_submit = UIButton(
            pygame.Rect(left_x + BTN_W + gap, btn_y, BTN_W, BTN_H),
            '提交成绩', (100, 100, 180), (80, 80, 150)
        )

        # 暂停菜单按钮
        self.btn_resume = UIButton(
            pygame.Rect(cx - BTN_W // 2, 280, BTN_W, BTN_H),
            '继续游戏', (60, 180, 100), (40, 150, 80)
        )
        self.btn_pause_settings = UIButton(
            pygame.Rect(cx - BTN_W // 2, 345, BTN_W, BTN_H),
            '设置', (80, 100, 180), (60, 80, 150)
        )
        self.btn_restart = UIButton(
            pygame.Rect(cx - BTN_W // 2, 410, BTN_W, BTN_H),
            '重新开始', (180, 120, 40), (150, 100, 30)
        )
        self.btn_quit = UIButton(
            pygame.Rect(cx - BTN_W // 2, 475, BTN_W, BTN_H),
            '退出游戏', (180, 60, 60), (150, 40, 40)
        )

    def _init_settings_ui(self):
        self.settings_sliders = {
            'music': {'rect': pygame.Rect(200, 250, 250, 20), 'value': self.music_volume, 'label': '音乐音量'},
            'sfx':   {'rect': pygame.Rect(200, 310, 250, 20), 'value': self.sfx_volume,   'label': '音效音量'},
        }
        self.settings_toggles = {
            'particles':  {'rect': pygame.Rect(200, 380, 50, 30), 'value': self.particles_enabled, 'label': '粒子效果'},
        }
        self.diff_buttons = {
            'easy':   pygame.Rect(150, 460, 100, 36),
            'normal': pygame.Rect(260, 460, 100, 36),
            'hard':   pygame.Rect(370, 460, 100, 36),
        }
        self.btn_settings_back = UIButton(
            pygame.Rect(SCREEN_W // 2 - 90, 540, 180, 45),
            '返回', (80, 80, 80), (60, 60, 60)
        )
        self.dragging_slider = None

    # ── 属性 ──────────────────────────────────────────────────────────────────
    @property
    def score(self):
        return max(0, int(self.total_scroll / 8) + self.entity_bonus + self.combo_score_bonus)

    @property
    def score_height(self):
        return abs(self.total_scroll)

    # ── 重置 ──────────────────────────────────────────────────────────────────
    def reset(self):
        self.total_scroll = 0
        self.entity_bonus = 0
        self.combo = 0
        self.max_combo = 0
        self.combo_score_bonus = 0
        self.game_over = False
        self.state = ST_PLAYING
        self.play_seconds = 0.0
        self.new_record = False
        self.wind_force = 0.0
        self.wind_timer = 0
        self.items = []
        self.item_spawn_counter = 0
        self.ice_slip_active = False
        self.ice_slip_dir = 0

        # 重置提示系统（每次新游戏允许重新提示）
        self.tips = []
        self._tip_shown = set()

        # 首次游戏提示
        self.tips.append(TipPopup(
            '左右方向键移动 | 高度越高天气越恶劣 | 收集道具获得增益',
            '?', (200, 255, 200)))
        self._tip_shown.add('_welcome')

        self.cloud = Cloud(self.cloud_frames)
        self.planks = []
        self.entities = []
        self.popups = []
        self.particles = ParticleSystem()

        ground_y = SCREEN_H - 130
        self._spawn_plank(SCREEN_W // 2 - 90, ground_y, TYPE_BEIGE, w=180)
        self.cloud.x = float(SCREEN_W // 2 - CLOUD_W // 2)
        self.cloud.y = float(ground_y - CLOUD_H)

        self._fill_planks_above(ground_y)
        self.cloud.do_jump()
        self.audio.play_bg()
        log('游戏重置完成')

    # ── 木板工厂 ──────────────────────────────────────────────────────────
    def _make_image(self, ptype, w):
        return pygame.transform.smoothscale(self.plank_src[ptype], (w, PLANK_H))

    def _spawn_plank(self, x, y, ptype, w=None):
        if w is None:
            if ptype == TYPE_MOVING:
                w = random.randint(MOVING_W_MIN, MOVING_W_MAX)
            else:
                w = random.randint(PLANK_W_MIN, PLANK_W_MAX)
        img = self._make_image(ptype, w)
        if ptype == TYPE_MOVING:
            self.planks.append(PlankMoving(x, y, w, img))
        elif ptype == TYPE_FRAGILE:
            self.planks.append(PlankFragile(x, y, w, img))
        elif ptype == TYPE_SPRING:
            self.planks.append(PlankSpring(x, y, w, img))
        elif ptype == TYPE_ICE:
            self.planks.append(PlankIce(x, y, w, img))
        else:
            self.planks.append(PlankNormal(x, y, ptype, w, img))

    def _random_ptype(self):
        r = random.random()
        if r < PURPLE_CHANCE:
            return TYPE_PURPLE
        r -= PURPLE_CHANCE
        if r < FRAGILE_CHANCE:
            return TYPE_FRAGILE
        r -= FRAGILE_CHANCE
        if r < SPRING_CHANCE:
            return TYPE_SPRING
        r -= SPRING_CHANCE
        if r < ICE_CHANCE:
            return TYPE_ICE
        return TYPE_BEIGE

    def _horiz_reachable(self, prev_x, prev_w, new_x, new_w):
        prev_right = prev_x + prev_w
        new_right  = new_x + new_w
        gap = max(0, max(prev_x, new_x) - min(prev_right, new_right))
        return gap <= MAX_HORIZ_REACH

    def _gen_one_plank(self, y, prev_x, prev_w):
        ptype = self._random_ptype()
        w     = random.randint(PLANK_W_MIN, PLANK_W_MAX)
        x     = random.randint(0, max(0, SCREEN_W - w))

        if not self._horiz_reachable(prev_x, prev_w, x, w):
            bridge_w = random.randint(MOVING_W_MIN, MOVING_W_MAX)
            bridge_x = int((prev_x + prev_w / 2 + x + w / 2) / 2 - bridge_w / 2)
            bridge_x = max(0, min(bridge_x, SCREEN_W - bridge_w))
            bridge_y = y + PLANK_GAP_MIN // 2
            self._spawn_plank(bridge_x, bridge_y, TYPE_MOVING, bridge_w)

        self._spawn_plank(x, y, ptype, w)
        return x, w

    def _fill_planks_above(self, from_y):
        prev_x, prev_w = SCREEN_W // 2 - 90, 180
        y = from_y - random.randint(PLANK_GAP_MIN, PLANK_GAP_MIN + 20)
        while y > -SCREEN_H * 0.5:
            prev_x, prev_w = self._gen_one_plank(y, prev_x, prev_w)
            y -= random.randint(PLANK_GAP_MIN, PLANK_GAP_MAX)

    def _ensure_planks_above(self):
        alive_planks = [p for p in self.planks if p.alive]
        if not alive_planks:
            return
        top_y     = min(p.y for p in alive_planks)
        top_plank = min(alive_planks, key=lambda p: p.y)
        prev_x, prev_w = int(top_plank.x), int(top_plank.w)
        while top_y > -SCREEN_H * 0.3:
            gap    = random.randint(PLANK_GAP_MIN, PLANK_GAP_MAX)
            top_y -= gap
            prev_x, prev_w = self._gen_one_plank(top_y, prev_x, prev_w)

    # ── 滚屏 ──────────────────────────────────────────────────────────────────
    def _scroll(self, dy):
        self.cloud.y += dy
        for p in self.planks:
            p.y += dy
        for e in self.entities:
            e.y += dy
        for pp in self.popups:
            pp.y += dy
        for item in self.items:
            item.y += dy
        self.total_scroll += dy

    # ── 天气/风力 ──────────────────────────────────────────────────────────────
    def _update_weather(self):
        weather_phase_idx = self.bg_system._get_weather_phase(self.score_height)
        if weather_phase_idx < len(WEATHER_PHASES):
            phase = WEATHER_PHASES[weather_phase_idx]

            if phase['wind']:
                self.wind_timer -= 1
                if self.wind_timer <= 0:
                    self.wind_direction = random.choice([-1, 1])
                    self.wind_force = self.wind_direction * random.uniform(0.05, 0.12)
                    self.wind_timer = random.randint(180, 300)
            else:
                self.wind_force *= 0.95  # 逐渐消失

    # ── 提示系统 ──────────────────────────────────────────────────────────────
    def _show_tip_once(self, key, text, icon='i', color=(200, 230, 255)):
        """只在 key 未触发过时才显示提示（每种提示只显示一次）"""
        if key not in self._tip_shown:
            self._tip_shown.add(key)
            self.tips.append(TipPopup(text, icon, color))

    def _check_tips(self):
        """根据游戏进程检测是否需要触发提示"""
        # 首次暴风天气
        if self.score_height >= 5000 and self.score_height < 5200:
            self._show_tip_once('storm_wind',
                '进入暴风区域! 天空变暗，注意观察周围', '~',
                (150, 200, 255))

        # 首次雷暴
        if self.score_height >= 8000 and self.score_height < 8200:
            self._show_tip_once('thunder_zone',
                '雷暴区域! 注意躲避雷云，避免大幅扣分', '!',
                (255, 150, 150))

        # 首次遭遇怪物
        monster_count = sum(1 for e in self.entities if e.kind.startswith('monster'))
        if monster_count > 0:
            self._show_tip_once('monster_warn',
                '小心! 怪物会追踪你，碰到会扣分', '!',
                (255, 100, 100))

        # 首次碰到冰板
        for p in self.planks:
            if isinstance(p, PlankIce) and p.is_slipping:
                self._show_tip_once('ice_slip',
                    '冰板会强制滑行! 无法控制方向', '*',
                    (150, 220, 255))
                break

        # 首次碰到易碎板
        for p in self.planks:
            if isinstance(p, PlankFragile) and not p.alive:
                self._show_tip_once('fragile_plank',
                    '深色木板是易碎的，踩一次就碎', '!',
                (255, 180, 100))
                break

        # 首次拿到道具
        if len(self._tip_shown) > 0 and 'item_first' not in self._tip_shown:
            if self.cloud.shield_active or self.cloud.magnet_active or \
               self.cloud.rocket_shoes_active or self.cloud.clock_active or \
               self.cloud.shrink_active:
                self._show_tip_once('item_first',
                    '获得道具! 屏幕下方会显示道具状态', '+',
                    (100, 255, 150))

        # 首次弹簧板
        for p in self.planks:
            if isinstance(p, PlankSpring) and p.spring_anim > 0:
                self._show_tip_once('spring_plank',
                    '弹簧板! 超级弹跳，一次飞很高', '^',
                    (255, 200, 100))
                break

    # ── 连击系统 ──────────────────────────────────────────────────────────────
    def _check_combo_milestones(self):
        milestones = {10: 50, 25: 150, 50: 500, 100: 2000}
        if self.combo in milestones:
            bonus = milestones[self.combo]
            self.combo_score_bonus += bonus
            cx = int(self.cloud.x + CLOUD_W / 2)
            cy = int(self.cloud.y - 20)
            self.popups.append(ScorePopup(cx, cy, bonus, self.font_popup))
            self.audio.play_sfx('combo')
            if self.particles_enabled:
                self.particles.emit_collect(cx, cy)

            # 成就检查
            if self.combo >= 25:
                self._unlock_achievement('连击新星')
            if self.combo >= 100:
                self._unlock_achievement('连击大师')

    # ── 道具生成 ──────────────────────────────────────────────────────────────
    def _try_spawn_item(self):
        self.item_spawn_counter += 1
        if self.item_spawn_counter >= random.randint(15, 25) and len(self.items) < 2:
            self.item_spawn_counter = 0
            alive_planks = [p for p in self.planks if p.alive and p.y > 0 and p.y < SCREEN_H]
            if alive_planks:
                plank = random.choice(alive_planks)
                item_type = random.choice(list(ITEM_DEFS.keys()))
                x = plank.x + plank.w / 2 - 18
                y = plank.y - 50
                self.items.append(ItemEntity(item_type, x, y))

    # ── 主更新 ────────────────────────────────────────────────────────────────
    def update(self, keys, dt):
        if self.game_over or self.state != ST_PLAYING:
            return

        self.play_seconds += dt / 1000.0

        # 道具计时
        self.cloud.update_item_timers()

        # 冰板状态
        ice_slip = False
        ice_slip_dir = 0
        if self.ice_slip_active:
            # 检查是否还在冰板上
            for p in self.planks:
                if isinstance(p, PlankIce) and p.is_slipping:
                    ice_slip = True
                    ice_slip_dir = p.slip_dir
                    break
            if not ice_slip:
                self.ice_slip_active = False

        self.cloud.update(keys, self.wind_force, ice_slip, ice_slip_dir)

        # 磁铁效果：吸附宠物
        if self.cloud.magnet_active:
            c_rect = self.cloud.rect().inflate(60, 60)
            for e in self.entities:
                if e.kind == 'pet_star_cloud' and e.alive:
                    if c_rect.colliderect(e.rect().inflate(80, 80)):
                        e.x += (self.cloud.x - e.x) * 0.05
                        e.y += (self.cloud.y - e.y) * 0.05

        if self.cloud.y < Cloud.SCROLL_THRESHOLD:
            dy = Cloud.SCROLL_THRESHOLD - self.cloud.y
            self._scroll(dy)
            self.cloud.y = Cloud.SCROLL_THRESHOLD

        for p in self.planks:
            p.update()

        self._ensure_planks_above()
        self.planks = [p for p in self.planks if p.alive and p.y < SCREEN_H + 60]

        # 道具生成
        self._try_spawn_item()

        # 木板碰撞
        if self.cloud.falling:
            c_rect = self.cloud.rect()
            cloud_bottom = self.cloud.y + CLOUD_H
            cloud_bottom_prev = cloud_bottom - self.cloud.vy

            landed_plank = None
            for p in self.planks:
                pr = p.rect()
                if (c_rect.right > pr.left and c_rect.left < pr.right and
                        cloud_bottom_prev <= pr.top + 6 and
                        cloud_bottom >= pr.top):
                    landed_plank = p
                    break

            if landed_plank is not None:
                self.cloud.y = landed_plank.y - CLOUD_H
                self.cloud.falling = False

                # 弹跳类型判断
                boosted = landed_plank.type == TYPE_PURPLE
                spring = landed_plank.type == TYPE_SPRING

                if spring:
                    spd = JUMP_SPEED * 2.5
                    if self.cloud.rocket_shoes_active:
                        spd *= 1.5
                    self.cloud.vy = spd
                    self.cloud.vx = 0.0
                    self.cloud.going_up = True
                    self.cloud.falling = False
                    if isinstance(landed_plank, PlankSpring):
                        landed_plank.trigger_spring()
                    self.audio.play_sfx('jump_boost')
                    if self.particles_enabled:
                        self.particles.emit_boost_jump(
                            int(self.cloud.x + CLOUD_W / 2),
                            int(self.cloud.y + CLOUD_H)
                        )
                else:
                    self.cloud.do_jump(boosted=boosted)
                    if boosted:
                        self.audio.play_sfx('jump_boost')
                        if self.particles_enabled:
                            self.particles.emit_boost_jump(
                                int(self.cloud.x + CLOUD_W / 2),
                                int(self.cloud.y + CLOUD_H)
                            )
                    else:
                        self.audio.play_sfx('jump_normal')
                        if self.particles_enabled:
                            self.particles.emit_jump(
                                int(self.cloud.x + CLOUD_W / 2),
                                int(self.cloud.y + CLOUD_H)
                            )

                # 冰板：触发滑行
                if isinstance(landed_plank, PlankIce):
                    landed_plank.trigger_slip(self.cloud.facing_left)
                    self.ice_slip_active = True

                # 易碎板
                if isinstance(landed_plank, PlankFragile):
                    landed_plank.start_crack()

                # 连击 +1
                self.combo += 1
                if self.combo > self.max_combo:
                    self.max_combo = self.combo
                self._check_combo_milestones()

        # 浮空实体生成
        speed_mult = 0.5 if self.cloud.clock_active else 1.0
        for kind, cfg in ENTITY_DEFS.items():
            count = sum(1 for e in self.entities if e.kind == kind)
            if count < cfg['max_count'] and random.random() < cfg['spawn_chance']:
                size = cfg['size']
                py = random.randint(int(SCREEN_H * 0.1), int(SCREEN_H * 0.75))

                if cfg.get('behavior') == 'chase':
                    from_right = random.random() < 0.5
                    px = SCREEN_W + size if from_right else -size
                    self.entities.append(ChasingEntity(
                        kind, self.entity_frames[kind],
                        px, py, cfg['speed'],
                        size, cfg['score_delta'], cfg['anim_speed'], cfg['margin']
                    ))
                else:
                    from_right = random.random() < 0.5
                    vx = random.uniform(cfg['speed_min'], cfg['speed_max'])
                    if from_right:
                        px, vx = SCREEN_W, -vx
                    else:
                        px = -size
                    self.entities.append(FloatingEntity(
                        kind, self.entity_frames[kind],
                        px, py, vx,
                        size, cfg['score_delta'], cfg['anim_speed'], cfg['margin']
                    ))

        # 实体碰撞
        c_rect = self.cloud.rect()
        target_cx = self.cloud.x + CLOUD_W / 2
        target_cy = self.cloud.y + CLOUD_H / 2
        for e in self.entities:
            e.update(target_cx, target_cy, speed_mult)
            if e.alive and c_rect.colliderect(e.rect()):
                e.alive = False
                self.entity_bonus += e.score_delta
                cx = int(e.x + e.size / 2)
                cy = int(e.y)

                if e.score_delta > 0:
                    self.audio.play_sfx('score_up')
                    if self.particles_enabled:
                        self.particles.emit_collect(cx, cy)
                else:
                    # 负分实体 - 检查护盾
                    if self.cloud.shield_active:
                        self.cloud.shield_active = False
                        self.audio.play_sfx('shield_hit')
                        if self.particles_enabled:
                            self.particles.emit_shield_block(cx, cy)
                        self.popups.append(ScorePopup(cx, cy, 0, self.font_popup))
                        self._unlock_achievement('不死之身')
                    else:
                        self.audio.play_sfx('score_down')
                        if self.particles_enabled:
                            self.particles.emit_monster_hit(cx, cy)
                        self.popups.append(ScorePopup(cx, cy, e.score_delta, self.font_popup))
                        # 碰到怪物重置连击
                        self.combo = 0
                self.popups.append(ScorePopup(cx + 20, cy, e.score_delta, self.font_popup))
        self.entities = [e for e in self.entities if e.alive]

        # 道具碰撞
        for item in self.items:
            item.update()
            if item.alive and c_rect.colliderect(item.rect()):
                item.alive = False
                self.cloud.activate_item(item.item_type)
                self.audio.play_sfx('item_collect')
                cx = int(item.x + item.size / 2)
                cy = int(item.y)
                if self.particles_enabled:
                    self.particles.emit_collect(cx, cy)
                self.popups.append(ScorePopup(cx, cy - 20, 0, self.font_popup))
                log(f'获得道具: {item.defn["name"]}')
        self.items = [item for item in self.items if item.alive]

        # 粒子
        if self.particles_enabled:
            self.particles.update()

        # 弹出文字
        for pp in self.popups:
            pp.update()
        self.popups = [pp for pp in self.popups if pp.alive]

        # 天气
        self._update_weather()
        self.bg_system.update(scroll_speed=abs(self.cloud.vy))

        # 提示检测
        self._check_tips()

        # 成就通知
        for ap in self.achieve_popups:
            ap.update()
        self.achieve_popups = [ap for ap in self.achieve_popups if ap.alive]

        # 提示气泡更新
        for tip in self.tips:
            tip.update()
        self.tips = [t for t in self.tips if t.alive]

        # 坠落结束
        if self.cloud.y > SCREEN_H + 40:
            self.game_over = True
            self.state = ST_OVER
            self.audio.stop_bg()
            self.audio.play_sfx('game_over')
            self._save_highscore()
            # 成就检查
            self._unlock_achievement('初出茅庐')
            if self.score > 1000:
                self._unlock_achievement('千分达人')
            if self.score > 10000:
                self._unlock_achievement('万分传奇')
            if self.play_seconds < 60 and self.score > 500:
                self._unlock_achievement('速通高手')
            log(f'游戏结束 得分={self.score}')

    # ── 渲染 ──────────────────────────────────────────────────────────────────
    def draw(self, mouse_pos):
        if self.state == ST_MENU:
            self._draw_menu(mouse_pos)
        elif self.state == ST_SETTINGS:
            self._draw_settings(mouse_pos)
        elif self.state == ST_PLAYING:
            self._draw_game(mouse_pos)
        elif self.state == ST_PAUSED:
            self._draw_game(mouse_pos)
            self._draw_pause_overlay(mouse_pos)
        elif self.state == ST_OVER:
            self._draw_game(mouse_pos)
            self._draw_game_over(mouse_pos)
        elif self.state == ST_CONFIRM:
            self._draw_game(mouse_pos)
            self._draw_game_over(mouse_pos)
            self._draw_confirm_dialog(mouse_pos)
        elif self.state == ST_SUBMIT_RESULT:
            self._draw_game(mouse_pos)
            self._draw_game_over(mouse_pos)
            self._draw_submit_result_dialog(mouse_pos)

    def _draw_game(self, mouse_pos):
        # 背景
        weather_phase_idx = self.bg_system._get_weather_phase(self.score_height)
        self.bg_system.draw(self.screen, self.score_height, weather_phase_idx, self.frame_count)

        # 木板
        for p in self.planks:
            p.draw(self.screen)

        # 道具
        for item in self.items:
            item.draw(self.screen, self.frame_count)

        # 浮空实体
        for e in self.entities:
            e.draw(self.screen)

        # 主角
        self.screen.blit(self.cloud.image, (int(self.cloud.x), int(self.cloud.y)))

        # 护盾光环
        if self.cloud.shield_active:
            shield_s = pygame.Surface((CLOUD_W + 20, CLOUD_H + 20), pygame.SRCALPHA)
            pulse = 1.0 + 0.15 * math.sin(self.frame_count * 0.15)
            r = int((CLOUD_W / 2 + 10) * pulse)
            pygame.draw.circle(shield_s, (255, 215, 0, 50),
                             (CLOUD_W // 2 + 10, CLOUD_H // 2 + 10), r)
            pygame.draw.circle(shield_s, (255, 215, 0, 120),
                             (CLOUD_W // 2 + 10, CLOUD_H // 2 + 10), r, 2)
            self.screen.blit(shield_s, (int(self.cloud.x) - 10, int(self.cloud.y) - 10))

        # 粒子
        if self.particles_enabled:
            self.particles.draw(self.screen)

        # 分数弹出
        for pp in self.popups:
            pp.draw(self.screen)

        # HUD
        self._draw_text_shadow(f'得分: {self.score}', self.font_big,
                               (255, 255, 255), (60, 80, 130), 12, 12)
        info = self.font_small.render(PLAYER_NAME, True, (220, 220, 255))
        self.screen.blit(info, (12, 46))

        # 连击
        if self.combo >= 3:
            combo_color = (255, 215, 0) if self.combo >= 10 else (255, 255, 255)
            self._draw_text_shadow(f'连击: {self.combo}', self.font_small,
                                   combo_color, (60, 40, 0), 12, 68)

        # 活跃道具状态条
        self._draw_active_items()

        # 提示气泡
        for tip in self.tips:
            tip.draw(self.screen, self.font_tiny, self.font_icon)

        # 静音 + 设置按钮
        self._draw_mute_btn(mouse_pos)
        self._draw_settings_btn(mouse_pos)

    def _draw_active_items(self):
        x = 10
        y = SCREEN_H - 40
        active_items = []
        if self.cloud.shield_active:
            active_items.append(('护盾', (255, 215, 0), -1))
        if self.cloud.magnet_active:
            active_items.append(('磁铁', (255, 80, 80), self.cloud.item_timers.get('magnet', 0)))
        if self.cloud.rocket_shoes_active:
            active_items.append(('火箭鞋', (255, 140, 0), self.cloud.item_timers.get('rocket_shoes', 0)))
        if self.cloud.clock_active:
            active_items.append(('时钟', (255, 255, 100), self.cloud.item_timers.get('clock', 0)))
        if self.cloud.shrink_active:
            active_items.append(('缩小', (180, 100, 255), self.cloud.item_timers.get('shrink', 0)))

        for name, color, timer in active_items:
            # 背景条
            bar_w = 80
            bar_h = 24
            bg_s = pygame.Surface((bar_w, bar_h), pygame.SRCALPHA)
            pygame.draw.rect(bg_s, (0, 0, 0, 120), bg_s.get_rect(), border_radius=6)
            self.screen.blit(bg_s, (x, y))

            # 颜色指示
            pygame.draw.rect(self.screen, color, (x, y, 4, bar_h), border_radius=2)

            # 文字
            text = self.font_tiny.render(name, True, color)
            self.screen.blit(text, (x + 8, y + (bar_h - text.get_height()) // 2))

            # 计时条
            if timer > 0:
                total = ITEM_DEFS.get({
                    '磁铁': 'magnet', '火箭鞋': 'rocket_shoes',
                    '时钟': 'clock', '缩小': 'shrink'
                }.get(name, ''), {}).get('duration', 480)
                fill = timer / total
                fill_w = int((bar_w - 8) * fill)
                pygame.draw.rect(self.screen, (*color, 100), (x + 4, y + bar_h - 4, bar_w - 8, 2))
                pygame.draw.rect(self.screen, color, (x + 4, y + bar_h - 4, fill_w, 2))

            x += bar_w + 8

    def _draw_menu(self, mouse_pos):
        # 背景
        self.bg_system.draw(self.screen, 0, 0, self.frame_count)

        # 标题
        title_pulse = 1.0 + 0.05 * math.sin(self.frame_count * 0.05)
        title_font = _font(int(48 * title_pulse), bold=True)
        self._draw_centered('云端冲天', title_font, (255, 255, 255),
                            SCREEN_W // 2, 160)
        self._draw_centered('鬼谷无双', self.font_big, (200, 210, 255),
                            SCREEN_W // 2, 220)

        # 最高分
        if self.highscore > 0:
            self._draw_centered(f'最高分: {self.highscore}', self.font_small,
                               (255, 215, 0), SCREEN_W // 2, 280)
            self._draw_centered(f'最高连击: {self.highscore_combo}', self.font_tiny,
                               (200, 200, 200), SCREEN_W // 2, 310)

        # 按钮
        self.btn_start.draw(self.screen, mouse_pos, self.font_btn)
        self.btn_menu_settings.draw(self.screen, mouse_pos, self.font_btn)

        # 操作说明
        self._draw_centered('操作: ← → 方向键移动 | ESC 暂停', self.font_tiny,
                           (180, 190, 220), SCREEN_W // 2, SCREEN_H - 60)
        self._draw_centered(f'玩家: {PLAYER_NAME}', self.font_tiny,
                           (180, 190, 220), SCREEN_W // 2, SCREEN_H - 35)

    def _draw_pause_overlay(self, mouse_pos):
        ov = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 140))
        self.screen.blit(ov, (0, 0))

        self._draw_centered('游戏暂停', self.font_big, (255, 255, 255),
                           SCREEN_W // 2, 220)
        self._draw_centered(f'得分: {self.score}', self.font_small,
                           (220, 220, 255), SCREEN_W // 2, 260)

        self.btn_resume.draw(self.screen, mouse_pos, self.font_btn)
        self.btn_pause_settings.draw(self.screen, mouse_pos, self.font_btn)
        self.btn_restart.draw(self.screen, mouse_pos, self.font_btn)
        self.btn_quit.draw(self.screen, mouse_pos, self.font_btn)

    def _draw_game_over(self, mouse_pos):
        self.screen.blit(self._over_overlay, (0, 0))
        cx = SCREEN_W // 2
        self._draw_centered('游戏结束！', self.font_big, (255, 90, 90), cx, SCREEN_H // 2 - 100)

        # 新纪录闪烁
        if hasattr(self, 'new_record') and self.new_record:
            if (self.frame_count // 30) % 2 == 0:
                self._draw_centered('新纪录！', self.font_small, (255, 215, 0), cx, SCREEN_H // 2 - 65)

        self._draw_centered(f'得分: {self.score}', self.font_big, (255, 255, 255), cx, SCREEN_H // 2 - 40)
        self._draw_centered(f'最大连击: {self.max_combo}', self.font_small,
                           (255, 215, 0) if self.max_combo >= 10 else (200, 200, 200), cx, SCREEN_H // 2 - 5)

        # 角色历史最佳
        self._draw_centered(f'── {PLAYER_NAME} 的最佳记录 ──', self.font_tiny,
                           (140, 160, 200), cx, SCREEN_H // 2 + 30)
        self._draw_centered(f'最高分: {self.highscore}    最高连击: {self.highscore_combo}    累计场次: {self.role_games_played}',
                           self.font_tiny, (180, 200, 255), cx, SCREEN_H // 2 + 52)
        if self.role_games_played > 1:
            avg = self.role_total_score // self.role_games_played
            self._draw_centered(f'场均得分: {avg}', self.font_tiny, (160, 180, 220), cx, SCREEN_H // 2 + 72)

        self.btn_retry.draw(self.screen, mouse_pos, self.font_btn)
        self.btn_submit.draw(self.screen, mouse_pos, self.font_btn)

    def _draw_settings(self, mouse_pos):
        self.screen.fill((25, 30, 50))
        self._draw_centered('游戏设置', self.font_big, (255, 255, 255), SCREEN_W // 2, 50)

        pygame.draw.line(self.screen, (60, 70, 100), (50, 90), (SCREEN_W - 50, 90), 1)

        # 滑块
        for key, slider in self.settings_sliders.items():
            label = self.font_small.render(slider['label'], True, (200, 210, 230))
            self.screen.blit(label, (50, slider['rect'].y))
            # 轨道
            r = slider['rect']
            pygame.draw.rect(self.screen, (60, 70, 90), r, border_radius=10)
            # 填充
            fill_w = int(r.w * slider['value'])
            fill_rect = pygame.Rect(r.x, r.y, fill_w, r.h)
            pygame.draw.rect(self.screen, (80, 160, 220), fill_rect, border_radius=10)
            # 滑块手柄
            handle_x = r.x + fill_w
            pygame.draw.circle(self.screen, (220, 230, 255), (handle_x, r.centery), 12)
            pygame.draw.circle(self.screen, (100, 150, 220), (handle_x, r.centery), 12, 2)
            # 数值
            val_text = self.font_tiny.render(f'{int(slider["value"] * 100)}%', True, (180, 190, 210))
            self.screen.blit(val_text, (r.right + 10, r.y))

        # 开关
        for key, toggle in self.settings_toggles.items():
            label = self.font_small.render(toggle['label'], True, (200, 210, 230))
            self.screen.blit(label, (50, toggle['rect'].y))
            tr = toggle['rect']
            bg_color = (80, 180, 100) if toggle['value'] else (80, 80, 80)
            pygame.draw.rect(self.screen, bg_color, tr, border_radius=15)
            handle_x = tr.right - 16 if toggle['value'] else tr.x + 16
            pygame.draw.circle(self.screen, (255, 255, 255), (handle_x, tr.centery), 13)

        # 难度选择
        diff_label = self.font_small.render('难度模式', True, (200, 210, 230))
        self.screen.blit(diff_label, (50, 470))
        diff_names = {'easy': '简单', 'normal': '普通', 'hard': '困难'}
        diff_colors = {'easy': ((60, 180, 100), (40, 150, 80)),
                       'normal': ((80, 100, 180), (60, 80, 150)),
                       'hard': ((180, 60, 60), (150, 40, 40))}
        for key, rect in self.diff_buttons.items():
            is_selected = (key == self.difficulty)
            c_top, c_bot = diff_colors[key]
            if is_selected:
                c_top = tuple(min(255, int(v * 1.3)) for v in c_top)
                c_bot = tuple(min(255, int(v * 1.3)) for v in c_bot)
                pygame.draw.rect(self.screen, (255, 255, 255), rect.inflate(4, 4), 2, border_radius=8)
            btn_s = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
            for row in range(rect.h):
                t = row / max(1, rect.h - 1)
                c = lerp_color(c_top, c_bot, t)
                pygame.draw.line(btn_s, c, (0, row), (rect.w, row))
            self.screen.blit(btn_s, rect.topleft)
            text = self.font_small.render(diff_names[key], True, (255, 255, 255))
            self.screen.blit(text, (rect.centerx - text.get_width() // 2,
                                    rect.centery - text.get_height() // 2))

        self.btn_settings_back.draw(self.screen, mouse_pos, self.font_btn)

    def _draw_mute_btn(self, mouse_pos):
        hover = self.btn_mute.collidepoint(mouse_pos)
        bg = (80, 80, 80, 180) if hover else (50, 50, 50, 150)
        btn_surf = pygame.Surface((self.btn_mute.w, self.btn_mute.h), pygame.SRCALPHA)
        pygame.draw.rect(btn_surf, bg, btn_surf.get_rect(), border_radius=8)
        self.screen.blit(btn_surf, self.btn_mute.topleft)
        icon = '🔇' if self.audio.muted else '🔊'
        icon_surf = self.font_icon.render(icon, True, (255, 255, 255))
        self.screen.blit(icon_surf, (
            self.btn_mute.centerx - icon_surf.get_width() // 2,
            self.btn_mute.centery - icon_surf.get_height() // 2,
        ))

    def _draw_settings_btn(self, mouse_pos):
        hover = self.btn_settings_play.collidepoint(mouse_pos)
        bg = (80, 80, 80, 180) if hover else (50, 50, 50, 150)
        btn_surf = pygame.Surface((self.btn_settings_play.w, self.btn_settings_play.h), pygame.SRCALPHA)
        pygame.draw.rect(btn_surf, bg, btn_surf.get_rect(), border_radius=8)
        self.screen.blit(btn_surf, self.btn_settings_play.topleft)
        icon_surf = self.font_icon.render('⚙', True, (200, 210, 230))
        self.screen.blit(icon_surf, (
            self.btn_settings_play.centerx - icon_surf.get_width() // 2,
            self.btn_settings_play.centery - icon_surf.get_height() // 2,
        ))

    def _draw_confirm_dialog(self, mouse_pos):
        ov = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 120))
        self.screen.blit(ov, (0, 0))

        dw, dh = 440, 230
        dx = (SCREEN_W - dw) // 2
        dy = (SCREEN_H - dh) // 2
        dlg = pygame.Surface((dw, dh), pygame.SRCALPHA)
        pygame.draw.rect(dlg, (20, 30, 70, 245), dlg.get_rect(), border_radius=16)
        pygame.draw.rect(dlg, (255, 210, 40), dlg.get_rect(), 2, border_radius=16)
        self.screen.blit(dlg, (dx, dy))

        cx = dx + dw // 2
        self._draw_centered("提交成绩确认", self.font_btn, (255, 210, 40), cx, dy + 30)
        self._draw_centered(f"本次游戏得分  {self.score}  分", self.font_small, (255, 255, 255), cx, dy + 85)
        self._draw_centered("确认提交？每日只可提交一次", self.font_small, (180, 210, 255), cx, dy + 115)

        pygame.draw.line(self.screen, (60, 80, 140), (dx + 20, dy + 148), (dx + dw - 20, dy + 148), 1)

        bw, bh, gap = 140, 42, 20
        bx0 = cx - bw - gap // 2
        bx1 = cx + gap // 2
        by  = dy + 162
        self.btn_confirm = pygame.Rect(bx0, by, bw, bh)
        self.btn_cancel  = pygame.Rect(bx1, by, bw, bh)

        hc = self.btn_confirm.collidepoint(mouse_pos)
        hx = self.btn_cancel.collidepoint(mouse_pos)
        # 确认按钮
        c_top = (200, 80, 80) if hc else (160, 60, 60)
        btn_s = pygame.Surface((bw, bh), pygame.SRCALPHA)
        for row in range(bh):
            t = row / max(1, bh - 1)
            c = lerp_color(c_top, (140, 40, 40), t)
            pygame.draw.line(btn_s, c, (0, row), (bw, row))
        self.screen.blit(btn_s, (bx0, by))
        pygame.draw.rect(self.screen, (220, 100, 100), self.btn_confirm, 2, border_radius=10)
        text = self.font_btn.render("确  认", True, (255, 255, 255))
        self.screen.blit(text, (self.btn_confirm.centerx - text.get_width() // 2,
                                self.btn_confirm.centery - text.get_height() // 2))

        # 取消按钮
        c_top = (100, 100, 100) if hx else (70, 70, 70)
        btn_s2 = pygame.Surface((bw, bh), pygame.SRCALPHA)
        for row in range(bh):
            t = row / max(1, bh - 1)
            c = lerp_color(c_top, (50, 50, 50), t)
            pygame.draw.line(btn_s2, c, (0, row), (bw, row))
        self.screen.blit(btn_s2, (bx1, by))
        pygame.draw.rect(self.screen, (120, 120, 120), self.btn_cancel, 2, border_radius=10)
        text2 = self.font_btn.render("取  消", True, (255, 255, 255))
        self.screen.blit(text2, (self.btn_cancel.centerx - text2.get_width() // 2,
                                self.btn_cancel.centery - text2.get_height() // 2))

    def _draw_submit_result_dialog(self, mouse_pos):
        ov = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 120))
        self.screen.blit(ov, (0, 0))

        dw, dh = 440, 240
        dx = (SCREEN_W - dw) // 2
        dy = (SCREEN_H - dh) // 2
        panel_color  = (20, 70, 30, 245) if self.submit_success else (70, 20, 20, 245)
        border_color = (50, 195, 75)     if self.submit_success else (210, 55, 55)
        dlg = pygame.Surface((dw, dh), pygame.SRCALPHA)
        pygame.draw.rect(dlg, panel_color,  dlg.get_rect(), border_radius=16)
        pygame.draw.rect(dlg, border_color, dlg.get_rect(), 2, border_radius=16)
        self.screen.blit(dlg, (dx, dy))

        cx = dx + dw // 2
        title = "成绩提交成功！" if self.submit_success else "成绩提交失败"
        self._draw_centered(title, self.font_btn, border_color, cx, dy + 30)

        lines = self.submit_message.split('\n')
        y_off = dy + 90
        for line in lines:
            self._draw_centered(line, self.font_small, (255, 255, 255), cx, y_off)
            y_off += 32

        pygame.draw.line(self.screen, (60, 80, 140), (dx + 20, dy + 190), (dx + dw - 20, dy + 190), 1)

        bw, bh = 160, 42
        by = dy + 204
        self.btn_submit_ok = pygame.Rect(cx - bw // 2, by, bw, bh)

        btn_s = pygame.Surface((bw, bh), pygame.SRCALPHA)
        for row in range(bh):
            t = row / max(1, bh - 1)
            c = lerp_color((160, 60, 60), (130, 40, 40), t)
            pygame.draw.line(btn_s, c, (0, row), (bw, row))
        self.screen.blit(btn_s, (cx - bw // 2, by))
        pygame.draw.rect(self.screen, (200, 80, 80), self.btn_submit_ok, 2, border_radius=10)
        text = self.font_btn.render("关  闭", True, (255, 255, 255))
        self.screen.blit(text, (self.btn_submit_ok.centerx - text.get_width() // 2,
                                self.btn_submit_ok.centery - text.get_height() // 2))

    def _draw_text_shadow(self, text, font, color, shadow_color, x, y):
        self.screen.blit(font.render(text, True, shadow_color), (x + 2, y + 2))
        self.screen.blit(font.render(text, True, color), (x, y))

    def _draw_centered(self, text, font, color, cx, y):
        surf = font.render(text, True, color)
        self.screen.blit(surf, (cx - surf.get_width() // 2, y))

    # ── 事件处理 ──────────────────────────────────────────────────────────────
    def _handle_events(self):
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            if event.type == pygame.KEYDOWN:
                self._handle_keydown(event)

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self._handle_click(event.pos)

            if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
                self.dragging_slider = None

            if event.type == pygame.MOUSEMOTION and self.dragging_slider:
                self._handle_slider_drag(event.pos)

        return mouse_pos

    def _handle_keydown(self, event):
        if event.key == pygame.K_ESCAPE:
            if self.state == ST_PLAYING:
                self.state = ST_PAUSED
            elif self.state == ST_PAUSED:
                self.state = ST_PLAYING
            elif self.state == ST_SETTINGS:
                if self.cloud is not None:
                    self.state = ST_PAUSED
                else:
                    self.state = ST_MENU
            elif self.state == ST_CONFIRM:
                self.state = ST_OVER
            elif self.state == ST_MENU:
                pygame.quit(); sys.exit()
            else:
                pygame.quit(); sys.exit()

        if event.key == pygame.K_p:
            if self.state == ST_PLAYING:
                self.state = ST_PAUSED
            elif self.state == ST_PAUSED:
                self.state = ST_PLAYING

        if event.key == pygame.K_r and self.state == ST_OVER:
            self.reset()

        if event.key == pygame.K_m:
            self.audio.toggle_mute()

    def _handle_click(self, pos):
        if self.btn_mute.collidepoint(pos):
            self.audio.toggle_mute()
            return

        if self.state == ST_MENU:
            if self.btn_start.collidepoint(pos):
                self.audio.play_sfx('click')
                self.reset()
            elif self.btn_menu_settings.collidepoint(pos):
                self.audio.play_sfx('click')
                self.state = ST_SETTINGS

        elif self.state == ST_SETTINGS:
            if self.btn_settings_back.collidepoint(pos):
                self.audio.play_sfx('click')
                self._save_settings()
                self._apply_settings_to_audio()
                if hasattr(self, 'cloud') and self.cloud:
                    self.state = ST_PAUSED
                else:
                    self.state = ST_MENU

            # 滑块点击
            for key, slider in self.settings_sliders.items():
                if slider['rect'].inflate(20, 20).collidepoint(pos):
                    self.dragging_slider = key
                    self._handle_slider_drag(pos)

            # 开关点击
            for key, toggle in self.settings_toggles.items():
                if toggle['rect'].collidepoint(pos):
                    toggle['value'] = not toggle['value']
                    if key == 'particles':
                        self.particles_enabled = toggle['value']

            # 难度选择
            for key, rect in self.diff_buttons.items():
                if rect.collidepoint(pos):
                    self.difficulty = key

        elif self.state == ST_PLAYING:
            if self.btn_settings_play.collidepoint(pos):
                self.state = ST_PAUSED

        elif self.state == ST_PAUSED:
            if self.btn_resume.collidepoint(pos):
                self.state = ST_PLAYING
            elif self.btn_pause_settings.collidepoint(pos):
                self.state = ST_SETTINGS
            elif self.btn_restart.collidepoint(pos):
                self.reset()
            elif self.btn_quit.collidepoint(pos):
                pygame.quit(); sys.exit()

        elif self.state == ST_SUBMIT_RESULT:
            if self.btn_submit_ok and self.btn_submit_ok.collidepoint(pos):
                pygame.quit(); sys.exit()

        elif self.state == ST_CONFIRM:
            if self.btn_confirm and self.btn_confirm.collidepoint(pos):
                success, msg = submit_game_result(
                    nAccountID=_args.nAccountID,
                    role_id=_args.role_id,
                    nWorldID=_args.nWorldID,
                    score=self.score,
                    play_seconds=int(self.play_seconds),
                )
                self.submit_success = success
                self.submit_message = msg
                self.state = ST_SUBMIT_RESULT
            elif self.btn_cancel and self.btn_cancel.collidepoint(pos):
                self.state = ST_OVER

        elif self.state == ST_OVER:
            if self.btn_retry.collidepoint(pos):
                self.reset()
            elif self.btn_submit.collidepoint(pos):
                self.state = ST_CONFIRM

    def _handle_slider_drag(self, pos):
        if not self.dragging_slider:
            return
        slider = self.settings_sliders[self.dragging_slider]
        r = slider['rect']
        val = (pos[0] - r.x) / r.w
        val = max(0.0, min(1.0, val))
        slider['value'] = val

        if self.dragging_slider == 'music':
            self.music_volume = val
            self.audio.set_music_volume(val)
        elif self.dragging_slider == 'sfx':
            self.sfx_volume = val
            self.audio.set_sfx_volume(val)

    # ── 主循环 ────────────────────────────────────────────────────────────────
    def run(self):
        while True:
            dt = self.clock.tick(FPS)
            self.frame_count += 1
            mouse_pos = self._handle_events()

            keys = pygame.key.get_pressed()
            self.update(keys, dt)
            self.draw(mouse_pos)

            # 成就通知（始终绘制在最上层）
            for ap in self.achieve_popups:
                ap.draw(self.screen)

            pygame.display.flip()


if __name__ == '__main__':
    Game().run()
