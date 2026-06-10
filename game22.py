# -*- coding: utf-8 -*-
import pygame
import sys
import os
import random
import math
import argparse
import hashlib
import calendar
import time
import json
import requests
from urllib import parse


def resource_path(relative_path):
    """兼容开发环境、PyInstaller、Nuitka 单文件模式的资源路径"""
    try:
        # PyInstaller onefile: 解压到 sys._MEIPASS 临时目录
        base_path = sys._MEIPASS
    except AttributeError:
        # Nuitka onefile: __file__ 指向临时解压目录
        # 开发环境: __file__ 指向源码所在目录
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


# ══════════════════════════════════════════════════════════
# 邮件发送接口
# ══════════════════════════════════════════════════════════
def send_email2(UserID, WorldID, ActorID, GoodsID, Quantity, score=0, play_seconds=0):
    """
    内网邮件发送接口（app_key 找阿江要）
    内网地址：http://gameapi.test.q1.com/api/Game/SendGameAwardsEmail
    正式地址：http://gameapi.q1.com/api/Game/SendGameAwardsEmail
    返回值：(success: bool, message: str)
    """
    url = "http://gameapi.q1.com/api/Game/SendGameAwardsEmail?"

    data = {
        "GameID":      6,
        "UserID":      UserID,
        "WorldID":     WorldID,
        "ActorID":     ActorID,
        "GoodsID":     GoodsID,
        "Quantity":    Quantity,
        "EmailTopic":  "休闲时刻",
        "EmailText":   (
            f"感谢您参与鬼谷无双休闲小休息，"
            f"游戏时长{play_seconds}秒，"
            f"你本次的游戏积分为{score}，"
            f"请及时领取您的奖励，祝您游戏愉快。"
        ),
        "LifeTimeLong": 1,
        "Timestamp":   calendar.timegm(time.gmtime()),
        "limitKey":    "game_gxbb",
    }

    app_key = "*@!szgla#bc%~D118109D-1678-47CE-ACC3-5685B6F603BE*"

    sign_for_md5 = (
        f"gameid=6&worldid={data['WorldID']}&userid={data['UserID']}"
        f"&actorid={data['ActorID']}&goodsid={data['GoodsID']}"
        f"&quantity={data['Quantity']}&emailtopic={data['EmailTopic']}"
        f"&emailtext={data['EmailText']}&lifetimelong={data['LifeTimeLong']}"
        f"&timestamp={data['Timestamp']}&app_key={app_key}"
    )

    # print("[邮件] 签名原文：", sign_for_md5)
    sign = hashlib.md5(sign_for_md5.encode()).hexdigest()
    # print("[邮件] MD5签名：", sign)

    data["Sign"] = sign
    new_url = url + parse.urlencode(data)
    # print("[邮件] 请求URL：", new_url)

    try:
        res = requests.get(url=new_url, timeout=10)
        # print("[邮件] 响应原文：", res.text)
        if res.json().get("code") == 1:
            # print("[邮件] 发送成功：", res.json().get("message"))
            return True, "游戏奖励已发送，请2分钟后在游戏内的邮件查看"
        else:
            # print("[邮件] 发送失败：", res.json())
            return False, "奖励发放失败，请联系GM"
    except Exception as e:
        # print("[邮件] 请求异常：", e)
        return False, f"奖励发放失败，请联系GM\n({e})"


def _show_popup(title, message):
    """用 tkinter 弹出提示框（不阻塞 pygame 主线程之外的资源）"""
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        if title == "成功":
            messagebox.showinfo(title, message, parent=root)
        else:
            messagebox.showerror(title, message, parent=root)
        root.destroy()
    except Exception as e:
        print(f"[弹窗] {title}: {message} (tkinter 不可用: {e})")
    # 点击确定后关闭游戏窗口
    pygame.quit()
    sys.exit()



# ══════════════════════════════════════════════════════════
# 命令行参数解析（外部调用传入）
# 用法示例：
#   python game.py --role_id 10001 --role_name 张三 --level 100 --vip_lv 3
#   python game.py --nAccountID 999 --role_id 10001 --role_name 张三 --nWorldID 1 --level 100 --vip_lv 3
# ══════════════════════════════════════════════════════════
def _parse_args():
    parser = argparse.ArgumentParser(description="动物连连看")
    parser.add_argument("--nAccountID",  default="0",  help="账号ID")
    parser.add_argument("--role_id",   default="0",  help="角色ID")
    parser.add_argument("--role_name", default="",   help="角色名")
    parser.add_argument("--nWorldID",  default="0",  help="服务器ID")
    parser.add_argument("--level",     default="0",  help="角色等级")
    parser.add_argument("--vip_lv",    default="0",  help="VIP等级")
    return parser.parse_args()

_args = _parse_args()

# 校验：role_id 为 0 或空则拒绝启动
if not _args.role_id or _args.role_id == "0":
    # 用一个简单的 Tk 弹窗提示错误（不依赖 pygame 初始化）
    try:
        import tkinter as tk
        from tkinter import messagebox
        _root = tk.Tk(); _root.withdraw()
        messagebox.showerror("启动失败", "启动失败，请通过游戏内启动。")
        _root.destroy()
    except Exception:
        pass
    sys.exit(1)

# ══════════════════════════════════════════════════════════
# 玩家信息（从参数中读取）
# ══════════════════════════════════════════════════════════
PLAYER_NAME  = _args.role_name or "未知角色"
PLAYER_ID    = _args.role_id
PLAYER_LEVEL = int(_args.level)  if _args.level.isdigit()  else 0
PLAYER_VIP   = int(_args.vip_lv) if _args.vip_lv.isdigit() else 0
nAccountID     = _args.nAccountID
WORLD_ID     = _args.nWorldID

# 版本配置：控制每关道具次数（自动消除 / 洗牌 / 提示）
# GAME_VERSION 根据传入的 vip_lv 动态决定，V1~V11 对应 vip 1~11，超出范围取 V11
GAME_VERSION = f"V{min(max(PLAYER_VIP, 1), 11)}"
TOOL_CONFIG  = {
    "V1": {"auto": 1,  "shuffle": 1,  "hint": 1},
    "V2": {"auto": 2,  "shuffle": 1,  "hint": 1},
    "V3": {"auto": 3,  "shuffle": 1,  "hint": 1},
	"V4": {"auto": 3,  "shuffle": 1,  "hint": 1},
	"V5": {"auto": 3,  "shuffle": 1,  "hint": 1},
	"V6": {"auto": 4,  "shuffle": 1,  "hint": 1},
	"V7": {"auto": 4,  "shuffle": 1,  "hint": 1},
	"V8": {"auto": 4,  "shuffle": 1,  "hint": 1},
	"V9": {"auto": 5,  "shuffle": 1,  "hint": 1},
	"V10": {"auto": 5,  "shuffle": 1,  "hint": 1},
    "V11": {"auto": 100,  "shuffle": 1,  "hint": 1},
}

# 关卡配置：name 关卡名  time_limit 限时秒数
LEVELS = [
    {"name": "第一关", "time_limit": 180},
    {"name": "第二关", "time_limit": 150},
    {"name": "第三关", "time_limit": 120},
    {"name": "第四关", "time_limit": 100},
    {"name": "第五关", "time_limit": 90},
]

# 星级评分阈值（剩余时间 / 限时），对应 1~5 星
STAR_THRESHOLDS = [0.0, 0.15, 0.35, 0.55, 0.70, 0.85]

# 星级额外奖励分（在本关基础消除分之上加）
# 设计思路：5星翻倍最诱人，4星也很可观，1星仅基础分
STAR_BONUS = {
    1: 0,    # 1星：无奖励，基础消除分
    2: 50,   # 2星：+50 分
    3: 150,  # 3星：+150 分
    4: 350,  # 4星：+350 分
    5: 700,  # 5星：+700 分（豪华奖励）
}

# ══════════════════════════════════════════════════════════
# 布局 & 颜色
# ══════════════════════════════════════════════════════════
TILE       = 80
COLS       = 10
ROWS       = 8
MARGIN_X   = 60
MARGIN_Y   = 152
WIN_W      = COLS * TILE + MARGIN_X * 2
WIN_H      = ROWS * TILE + MARGIN_Y + 50
FPS        = 60
TOTAL_IMGS = 80   # 图片库总数
IMG_COUNT  = 20   # 每局随机选取数量

WHITE   = (255, 255, 255)
BG      = (220, 238, 255)
GRID_C  = (160, 195, 225)
SEL_C   = (255, 215,  40)
HINT_C  = ( 60, 210,  90)
MATCH_C = (255, 160, 160)
HDR     = ( 30,  90, 160)
HDR2    = ( 18,  65, 125)
BTN_N   = ( 55, 135, 200)
BTN_H   = ( 90, 170, 240)
BTN_D   = (100, 105, 115)
RED     = (210,  55,  55)
GOLD    = (255, 210,  40)
GREEN   = ( 50, 195,  75)
ORANGE  = (255, 140,  30)
PAUSE_C = ( 80, 150, 220)
NEXT_C  = (180, 110,  20)
SUBMIT_C= ( 70,  70, 140)
CONFIRM_C=(160,  60,  60)
CANCEL_C = (70,  70,  70)


# ══════════════════════════════════════════════════════════
# 字体
# ══════════════════════════════════════════════════════════
def _font(size):
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
    return pygame.font.SysFont("microsoftyahei,arial", size)


# ══════════════════════════════════════════════════════════
# 连通性 & 棋盘逻辑
# ══════════════════════════════════════════════════════════
def can_connect(board, r1, c1, r2, c2):
    if (r1, c1) == (r2, c2):
        return False, []
    if board[r1][c1] != board[r2][c2]:
        return False, []
    R, C = len(board), len(board[0])

    def emp(r, c):
        return r < 0 or r >= R or c < 0 or c >= C or board[r][c] == 0

    def h(r, ca, cb):
        s = 1 if cb > ca else -1
        return all(emp(r, c) for c in range(ca + s, cb, s))

    def v(c, ra, rb):
        s = 1 if rb > ra else -1
        return all(emp(r, c) for r in range(ra + s, rb, s))

    if r1 == r2 and h(r1, c1, c2):
        return True, [(r1, c1), (r1, c2)]
    if c1 == c2 and v(c1, r1, r2):
        return True, [(r1, c1), (r2, c2)]
    if emp(r1, c2) and h(r1, c1, c2) and v(c2, r1, r2):
        return True, [(r1, c1), (r1, c2), (r2, c2)]
    if emp(r2, c1) and v(c1, r1, r2) and h(r2, c1, c2):
        return True, [(r1, c1), (r2, c1), (r2, c2)]
    for r in range(-1, R + 1):
        if r == r1 or r == r2:
            continue
        if emp(r, c1) and emp(r, c2) and v(c1, r1, r) and h(r, c1, c2) and v(c2, r, r2):
            return True, [(r1, c1), (r, c1), (r, c2), (r2, c2)]
    for c in range(-1, C + 1):
        if c == c1 or c == c2:
            continue
        if emp(r1, c) and emp(r2, c) and h(r1, c1, c) and v(c, r1, r2) and h(r2, c, c2):
            return True, [(r1, c1), (r1, c), (r2, c), (r2, c2)]
    return False, []


def find_pair(board):
    cells = [(r, c) for r in range(ROWS) for c in range(COLS) if board[r][c] != 0]
    random.shuffle(cells)
    for i in range(len(cells)):
        for j in range(i + 1, len(cells)):
            r1, c1 = cells[i]; r2, c2 = cells[j]
            if board[r1][c1] == board[r2][c2]:
                ok, path = can_connect(board, r1, c1, r2, c2)
                if ok:
                    return r1, c1, r2, c2, path
    return None


def make_board():
    per   = (ROWS * COLS) // IMG_COUNT
    tiles = sum(([i] * per for i in range(1, IMG_COUNT + 1)), [])
    random.shuffle(tiles)
    return [tiles[r * COLS:(r + 1) * COLS] for r in range(ROWS)]


def shuffle_board(board):
    vals, pos = [], []
    for r in range(ROWS):
        for c in range(COLS):
            if board[r][c] != 0:
                vals.append(board[r][c]); pos.append((r, c))
    random.shuffle(vals)
    for (r, c), v in zip(pos, vals):
        board[r][c] = v


def calc_stars(time_left, time_limit):
    ratio = time_left / max(time_limit, 1)
    for s in range(5, 0, -1):
        if ratio >= STAR_THRESHOLDS[s]:
            return s
    return 1


def star_pts(cx, cy, outer, inner):
    pts = []
    for i in range(10):
        angle = math.radians(i * 36 - 90)
        r = outer if i % 2 == 0 else inner
        pts.append((cx + r * math.cos(angle), cy + r * math.sin(angle)))
    return pts


# ══════════════════════════════════════════════════════════
# UI 工具
# ══════════════════════════════════════════════════════════
def draw_btn(surf, font, rect, text, color, hover=False, disabled=False):
    c = BTN_D if disabled else (BTN_H if hover else color)
    pygame.draw.rect(surf, c, rect, border_radius=9)
    pygame.draw.rect(surf, WHITE, rect, 2, border_radius=9)
    lbl = font.render(text, True, WHITE if not disabled else (160, 160, 160))
    surf.blit(lbl, lbl.get_rect(center=rect.center))


def draw_pill(surf, font, rect, text, color):
    pygame.draw.rect(surf, color, rect, border_radius=rect.height // 2)
    lbl = font.render(text, True, WHITE)
    surf.blit(lbl, lbl.get_rect(center=rect.center))


def draw_shadow_text(surf, font, text, color, center):
    shadow = font.render(text, True, (0, 0, 0))
    main   = font.render(text, True, color)
    surf.blit(shadow, shadow.get_rect(center=(center[0]+2, center[1]+2)))
    surf.blit(main,   main.get_rect(center=center))


# ══════════════════════════════════════════════════════════
# 主游戏类
# ══════════════════════════════════════════════════════════
class LinkGame:
    ST_PLAYING       = "playing"
    ST_PAUSED        = "paused"
    ST_RESULT        = "result"
    ST_CONFIRM       = "confirm"        # 提交成绩二次确认
    ST_REPLAY_CONFIRM = "replay_confirm" # 通关后再玩一次二次确认

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIN_W, WIN_H))
        pygame.display.set_caption("鬼谷无双连连看")
        pygame.display.set_icon(pygame.image.load(resource_path("ggimg/1.png")))
        self.clock = pygame.time.Clock()

        self.F_LG = _font(30)
        self.F_MD = _font(22)
        self.F_SM = _font(17)
        self.F_XS = _font(14)

        self._load_static_images()

        # 跨关卡累计分（整场游戏重置才清零）
        self.total_score    = 0
        self.current_level  = 0
        self.play_seconds   = 0.0   # 累计有效游戏时长（暂停不计）
        self._start_level()

    # ── 资源 ──────────────────────────────────────────────
    def _load_static_images(self):
        """只加载一次的特殊图片（表情、星星等）"""
        def _load(name, size):
            try:
                return pygame.transform.smoothscale(
                    pygame.image.load(resource_path(f"ggimg/{name}")).convert_alpha(), size)
            except Exception:
                return None

        self.img_silly    = _load("silly.png",    (120, 120))
        self.img_sick     = _load("sick.png",     (120, 120))
        self.img_star_on  = _load("Star_01.png",  (50, 50))
        self.img_star_off = _load("star_dark.png",(50, 50))

    def _load_tile_images(self):
        """每关随机从图库中抽取 IMG_COUNT 张图片加载"""
        sz = (TILE - 10, TILE - 10)
        self.selected_ids = random.sample(range(1, TOTAL_IMGS + 1), IMG_COUNT)
        self.imgs = {0: None}
        for idx, file_id in enumerate(self.selected_ids, start=1):
            try:
                raw = pygame.image.load(resource_path(f"ggimg/{file_id}.png")).convert_alpha()
                self.imgs[idx] = pygame.transform.smoothscale(raw, sz)
            except Exception:
                s = pygame.Surface(sz, pygame.SRCALPHA)
                s.fill((180, 180, 200, 180))
                self.imgs[idx] = s

    # ── 关卡初始化 ────────────────────────────────────────
    def _start_level(self):
        cfg = LEVELS[self.current_level]
        self.level_name = cfg["name"]
        self.time_limit = cfg["time_limit"]
        self.time_left  = float(self.time_limit)

        tools = TOOL_CONFIG.get(GAME_VERSION, TOOL_CONFIG["V1"])
        self.tool_auto    = tools["auto"]
        self.tool_shuffle = tools["shuffle"]
        self.tool_hint    = tools["hint"]

        self._load_tile_images()
        self.board        = make_board()
        self.selected     = None
        self.path         = []
        self.path_timer   = 0
        self.match_cells  = []
        self.score        = 0   # 本关基础消除分
        self.state        = self.ST_PLAYING
        self.win          = False
        self.hint_pair    = []

        # 结算数据（_end_level 时写入）
        self.result_stars  = 0
        self.result_bonus  = 0
        self.result_total  = 0  # 本关最终得分 = score + bonus

        # 动态按钮
        self.btn_replay  = None
        self.btn_next    = None
        self.btn_submit  = None
        self.btn_confirm       = None
        self.btn_cancel        = None
        self.btn_replay_ok     = None
        self.btn_replay_cancel = None

        self._build_rects()

    def _full_restart(self):
        """全部重来：清空累计分、关卡、游戏时长"""
        self.total_score   = 0
        self.current_level = 0
        self.play_seconds  = 0.0
        self._start_level()

    def _build_rects(self):
        self.btn_pause   = pygame.Rect(WIN_W - 112, 8, 104, 34)
        bw, bh, gap = 82, 30, 7
        bx, by = MARGIN_X, 108
        self.btn_restart = pygame.Rect(bx,              by, bw, bh)
        self.btn_shuffle = pygame.Rect(bx + (bw+gap),   by, bw, bh)
        self.btn_hint    = pygame.Rect(bx + (bw+gap)*2, by, bw, bh)
        self.btn_auto    = pygame.Rect(bx + (bw+gap)*3, by, 148, bh)

    # ── 坐标 ──────────────────────────────────────────────
    def cell_px(self, r, c):
        return MARGIN_X + c * TILE, MARGIN_Y + r * TILE

    def px_cell(self, x, y):
        c = (x - MARGIN_X) // TILE
        r = (y - MARGIN_Y) // TILE
        return (r, c) if 0 <= r < ROWS and 0 <= c < COLS else None

    # ── 主循环 ────────────────────────────────────────────
    def run(self):
        while True:
            dt = self.clock.tick(FPS)
            self._handle_events()
            self._update(dt)
            self._draw()

    # ── 事件 ──────────────────────────────────────────────
    def _handle_events(self):
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            if ev.type == pygame.KEYDOWN:
                k = ev.key
                if k == pygame.K_ESCAPE:
                    if self.state == self.ST_CONFIRM:
                        self.state = self.ST_RESULT  # 取消确认框
                    else:
                        pygame.quit(); sys.exit()
                if k == pygame.K_p and self.state in (self.ST_PLAYING, self.ST_PAUSED):
                    self._toggle_pause()
                if self.state == self.ST_PLAYING:
                    if k == pygame.K_r:
                        self._start_level()
                    elif k == pygame.K_s:
                        self._do_shuffle()
                    elif k == pygame.K_h:
                        self._do_hint()

            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                pos = ev.pos
                if self.state == self.ST_CONFIRM:
                    self._click_confirm(pos)
                elif self.state == self.ST_REPLAY_CONFIRM:
                    self._click_replay_confirm(pos)
                elif self.state == self.ST_RESULT:
                    self._click_result(pos)
                elif self.state == self.ST_PAUSED:
                    if self.btn_pause.collidepoint(pos):
                        self._toggle_pause()
                else:
                    self._click_header(pos)
                    self._click_board(pos)

    def _click_header(self, pos):
        if self.btn_pause.collidepoint(pos):
            self._toggle_pause(); return
        if self.btn_restart.collidepoint(pos):
            self._start_level(); return
        if self.btn_shuffle.collidepoint(pos):
            self._do_shuffle(); return
        if self.btn_hint.collidepoint(pos):
            self._do_hint(); return
        if self.btn_auto.collidepoint(pos):
            self._do_auto()

    def _click_board(self, pos):
        cell = self.px_cell(*pos)
        if cell is None:
            return
        r, c = cell
        if self.board[r][c] == 0:
            return
        self.hint_pair = []
        if self.selected is None:
            self.selected = (r, c)
        else:
            r1, c1 = self.selected
            if (r1, c1) == (r, c):
                self.selected = None; return
            ok, path = can_connect(self.board, r1, c1, r, c)
            if ok:
                self._do_match(r1, c1, r, c, path)
            else:
                self.selected = (r, c)

    def _click_result(self, pos):
        if self.btn_replay and self.btn_replay.collidepoint(pos):
            # 全部通关后再玩一次：弹二次确认；失败时直接重玩
            if self.win and self.current_level >= len(LEVELS) - 1:
                self.state = self.ST_REPLAY_CONFIRM
            else:
                self._full_restart()
        if self.btn_next and self.btn_next.collidepoint(pos):
            self.current_level += 1
            self._start_level()
        if self.btn_submit and self.btn_submit.collidepoint(pos):
            self.state = self.ST_CONFIRM

    def _click_confirm(self, pos):
        if self.btn_confirm and self.btn_confirm.collidepoint(pos):
            # 发送邮件（使用传入的玩家参数）
            success, msg = send_email2(
                UserID=int(_args.nAccountID),
                WorldID=int(_args.nWorldID),
                ActorID=int(_args.role_id),
                GoodsID=21601490,
                Quantity=1,
                score=self.total_score,
                play_seconds=int(self.play_seconds),
            )

            self.state = self.ST_RESULT
            _show_popup("成功" if success else "提示", msg)
        if self.btn_cancel  and self.btn_cancel.collidepoint(pos):
            self.state = self.ST_RESULT

    def _click_replay_confirm(self, pos):
        if self.btn_replay_ok and self.btn_replay_ok.collidepoint(pos):
            self._full_restart()
        if self.btn_replay_cancel and self.btn_replay_cancel.collidepoint(pos):
            self.state = self.ST_RESULT

    def _toggle_pause(self):
        if self.state == self.ST_PLAYING:
            self.state = self.ST_PAUSED
        elif self.state == self.ST_PAUSED:
            self.state = self.ST_PLAYING

    # ── 游戏动作 ──────────────────────────────────────────
    def _do_match(self, r1, c1, r2, c2, path):
        self.board[r1][c1] = 0
        self.board[r2][c2] = 0
        self.selected    = None
        self.path        = path
        self.path_timer  = 420
        self.match_cells = [(r1, c1), (r2, c2)]
        self.score      += 10

        if all(self.board[r][c] == 0 for r in range(ROWS) for c in range(COLS)):
            self._end_level(win=True); return

        if not find_pair(self.board):
            shuffle_board(self.board)
            if not find_pair(self.board):
                self._end_level(win=False)

    def _do_shuffle(self):
        if self.tool_shuffle <= 0:
            return
        self.tool_shuffle -= 1
        shuffle_board(self.board)
        self.selected  = None
        self.hint_pair = []

    def _do_hint(self):
        if self.tool_hint <= 0:
            return
        self.tool_hint -= 1
        pair = find_pair(self.board)
        if pair:
            r1, c1, r2, c2, _ = pair
            self.hint_pair = [(r1, c1), (r2, c2)]

    def _do_auto(self):
        if self.tool_auto <= 0:
            return
        pair = find_pair(self.board)
        if pair:
            r1, c1, r2, c2, path = pair
            self.tool_auto -= 1
            self._do_match(r1, c1, r2, c2, path)

    def _end_level(self, win):
        self.win   = win
        self.state = self.ST_RESULT
        if win:
            self.result_stars = calc_stars(self.time_left, self.time_limit)
            self.result_bonus = STAR_BONUS[self.result_stars]
            self.result_total = self.score + self.result_bonus
            self.total_score += self.result_total   # 累加到全局
        else:
            self.result_stars = 0
            self.result_bonus = 0
            self.result_total = self.score

    # ── 更新 ──────────────────────────────────────────────
    def _update(self, dt):
        if self.state != self.ST_PLAYING:
            return
        if self.path_timer > 0:
            self.path_timer -= dt
            if self.path_timer <= 0:
                self.path = []; self.match_cells = []
        self.play_seconds += dt / 1000.0   # 仅 PLAYING 状态下累加，暂停不计
        self.time_left -= dt / 1000.0
        if self.time_left <= 0:
            self.time_left = 0
            self._end_level(win=False)

    # ══════════════════════════════════════════════════════
    # 绘制
    # ══════════════════════════════════════════════════════
    def _draw(self):
        self.screen.fill(BG)
        self._draw_header()
        self._draw_grid()
        self._draw_tiles()
        self._draw_path()
        self._draw_selected()
        self._draw_hint()

        if self.state == self.ST_PAUSED:
            self._draw_pause()
        elif self.state == self.ST_RESULT:
            self._draw_result()
        elif self.state == self.ST_CONFIRM:
            self._draw_result()
            self._draw_confirm_dialog()
        elif self.state == self.ST_REPLAY_CONFIRM:
            self._draw_result()
            self._draw_replay_confirm_dialog()

        pygame.display.flip()

    # ── 顶部 ──────────────────────────────────────────────
    def _draw_header(self):
        pygame.draw.rect(self.screen, HDR,  (0, 0, WIN_W, MARGIN_Y - 14))
        pygame.draw.rect(self.screen, HDR2, (0, MARGIN_Y - 16, WIN_W, 4))
        mx, my = pygame.mouse.get_pos()

        # 玩家信息
        n = self.F_MD.render(
            f"{PLAYER_NAME}  Lv.{PLAYER_LEVEL}  VIP.{PLAYER_VIP}  [{PLAYER_ID}]", True, GOLD)
        self.screen.blit(n, (16, 10))

        # 关卡 + 本关得分 + 累计分
        lvl = self.F_MD.render(
            f"{self.level_name}   得分: {self.score}   累计: {self.total_score}", True, WHITE)
        self.screen.blit(lvl, (16, 46))

        # 版本标签
        draw_pill(self.screen, self.F_XS,
                  pygame.Rect(WIN_W - 180, 46, 36, 22), GAME_VERSION, ORANGE)

        # 关卡进度点（右上）
        total = len(LEVELS)
        dot_r, dot_gap = 8, 22
        dot_sx = WIN_W - total * dot_gap - 16
        for i in range(total):
            dcx = dot_sx + i * dot_gap
            dcy = 20
            if i < self.current_level:
                pygame.draw.circle(self.screen, GREEN, (dcx, dcy), dot_r)
            elif i == self.current_level:
                pygame.draw.circle(self.screen, GOLD,  (dcx, dcy), dot_r)
                pygame.draw.circle(self.screen, WHITE, (dcx, dcy), dot_r, 2)
            else:
                pygame.draw.circle(self.screen, HDR2,           (dcx, dcy), dot_r)
                pygame.draw.circle(self.screen, (120, 160, 210),(dcx, dcy), dot_r, 2)

        # 暂停按钮
        hp = self.btn_pause.collidepoint(mx, my)
        ptxt = "继续游戏" if self.state == self.ST_PAUSED else "暂停游戏"
        draw_btn(self.screen, self.F_SM, self.btn_pause, ptxt, (70, 130, 190), hp)

        # 倒计时进度条
        bx, by, bw, bh = 16, 80, WIN_W - 32, 13
        ratio = max(0.0, self.time_left / self.time_limit)
        bar_c = GREEN if ratio > 0.4 else (ORANGE if ratio > 0.2 else RED)
        pygame.draw.rect(self.screen, HDR2, (bx, by, bw, bh), border_radius=7)
        if ratio > 0:
            pygame.draw.rect(self.screen, bar_c,
                             (bx, by, int(bw * ratio), bh), border_radius=7)
        tl = int(self.time_left)
        ts = self.F_XS.render(f"剩余: {tl//60:02d}:{tl%60:02d}", True, WHITE)
        self.screen.blit(ts, (bx + bw - ts.get_width() - 2, by - 1))

        # 工具按钮行
        draw_btn(self.screen, self.F_SM, self.btn_restart, "重新开始",
                 BTN_N, self.btn_restart.collidepoint(mx, my))
        draw_btn(self.screen, self.F_SM, self.btn_shuffle,
                 f"洗牌 x{self.tool_shuffle}", BTN_N,
                 self.btn_shuffle.collidepoint(mx, my), self.tool_shuffle <= 0)
        draw_btn(self.screen, self.F_SM, self.btn_hint,
                 f"提示 x{self.tool_hint}", BTN_N,
                 self.btn_hint.collidepoint(mx, my), self.tool_hint <= 0)
        draw_btn(self.screen, self.F_SM, self.btn_auto,
                 f"自动({GAME_VERSION}) x{self.tool_auto}", BTN_N,
                 self.btn_auto.collidepoint(mx, my), self.tool_auto <= 0)

    # ── 棋盘 ──────────────────────────────────────────────
    def _draw_grid(self):
        for r in range(ROWS):
            for c in range(COLS):
                x, y = self.cell_px(r, c)
                pygame.draw.rect(self.screen, GRID_C, (x, y, TILE, TILE), 1)

    def _draw_tiles(self):
        for r in range(ROWS):
            for c in range(COLS):
                v = self.board[r][c]
                if v == 0:
                    continue
                x, y = self.cell_px(r, c)
                bg = MATCH_C if (r, c) in self.match_cells else WHITE
                pygame.draw.rect(self.screen, bg, (x+1, y+1, TILE-2, TILE-2), border_radius=8)
                if self.imgs[v]:
                    self.screen.blit(self.imgs[v], (x+5, y+5))

    def _draw_selected(self):
        if self.selected:
            r, c = self.selected
            x, y = self.cell_px(r, c)
            pygame.draw.rect(self.screen, SEL_C, (x+1, y+1, TILE-2, TILE-2), 4, border_radius=8)

    def _draw_hint(self):
        for (r, c) in self.hint_pair:
            x, y = self.cell_px(r, c)
            pygame.draw.rect(self.screen, GREEN, (x+1, y+1, TILE-2, TILE-2), 4, border_radius=8)

    def _draw_path(self):
        if len(self.path) < 2:
            return
        pts = [(self.cell_px(r, c)[0] + TILE//2, self.cell_px(r, c)[1] + TILE//2)
               for (r, c) in self.path]
        for i in range(len(pts)-1):
            pygame.draw.line(self.screen, HINT_C, pts[i], pts[i+1], 5)
        for pt in pts:
            pygame.draw.circle(self.screen, HINT_C, pt, 7)

    # ── 暂停 ──────────────────────────────────────────────
    def _draw_pause(self):
        # 用纯色块盖住整个棋盘区域，防止玩家暂停后观察棋盘
        board_rect = (0, MARGIN_Y, WIN_W, ROWS * TILE + 50)
        pygame.draw.rect(self.screen, HDR, board_rect)

        ov = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
        ov.fill((0, 10, 40, 165))
        self.screen.blit(ov, (0, 0))
        cx, cy = WIN_W // 2, WIN_H // 2
        draw_shadow_text(self.screen, self.F_LG, "游戏已暂停", GOLD, (cx, cy - 24))
        t2 = self.F_SM.render("点击右上角「继续游戏」或按 P 键继续", True, WHITE)
        self.screen.blit(t2, t2.get_rect(center=(cx, cy + 18)))

    # ── 结算界面 ──────────────────────────────────────────
    def _draw_result(self):
        ov = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
        ov.fill((0, 10, 40, 170))
        self.screen.blit(ov, (0, 0))

        pw, ph = 540, 420
        px = (WIN_W - pw) // 2
        py = (WIN_H - ph) // 2

        panel = pygame.Surface((pw, ph), pygame.SRCALPHA)
        pygame.draw.rect(panel, (15, 35, 80, 235), panel.get_rect(), border_radius=20)
        border_col = GOLD if self.win else RED
        pygame.draw.rect(panel, border_col, panel.get_rect(), 3, border_radius=20)
        self.screen.blit(panel, (px, py))

        cx  = px + pw // 2
        top = py

        # 表情图
        emoji = self.img_silly if self.win else self.img_sick
        if emoji:
            self.screen.blit(emoji, emoji.get_rect(center=(cx, top + 70)))

        # 标题
        if self.win:
            title, tc = f"{self.level_name}  通关！", GOLD
        else:
            title, tc = "时间到！游戏结束", RED
        draw_shadow_text(self.screen, self.F_LG, title, tc, (cx, top + 145))

        # 星星（仅通关时）
        if self.win:
            sw, gap_s = 50, 8
            total_sw = sw * 5 + gap_s * 4
            sx = cx - total_sw // 2
            sy = top + 175
            for i in range(5):
                img = self.img_star_on if i < self.result_stars else self.img_star_off
                if img:
                    self.screen.blit(img, (sx + i * (sw + gap_s), sy))
                else:
                    col = GOLD if i < self.result_stars else (70, 70, 100)
                    pygame.draw.polygon(
                        self.screen, col,
                        star_pts(sx + i*(sw+gap_s) + sw//2, sy + sw//2, sw//2, sw//4))

            STAR_LABELS = {1:"初级完成", 2:"良好完成", 3:"优秀完成", 4:"精彩完成", 5:"完美通关！"}
            sl = self.F_SM.render(STAR_LABELS[self.result_stars], True, GOLD)
            self.screen.blit(sl, sl.get_rect(center=(cx, top + 238)))

        # 得分明细
        base_t  = self.F_SM.render(f"消除得分：{self.score} 分", True, WHITE)
        bonus_t = self.F_SM.render(
            f"★星级奖励：+{self.result_bonus} 分"
            if self.win else "未通关，无星级奖励", True,
            GOLD if self.result_bonus > 0 else (150, 150, 170))
        total_t = self.F_MD.render(f"本关合计：{self.result_total} 分", True, WHITE)
        accum_t = self.F_SM.render(f"累计总分：{self.total_score} 分", True, (180, 220, 255))

        self.screen.blit(base_t,  base_t.get_rect(center=(cx, top + 265)))
        self.screen.blit(bonus_t, bonus_t.get_rect(center=(cx, top + 290)))
        self.screen.blit(total_t, total_t.get_rect(center=(cx, top + 317)))
        self.screen.blit(accum_t, accum_t.get_rect(center=(cx, top + 343)))

        # ── 按钮区 ────────────────────────────────────────
        mx, my = pygame.mouse.get_pos()
        bw, bh, gap = 155, 44, 18
        by = top + 370

        if self.win and self.current_level < len(LEVELS) - 1:
            # 通关且还有下一关：下一关 | 提交成绩
            total_bw = bw * 2 + gap
            bx0 = cx - total_bw // 2
            self.btn_replay = None
            self.btn_next   = pygame.Rect(bx0,          by, bw, bh)
            self.btn_submit = pygame.Rect(bx0 + bw + gap, by, bw, bh)
            draw_btn(self.screen, self.F_MD, self.btn_next,
                     "下一关  ▶", NEXT_C, self.btn_next.collidepoint(mx, my))
            draw_btn(self.screen, self.F_MD, self.btn_submit,
                     "提交成绩", SUBMIT_C, self.btn_submit.collidepoint(mx, my))
        else:
            # 失败 或 最后一关通关：再玩一次 | 提交成绩
            total_bw = bw * 2 + gap
            bx0 = cx - total_bw // 2
            self.btn_next   = None
            self.btn_replay = pygame.Rect(bx0,          by, bw, bh)
            self.btn_submit = pygame.Rect(bx0 + bw + gap, by, bw, bh)
            draw_btn(self.screen, self.F_MD, self.btn_replay,
                     "再玩一次", BTN_N, self.btn_replay.collidepoint(mx, my))
            draw_btn(self.screen, self.F_MD, self.btn_submit,
                     "提交成绩", SUBMIT_C, self.btn_submit.collidepoint(mx, my))

    # ── 提交成绩二次确认弹窗 ──────────────────────────────
    def _draw_confirm_dialog(self):
        # 额外半透明遮罩
        ov2 = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
        ov2.fill((0, 0, 0, 100))
        self.screen.blit(ov2, (0, 0))

        dw, dh = 460, 240
        dx = (WIN_W - dw) // 2
        dy = (WIN_H - dh) // 2

        # 弹窗面板
        dlg = pygame.Surface((dw, dh), pygame.SRCALPHA)
        pygame.draw.rect(dlg, (20, 30, 70, 245), dlg.get_rect(), border_radius=16)
        pygame.draw.rect(dlg, GOLD, dlg.get_rect(), 2, border_radius=16)
        self.screen.blit(dlg, (dx, dy))

        cx = dx + dw // 2

        # 标题
        t_title = self.F_MD.render("提交成绩确认", True, GOLD)
        self.screen.blit(t_title, t_title.get_rect(center=(cx, dy + 38)))

        # 提示正文
        line1 = self.F_SM.render(
            f"本次游戏总共获得  {self.total_score}  分", True, WHITE)
        line2 = self.F_XS.render(
            "你确认将成绩进行提交吗？每日只可提交一次", True, (180, 210, 255))
        self.screen.blit(line1, line1.get_rect(center=(cx, dy + 100)))
        self.screen.blit(line2, line2.get_rect(center=(cx, dy + 130)))

        # 分隔线
        pygame.draw.line(self.screen, (60, 80, 140),
                         (dx + 20, dy + 155), (dx + dw - 20, dy + 155), 1)

        # 确认 / 取消 按钮
        mx, my = pygame.mouse.get_pos()
        bw, bh, gap = 150, 42, 20
        bx0 = cx - bw - gap // 2
        bx1 = cx + gap // 2
        by  = dy + 170

        self.btn_confirm = pygame.Rect(bx0, by, bw, bh)
        self.btn_cancel  = pygame.Rect(bx1, by, bw, bh)

        draw_btn(self.screen, self.F_MD, self.btn_confirm, "确  认",
                 CONFIRM_C, self.btn_confirm.collidepoint(mx, my))
        draw_btn(self.screen, self.F_MD, self.btn_cancel,  "取  消",
                 CANCEL_C,  self.btn_cancel.collidepoint(mx, my))

    # ── 再玩一次二次确认弹窗 ──────────────────────────────
    def _draw_replay_confirm_dialog(self):
        ov = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 120))
        self.screen.blit(ov, (0, 0))

        dw, dh = 480, 260
        dx = (WIN_W - dw) // 2
        dy = (WIN_H - dh) // 2

        dlg = pygame.Surface((dw, dh), pygame.SRCALPHA)
        pygame.draw.rect(dlg, (20, 30, 70, 245), dlg.get_rect(), border_radius=16)
        pygame.draw.rect(dlg, GOLD, dlg.get_rect(), 2, border_radius=16)
        self.screen.blit(dlg, (dx, dy))

        cx = dx + dw // 2

        # 标题
        t_title = self.F_MD.render("恭喜！全部关卡已通关", True, GOLD)
        self.screen.blit(t_title, t_title.get_rect(center=(cx, dy + 40)))

        # 正文
        line1 = self.F_SM.render("建议优先提交成绩，再决定是否重玩", True, WHITE)
        line2 = self.F_SM.render(f"重新开始将清空当前累计 {self.total_score} 分", True, ORANGE)
        line3 = self.F_XS.render("确定要放弃成绩重新开始吗？", True, (180, 210, 255))
        self.screen.blit(line1, line1.get_rect(center=(cx, dy + 90)))
        self.screen.blit(line2, line2.get_rect(center=(cx, dy + 120)))
        self.screen.blit(line3, line3.get_rect(center=(cx, dy + 148)))

        pygame.draw.line(self.screen, (60, 80, 140),
                         (dx + 20, dy + 168), (dx + dw - 20, dy + 168), 1)

        mx, my = pygame.mouse.get_pos()
        bw, bh, gap = 160, 44, 20
        bx0 = cx - bw - gap // 2
        bx1 = cx + gap // 2
        by  = dy + 182

        self.btn_replay_ok     = pygame.Rect(bx0, by, bw, bh)
        self.btn_replay_cancel = pygame.Rect(bx1, by, bw, bh)

        draw_btn(self.screen, self.F_MD, self.btn_replay_ok,
                 "继续重玩", CONFIRM_C, self.btn_replay_ok.collidepoint(mx, my))
        draw_btn(self.screen, self.F_MD, self.btn_replay_cancel,
                 "去提交成绩", SUBMIT_C, self.btn_replay_cancel.collidepoint(mx, my))


# ══════════════════════════════════════════════════════════
if __name__ == "__main__":
    LinkGame().run()
