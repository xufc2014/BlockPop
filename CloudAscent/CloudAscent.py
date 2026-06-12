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

SKY_TOP = (131, 188, 249)
SKY_BOT = (152, 169, 230)

GRAVITY          = 0.55
JUMP_SPEED       = -14.0
MOVE_SPEED       = 5.5
CLOUD_W          = 90
CLOUD_H          = 90
CLOUD_ANIM_SPEED = 10      # 主角动画切帧间隔

PLANK_W_MIN   = 80
PLANK_W_MAX   = 170
MOVING_W_MIN  = 55   # 移动板专用宽度，更短需要技巧
MOVING_W_MAX  = 90
PLANK_H       = 30
PLANK_GAP_MIN = 110   # 最小间距
PLANK_GAP_MAX = 155   # 最大间距：严格小于最大跳高178px，留20px安全余量

# 单跳最大横向可达距离（上升25帧 × 5.5px/帧 = 140，留15px余量）
MAX_HORIZ_REACH = 125

# 木板类型
TYPE_BEIGE    = 'beige'    # 普通固定板
TYPE_PURPLE   = 'purple'   # 紫楹板：跳跃翻倍
TYPE_MOVING   = 'moving'   # 青蓝板：左右移动，出界销毁
TYPE_FRAGILE  = 'fragile'  # 玄棕板：站超1秒爆碎

PURPLE_CHANCE  = 0.10
FRAGILE_CHANCE = 0.12
# 移动板不参与随机概率池，只在横向太远时自动插入

MOVING_SPEED_MIN = 1.2
MOVING_SPEED_MAX = 2.8
FRAGILE_STAND_FRAMES = FPS  # 站1秒后爆碎（60帧）

IMG_DIR   = os.path.join(BASE_DIR, 'img')
SOUND_DIR = os.path.join(BASE_DIR, 'Sound')

BTN_W, BTN_H = 160, 50
BTN_RADIUS   = 12

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
        'speed':        2.2,      # 追踪速度（统一）
        'spawn_chance': 0.003,    # 降低出现频率（原0.004）
        'max_count':    2,        # 降低同时数量（原3）
        'anim_speed':   5,
        'margin':       12,
        'behavior':     'chase',  # 标记为追踪型
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


# ── 工具 ──────────────────────────────────────────────────────────────────────
def load_img(path, w, h):
    img = pygame.image.load(path).convert_alpha()
    return pygame.transform.smoothscale(img, (w, h))


def make_gradient_bg():
    surf = pygame.Surface((SCREEN_W, SCREEN_H))
    for y in range(SCREEN_H):
        t = y / (SCREEN_H - 1)
        r = int(SKY_TOP[0] + (SKY_BOT[0] - SKY_TOP[0]) * t)
        g = int(SKY_TOP[1] + (SKY_BOT[1] - SKY_TOP[1]) * t)
        b = int(SKY_TOP[2] + (SKY_BOT[2] - SKY_TOP[2]) * t)
        pygame.draw.line(surf, (r, g, b), (0, y), (SCREEN_W, y))
    return surf


def draw_round_rect(surf, color, rect, radius):
    pygame.draw.rect(surf, color, rect, border_radius=radius)


# ── 音频管理器 ────────────────────────────────────────────────────────────────
class AudioManager:
    """统一管理背景音乐和音效，支持全局静音切换。
    后续新增音效只需在 sfx_files 里加一行，然后调 play_sfx('key') 即可。
    """
    def __init__(self):
        self.muted = False
        pygame.mixer.init()

        # 背景音乐
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

        # 音效映射表：key → 文件名
        # 后续新增音效在这里加一行即可
        sfx_files = {
            'game_over': 'game-over.wav',
            # 'score_up':  'score_up.wav',   # 预留：加分音效
            # 'score_down':'score_down.wav',  # 预留：减分音效
            # 'land':      'land.wav',        # 预留：落板音效
            # 'boost':     'boost.wav',       # 预留：紫楹板翻倍音效
        }
        self.sfx = {}
        for key, fname in sfx_files.items():
            path = os.path.join(SOUND_DIR, fname)
            if os.path.exists(path):
                try:
                    self.sfx[key] = pygame.mixer.Sound(path)
                    log(f'音效加载成功: {key}')
                except Exception as e:
                    log(f'音效加载失败 {key}: {e}')
            else:
                log(f'音效文件不存在: {path}')

    def play_bg(self):
        """开始/重新循环播放背景音乐（静音时只是音量为0，仍然在播放）。"""
        if not self._bg_loaded:
            return
        pygame.mixer.music.play(-1)
        pygame.mixer.music.set_volume(0.0 if self.muted else 1.0)

    def stop_bg(self):
        """游戏结束时停止背景音乐（不影响静音状态）。"""
        pygame.mixer.music.stop()

    def play_sfx(self, key):
        """播放指定音效，静音时跳过。"""
        if self.muted:
            return
        sfx = self.sfx.get(key)
        if sfx:
            sfx.play()

    def toggle_mute(self):
        """切换静音：只改音量，不 stop/pause，避免 unpause 对 stopped 音乐失效。"""
        self.muted = not self.muted
        pygame.mixer.music.set_volume(0.0 if self.muted else 1.0)
        # 如果当前音乐已经 stop（游戏结束状态），静音解除也无需自动重播
        log(f'静音: {self.muted}')
        return self.muted


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
        pass   # 子类重写

    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), self.w, PLANK_H)

    def draw(self, surf):
        surf.blit(self.image, (int(self.x), int(self.y)))


class PlankNormal(Plank):
    """普通固定板 / 紫楹板：不动。"""
    pass


class PlankMoving(Plank):
    """青蓝板：左右匀速移动，碰到边界反弹。"""
    def __init__(self, x, y, w, image):
        super().__init__(x, y, TYPE_MOVING, w, image)
        speed = random.uniform(MOVING_SPEED_MIN, MOVING_SPEED_MAX)
        self.vx = speed if random.random() < 0.5 else -speed

    def update(self):
        self.x += self.vx
        if self.x < 0:
            self.x = 0
            self.vx = abs(self.vx)   # 反弹向右
        elif self.x + self.w > SCREEN_W:
            self.x = SCREEN_W - self.w
            self.vx = -abs(self.vx)  # 反弹向左


class PlankFragile(Plank):
    """玄棕板：玩家站上去超过1秒后爆碎。"""
    def __init__(self, x, y, w, image):
        super().__init__(x, y, TYPE_FRAGILE, w, image)
        self.stand_timer = 0      # 玩家站在上面的帧计数
        self.cracking    = False  # 是否已开始倒计时
        self._flash      = 0      # 闪烁计时，用于视觉提示

    def start_crack(self):
        self.cracking = True

    def update(self):
        if self.cracking:
            self.stand_timer += 1
            self._flash += 1
            if self.stand_timer >= FRAGILE_STAND_FRAMES:
                self.alive = False
        else:
            # 不站就重置
            self.stand_timer = 0
            self._flash = 0

    def draw(self, surf):
        # 最后0.5秒快速闪烁提示即将爆碎
        remaining = FRAGILE_STAND_FRAMES - self.stand_timer
        if self.cracking and remaining < FPS // 2:
            if (self._flash // 4) % 2 == 0:
                return   # 闪烁：跳过绘制
        surf.blit(self.image, (int(self.x), int(self.y)))


# ── 浮空实体（pet / monster） ─────────────────────────────────────────────────
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

    def update(self, target_x=None, target_y=None):
        self.x += self.vx
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
    """追踪型实体：朝主角方向移动，离屏销毁。"""
    def __init__(self, kind, frames, x, y, speed, size, score_delta, anim_speed, margin):
        super().__init__(kind, frames, x, y, 0, size, score_delta, anim_speed, margin)
        self.speed = speed
        self.vy = 0.0

    def update(self, target_x=None, target_y=None):
        if target_x is None or target_y is None:
            self.alive = False
            return

        # 计算朝向主角的单位向量
        cx = self.x + self.size / 2
        cy = self.y + self.size / 2
        dx = target_x - cx
        dy = target_y - cy
        dist = (dx**2 + dy**2) ** 0.5

        if dist < 5:  # 贴脸时停止
            self.vx = self.vy = 0
        else:
            self.vx = (dx / dist) * self.speed
            self.vy = (dy / dist) * self.speed

        self.x += self.vx
        self.y += self.vy

        # 离开屏幕范围销毁（不只左右，上下也算）
        if (self.x + self.size < -50 or self.x > SCREEN_W + 50 or
                self.y + self.size < -50 or self.y > SCREEN_H + 50):
            self.alive = False
            return

        # 帧动画
        self.frame_timer += 1
        if self.frame_timer >= self.anim_speed:
            self.frame_timer = 0
            self.frame_idx = (self.frame_idx + 1) % len(self.frames)


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


# ── 主角 ──────────────────────────────────────────────────────────────────────
class Cloud:
    SCROLL_THRESHOLD = SCREEN_H * 0.38

    def __init__(self, frames):
        self.frames_right = frames                                       # 原始朝右帧
        self.frames_left  = [pygame.transform.flip(f, True, False)      # 水平翻转朝左
                             for f in frames]
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

    def do_jump(self, boosted=False):
        spd = JUMP_SPEED * (2.0 if boosted else 1.0)
        self.vy = spd
        self.vx = 0.0
        self.going_up = True
        self.falling  = False

    def update(self, keys):
        if self.going_up:
            if keys[pygame.K_LEFT]:
                self.vx = max(self.vx - 1.2, -MOVE_SPEED)
                self.facing_left = True
            elif keys[pygame.K_RIGHT]:
                self.vx = min(self.vx + 1.2, MOVE_SPEED)
                self.facing_left = False
            else:
                self.vx *= 0.82

        self.x += self.vx

        if self.x > SCREEN_W:
            self.x = -CLOUD_W
        elif self.x + CLOUD_W < 0:
            self.x = SCREEN_W

        self.vy += GRAVITY
        self.y  += self.vy

        if self.vy >= 0 and self.going_up:
            self.going_up = False
            self.falling  = True

        # 帧动画 + 朝向选帧
        self.frame_timer += 1
        if self.frame_timer >= CLOUD_ANIM_SPEED:
            self.frame_timer = 0
            self.frame_idx = (self.frame_idx + 1) % len(self.frames_right)
        frames = self.frames_left if self.facing_left else self.frames_right
        self.image = frames[self.frame_idx]

    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), CLOUD_W, CLOUD_H)


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

        self.font_big   = _font(30)
        self.font_small = _font(20)
        self.font_btn   = _font(22)
        self.font_popup = _font(26)
        self.font_icon  = _font(22)

        self.audio = AudioManager()
        self._load_assets()

        self._over_overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        self._over_overlay.fill((0, 0, 0, 160))

        gap    = 20
        total  = BTN_W * 2 + gap
        left_x = (SCREEN_W - total) // 2
        btn_y  = SCREEN_H // 2 + 60
        self.btn_retry  = pygame.Rect(left_x,               btn_y, BTN_W, BTN_H)
        self.btn_submit = pygame.Rect(left_x + BTN_W + gap,  btn_y, BTN_W, BTN_H)

        # 静音按钮：右上角，固定位置
        self.btn_mute = pygame.Rect(SCREEN_W - 50, 10, 40, 40)

        # 提交成绩相关状态
        # ST_PLAYING → ST_OVER → ST_CONFIRM → ST_SUBMIT_RESULT
        self.ST_PLAYING       = "playing"
        self.ST_OVER          = "over"
        self.ST_CONFIRM       = "confirm"
        self.ST_SUBMIT_RESULT = "submit_result"

        self.state          = self.ST_PLAYING
        self.play_seconds   = 0.0
        self.submit_success = False
        self.submit_message = ""

        # 确认弹窗按钮
        self.btn_confirm       = None
        self.btn_cancel        = None
        self.btn_submit_ok     = None

        self.reset()
        self.audio.play_bg()

    # ── 资源加载 ──────────────────────────────────────────────────────────────
    def _load_assets(self):
        pl = os.path.join(IMG_DIR, 'plank')

        # 主角 Aquafluff 4帧
        aq = os.path.join(IMG_DIR, 'Aquafluff')
        self.cloud_frames = [
            load_img(os.path.join(aq, f'{i}.png'), CLOUD_W, CLOUD_H)
            for i in range(1, 5)
        ]

        # 紫楹板原图（备用哈希文件名）
        purple_path = os.path.join(pl, 'plank_purple.png')
        if not os.path.exists(purple_path):
            purple_path = os.path.join(pl, 'e25020e35571a32027123e80514d8158_16.png')

        # 原始未缩放的木板源图（Plank 构造时按宽度缩放）
        self.plank_src = {
            TYPE_BEIGE:   pygame.image.load(os.path.join(pl, 'plank_beige.png')).convert_alpha(),
            TYPE_PURPLE:  pygame.image.load(purple_path).convert_alpha(),
            TYPE_MOVING:  pygame.image.load(os.path.join(pl, 'plank_cyan.png')).convert_alpha(),
            TYPE_FRAGILE: pygame.image.load(os.path.join(pl, 'plank_darkbrown.png')).convert_alpha(),
        }

        self.bg = make_gradient_bg()

        # 浮空实体帧
        self.entity_frames = {}
        for kind, cfg in ENTITY_DEFS.items():
            d = os.path.join(IMG_DIR, cfg['img_dir'])
            files = cfg.get('frame_files') or [f'{i}.png' for i in range(1, cfg['frame_count'] + 1)]
            self.entity_frames[kind] = [
                load_img(os.path.join(d, f), cfg['size'], cfg['size'])
                for f in files
            ]
            log(f'加载 {kind} 共 {len(files)} 帧')

    # ── 重置 ──────────────────────────────────────────────────────────────────
    def reset(self):
        self.total_scroll = 0
        self.entity_bonus = 0
        self.game_over    = False
        self.state        = self.ST_PLAYING
        self.play_seconds = 0.0

        self.cloud    = Cloud(self.cloud_frames)
        self.planks   = []
        self.entities = []
        self.popups   = []

        ground_y = SCREEN_H - 130
        self._spawn_plank(SCREEN_W // 2 - 90, ground_y, TYPE_BEIGE, w=180)

        self.cloud.x = float(SCREEN_W // 2 - CLOUD_W // 2)
        self.cloud.y = float(ground_y - CLOUD_H)

        self._fill_planks_above(ground_y)
        self.cloud.do_jump()
        self.audio.play_bg()
        log('游戏重置完成')

    @property
    def score(self):
        return max(0, int(self.total_scroll / 8) + self.entity_bonus)

    # ── 木板工厂 ──────────────────────────────────────────────────────────────
    def _make_image(self, ptype, w):
        return pygame.transform.smoothscale(self.plank_src[ptype], (w, PLANK_H))

    def _spawn_plank(self, x, y, ptype, w=None):
        if w is None:
            # 移动板用独立的（更小）宽度范围
            if ptype == TYPE_MOVING:
                w = random.randint(MOVING_W_MIN, MOVING_W_MAX)
            else:
                w = random.randint(PLANK_W_MIN, PLANK_W_MAX)
        img = self._make_image(ptype, w)
        if ptype == TYPE_MOVING:
            self.planks.append(PlankMoving(x, y, w, img))
        elif ptype == TYPE_FRAGILE:
            self.planks.append(PlankFragile(x, y, w, img))
        else:
            self.planks.append(PlankNormal(x, y, ptype, w, img))

    def _random_ptype(self):
        r = random.random()
        if r < PURPLE_CHANCE:
            return TYPE_PURPLE
        r -= PURPLE_CHANCE
        if r < FRAGILE_CHANCE:
            return TYPE_FRAGILE
        return TYPE_BEIGE

    def _horiz_reachable(self, prev_x, prev_w, new_x, new_w):
        """判断从上一块板能否横向跳到新板（板面边缘间距 <= MAX_HORIZ_REACH）。"""
        prev_right = prev_x + prev_w
        new_right  = new_x + new_w
        gap = max(0, max(prev_x, new_x) - min(prev_right, new_right))
        return gap <= MAX_HORIZ_REACH

    def _gen_one_plank(self, y, prev_x, prev_w):
        """生成一块板。若随机位置横向不可达，自动插入移动板作为跳板。"""
        ptype = self._random_ptype()
        w     = random.randint(PLANK_W_MIN, PLANK_W_MAX)
        x     = random.randint(0, max(0, SCREEN_W - w))

        # 检测横向是否可达
        if not self._horiz_reachable(prev_x, prev_w, x, w):
            # 在两板之间竖向中点插一块移动板
            bridge_w = random.randint(MOVING_W_MIN, MOVING_W_MAX)
            # 移动板初始位置放在两板横向中间
            bridge_x = int((prev_x + prev_w / 2 + x + w / 2) / 2 - bridge_w / 2)
            bridge_x = max(0, min(bridge_x, SCREEN_W - bridge_w))
            bridge_y = y + PLANK_GAP_MIN // 2   # 在当前板下方一半间距处（世界坐标往下=y大）
            self._spawn_plank(bridge_x, bridge_y, TYPE_MOVING, bridge_w)
            log(f'横向过远 自动插入移动板 bridge_x={bridge_x} bridge_y={bridge_y}')

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
        self.total_scroll += dy

    # ── 主更新 ────────────────────────────────────────────────────────────────
    def update(self, keys, dt):
        if self.game_over:
            return

        self.play_seconds += dt / 1000.0
        self.cloud.update(keys)

        if self.cloud.y < Cloud.SCROLL_THRESHOLD:
            dy = Cloud.SCROLL_THRESHOLD - self.cloud.y
            self._scroll(dy)
            self.cloud.y = Cloud.SCROLL_THRESHOLD

        # 木板更新（移动、易碎计时）
        for p in self.planks:
            p.update()

        self._ensure_planks_above()
        # 清理：出屏幕下方 或 已销毁
        self.planks = [p for p in self.planks if p.alive and p.y < SCREEN_H + 60]

        # 木板碰撞（仅下落阶段）
        if self.cloud.falling:
            c_rect            = self.cloud.rect()
            cloud_bottom      = self.cloud.y + CLOUD_H
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
                self.cloud.y       = landed_plank.y - CLOUD_H
                self.cloud.falling = False
                boosted = (landed_plank.type == TYPE_PURPLE)
                if boosted:
                    log(f'踩中紫楹木！跳跃翻倍 得分={self.score}')
                self.cloud.do_jump(boosted=boosted)

                # 易碎板：踩上去开始倒计时
                if isinstance(landed_plank, PlankFragile):
                    landed_plank.start_crack()
                    log('踩上易碎板，开始倒计时')

            # 如果踩着的易碎板已经炸了（理论上下帧才销毁，这里不影响）
        else:
            # 站在某块板上（going_up=False, falling=False = 刚落地瞬间，已由do_jump接管）
            # 易碎板：如果玩家不在空中且站在其上，持续累计
            # 实际上 do_jump 会立即让玩家再起跳，所以 fragile 的倒计时逻辑
            # 在 update() 里每帧调用 p.update() 即可，start_crack 已在落地时触发
            pass

        # 浮空实体生成
        for kind, cfg in ENTITY_DEFS.items():
            count = sum(1 for e in self.entities if e.kind == kind)
            if count < cfg['max_count'] and random.random() < cfg['spawn_chance']:
                size = cfg['size']
                py = random.randint(int(SCREEN_H * 0.1), int(SCREEN_H * 0.75))

                if cfg.get('behavior') == 'chase':
                    # 追踪型：从屏幕边缘随机位置出现
                    from_right = random.random() < 0.5
                    px = SCREEN_W + size if from_right else -size
                    self.entities.append(ChasingEntity(
                        kind, self.entity_frames[kind],
                        px, py, cfg['speed'],
                        size, cfg['score_delta'], cfg['anim_speed'], cfg['margin']
                    ))
                    log(f'{kind}(追踪型) 出现 x={px:.0f}')
                else:
                    # 普通横向移动型
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
                    tag = '+奖励' if cfg['score_delta'] > 0 else '-惩罚'
                    log(f'{kind}({tag}) 出现 x={px:.0f} vx={vx:.2f}')

        # 实体碰撞
        c_rect = self.cloud.rect()
        target_cx = self.cloud.x + CLOUD_W / 2
        target_cy = self.cloud.y + CLOUD_H / 2
        for e in self.entities:
            e.update(target_cx, target_cy)
            if e.alive and c_rect.colliderect(e.rect()):
                e.alive = False
                e.alive = False
                self.entity_bonus += e.score_delta
                cx = int(e.x + e.size / 2)
                cy = int(e.y)
                self.popups.append(ScorePopup(cx, cy, e.score_delta, self.font_popup))
                sign = '+' if e.score_delta > 0 else ''
                log(f'碰到 {e.kind}！{sign}{e.score_delta}分 当前总分={self.score}')
        self.entities = [e for e in self.entities if e.alive]

        # 弹出文字
        for pp in self.popups:
            pp.update()
        self.popups = [pp for pp in self.popups if pp.alive]

        # 坠落结束
        if self.cloud.y > SCREEN_H + 40:
            self.game_over = True
            self.state     = self.ST_OVER
            self.audio.stop_bg()
            self.audio.play_sfx('game_over')
            log(f'游戏结束 得分={self.score}')

    # ── 渲染 ──────────────────────────────────────────────────────────────────
    def draw(self, mouse_pos):
        self.screen.blit(self.bg, (0, 0))

        for p in self.planks:
            p.draw(self.screen)

        for e in self.entities:
            e.draw(self.screen)

        self.screen.blit(self.cloud.image, (int(self.cloud.x), int(self.cloud.y)))

        for pp in self.popups:
            pp.draw(self.screen)

        self._draw_text_shadow(f'得分: {self.score}', self.font_big,
                               (255, 255, 255), (60, 80, 130), 12, 12)
        info = self.font_small.render(PLAYER_NAME, True, (220, 220, 255))
        self.screen.blit(info, (12, 46))

        # 静音按钮（右上角，始终显示）
        self._draw_mute_btn(mouse_pos)

        if self.game_over:
            self.screen.blit(self._over_overlay, (0, 0))
            cx = SCREEN_W // 2
            self._draw_centered('游戏结束！',           self.font_big, (255, 90, 90),   cx, SCREEN_H // 2 - 90)
            self._draw_centered(f'得分: {self.score}',  self.font_big, (255, 255, 255), cx, SCREEN_H // 2 - 30)

            hover_r = self.btn_retry.collidepoint(mouse_pos)
            self._draw_btn(self.btn_retry,  '再玩一次',
                           (60, 180, 100) if hover_r else (40, 150, 80), (255, 255, 255))

            hover_s = self.btn_submit.collidepoint(mouse_pos)
            self._draw_btn(self.btn_submit, '提交成绩',
                           (100, 100, 180) if hover_s else (80, 80, 150), (220, 220, 255))

        if self.state == self.ST_CONFIRM:
            self._draw_confirm_dialog(mouse_pos)
        elif self.state == self.ST_SUBMIT_RESULT:
            self._draw_submit_result_dialog(mouse_pos)

    def _draw_mute_btn(self, mouse_pos):
        """右上角静音按钮：🔊 / 🔇，悬停高亮。"""
        hover = self.btn_mute.collidepoint(mouse_pos)
        bg    = (80, 80, 80, 180) if hover else (50, 50, 50, 150)
        # 半透明圆角背景
        btn_surf = pygame.Surface((self.btn_mute.w, self.btn_mute.h), pygame.SRCALPHA)
        pygame.draw.rect(btn_surf, bg, btn_surf.get_rect(), border_radius=8)
        self.screen.blit(btn_surf, self.btn_mute.topleft)
        # 图标文字
        icon = '🔇' if self.audio.muted else '🔊'
        icon_surf = self.font_icon.render(icon, True, (255, 255, 255))
        self.screen.blit(icon_surf, (
            self.btn_mute.centerx - icon_surf.get_width() // 2,
            self.btn_mute.centery - icon_surf.get_height() // 2,
        ))

    def _draw_btn(self, rect, text, bg_color, text_color):
        draw_round_rect(self.screen, bg_color, rect, BTN_RADIUS)
        surf = self.font_btn.render(text, True, text_color)
        self.screen.blit(surf, (rect.centerx - surf.get_width() // 2,
                                rect.centery - surf.get_height() // 2))

    def _draw_text_shadow(self, text, font, color, shadow_color, x, y):
        self.screen.blit(font.render(text, True, shadow_color), (x + 2, y + 2))
        self.screen.blit(font.render(text, True, color),        (x,     y))

    def _draw_centered(self, text, font, color, cx, y):
        surf = font.render(text, True, color)
        self.screen.blit(surf, (cx - surf.get_width() // 2, y))

    def _draw_confirm_dialog(self, mouse_pos):
        # 遮罩
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

        pygame.draw.line(self.screen, (60, 80, 140),
                         (dx + 20, dy + 148), (dx + dw - 20, dy + 148), 1)

        bw, bh, gap = 140, 42, 20
        bx0 = cx - bw - gap // 2
        bx1 = cx + gap // 2
        by  = dy + 162
        self.btn_confirm = pygame.Rect(bx0, by, bw, bh)
        self.btn_cancel  = pygame.Rect(bx1, by, bw, bh)

        hc = self.btn_confirm.collidepoint(mouse_pos)
        hx = self.btn_cancel.collidepoint(mouse_pos)
        self._draw_btn(self.btn_confirm, "确  认", (160, 60, 60) if not hc else (200, 80, 80), (255, 255, 255))
        self._draw_btn(self.btn_cancel,  "取  消", (70, 70, 70)  if not hx else (100, 100, 100), (255, 255, 255))

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

        pygame.draw.line(self.screen, (60, 80, 140),
                         (dx + 20, dy + 190), (dx + dw - 20, dy + 190), 1)

        bw, bh = 160, 42
        by = dy + 204
        self.btn_submit_ok = pygame.Rect(cx - bw // 2, by, bw, bh)
        hok = self.btn_submit_ok.collidepoint(mouse_pos)
        self._draw_btn(self.btn_submit_ok, "关  闭",
                       (160, 60, 60) if not hok else (200, 80, 80), (255, 255, 255))

    # ── 主循环 ────────────────────────────────────────────────────────────────
    def run(self):
        prev_left = prev_right = False

        while True:
            dt        = self.clock.tick(FPS)
            mouse_pos = pygame.mouse.get_pos()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit(); sys.exit()

                if event.type == pygame.ACTIVEEVENT:
                    if event.state & 2:
                        log(f'键盘焦点: {"获得" if event.gain else "失去"}')
                    if event.state & 1:
                        log(f'鼠标焦点: {"获得" if event.gain else "失去"}')

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.state == self.ST_CONFIRM:
                            self.state = self.ST_OVER
                        else:
                            pygame.quit(); sys.exit()
                    if event.key == pygame.K_r and self.state == self.ST_OVER:
                        log('R键 重新开始')
                        self.reset()
                    if event.key == pygame.K_m:
                        self.audio.toggle_mute()

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.btn_mute.collidepoint(event.pos):
                        self.audio.toggle_mute()
                    elif self.state == self.ST_SUBMIT_RESULT:
                        if self.btn_submit_ok and self.btn_submit_ok.collidepoint(event.pos):
                            pygame.quit(); sys.exit()
                    elif self.state == self.ST_CONFIRM:
                        if self.btn_confirm and self.btn_confirm.collidepoint(event.pos):
                            success, msg = submit_game_result(
                                nAccountID=_args.nAccountID,
                                role_id=_args.role_id,
                                nWorldID=_args.nWorldID,
                                score=self.score,
                                play_seconds=int(self.play_seconds),
                            )
                            self.submit_success = success
                            self.submit_message = msg
                            self.state = self.ST_SUBMIT_RESULT
                        elif self.btn_cancel and self.btn_cancel.collidepoint(event.pos):
                            self.state = self.ST_OVER
                    elif self.state == self.ST_OVER:
                        if self.btn_retry.collidepoint(event.pos):
                            log('点击「再玩一次」')
                            self.reset()
                        elif self.btn_submit.collidepoint(event.pos):
                            log('点击「提交成绩」')
                            self.state = self.ST_CONFIRM

            keys = pygame.key.get_pressed()
            if DEBUG:
                if keys[pygame.K_LEFT]  and not prev_left:  log('左方向键 按下')
                if not keys[pygame.K_LEFT]  and prev_left:  log('左方向键 释放')
                if keys[pygame.K_RIGHT] and not prev_right: log('右方向键 按下')
                if not keys[pygame.K_RIGHT] and prev_right: log('右方向键 释放')
            prev_left  = bool(keys[pygame.K_LEFT])
            prev_right = bool(keys[pygame.K_RIGHT])

            self.update(keys, dt)
            self.draw(mouse_pos)
            pygame.display.flip()


if __name__ == '__main__':
    Game().run()
