"""
CloudAscent 音效生成器
使用纯 Python (wave/struct/math) 生成游戏音效 WAV 文件
"""

import struct, math, wave, os

OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Sound')
SAMPLE_RATE = 44100
SIXTEEN_BIT = 2 ** 15 - 1


def _normalize(samples):
    """归一化到 [-1, 1]，然后缩放到 int16 范围"""
    mx = max(abs(s) for s in samples) if samples else 1
    if mx == 0:
        mx = 1
    return [int(s / mx * SIXTEEN_BIT) for s in samples]


def _save(samples, filename):
    path = os.path.join(OUT_DIR, filename)
    data = b''.join(struct.pack('<h', s) for s in samples)
    with wave.open(path, 'w') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(data)
    print(f'  已生成: {filename} ({len(samples)/SAMPLE_RATE:.2f}s)')


def _envelope_attack_decay(n, attack=0.05, decay=0.3):
    """包络：快速 attack + 指数 decay"""
    env = []
    for i in range(n):
        t = i / n
        if t < attack:
            env.append(t / attack)
        else:
            env.append(math.exp(-6.0 * (t - attack) / decay))
        env[-1] = min(env[-1], 1.0)
    return env


def _envelope_sustain(n, attack=0.02, sustain_len=0.3, release=0.2):
    """包络：attack -> sustain -> release"""
    env = []
    total_sustain = int(sustain_len * SAMPLE_RATE)
    release_start = n - int(release * SAMPLE_RATE)
    for i in range(n):
        t = i / n
        if i < int(attack * n):
            env.append(i / (attack * n))
        elif i < release_start:
            env.append(1.0)
        else:
            env.append((n - i) / max(n - release_start, 1))
        env[-1] = max(0, min(env[-1], 1.0))
    return env


def gen_jump_normal():
    """跳跃音效：短促上升的"boing"声"""
    dur = 0.15
    n = int(dur * SAMPLE_RATE)
    samples = []
    env = _envelope_attack_decay(n, attack=0.01, decay=0.1)
    for i in range(n):
        t = i / SAMPLE_RATE
        # 频率从300快速上升到800，模拟弹跳
        freq = 300 + 500 * (t / dur) ** 0.5
        # 叠加基波+泛音
        s = math.sin(2 * math.pi * freq * t) * 0.6
        s += math.sin(2 * math.pi * freq * 2 * t) * 0.2
        s += math.sin(2 * math.pi * freq * 3 * t) * 0.1
        # 轻微频率调制，增加"弹性"感
        s *= (1.0 + 0.3 * math.sin(2 * math.pi * 25 * t))
        samples.append(s * env[i] * 0.7)
    return _normalize(samples)


def gen_jump_boost():
    """弹簧板跳跃：更强烈的"boing"，音调更高更长"""
    dur = 0.25
    n = int(dur * SAMPLE_RATE)
    samples = []
    env = _envelope_attack_decay(n, attack=0.01, decay=0.15)
    for i in range(n):
        t = i / SAMPLE_RATE
        freq = 400 + 800 * (t / dur) ** 0.4
        s = math.sin(2 * math.pi * freq * t) * 0.5
        s += math.sin(2 * math.pi * freq * 2.3 * t) * 0.25
        s += math.sin(2 * math.pi * freq * 0.5 * t) * 0.15
        s *= (1.0 + 0.4 * math.sin(2 * math.pi * 30 * t))
        samples.append(s * env[i] * 0.8)
    return _normalize(samples)


def gen_land():
    """落地音效：沉闷的"thud"声"""
    dur = 0.1
    n = int(dur * SAMPLE_RATE)
    samples = []
    env = _envelope_attack_decay(n, attack=0.005, decay=0.06)
    for i in range(n):
        t = i / SAMPLE_RATE
        freq = 120 - 40 * (t / dur)
        s = math.sin(2 * math.pi * freq * t) * 0.7
        s += (hash(str(i)) % 1000 / 1000 - 0.5) * 0.15 * env[i]  # 噪音
        samples.append(s * env[i] * 0.6)
    return _normalize(samples)


def gen_score_up():
    """加分音效：明快的上升"ding"双音"""
    dur = 0.3
    n = int(dur * SAMPLE_RATE)
    samples = []
    env = _envelope_sustain(n, attack=0.005, sustain_len=0.1, release=0.15)
    for i in range(n):
        t = i / SAMPLE_RATE
        # 两个和谐频率 C5 -> E5
        f1 = 523.25  # C5
        f2 = 659.25  # E5
        # 淡入第二个音
        blend = min(1, t / 0.08)
        s = math.sin(2 * math.pi * f1 * t) * 0.5
        s += math.sin(2 * math.pi * f2 * t) * 0.4 * blend
        s += math.sin(2 * math.pi * f1 * 2 * t) * 0.15
        samples.append(s * env[i] * 0.8)
    return _normalize(samples)


def gen_score_down():
    """扣分音效：下降的"womp"嗡嗡声"""
    dur = 0.35
    n = int(dur * SAMPLE_RATE)
    samples = []
    env = _envelope_attack_decay(n, attack=0.01, decay=0.25)
    for i in range(n):
        t = i / SAMPLE_RATE
        # 频率从400下降到200
        freq = 400 - 200 * (t / dur)
        s = math.sin(2 * math.pi * freq * t) * 0.5
        s += math.sin(2 * math.pi * freq * 1.5 * t) * 0.2
        s += math.sin(2 * math.pi * freq * 0.5 * t) * 0.15
        # 加入失谐，产生"不和谐"效果
        s += math.sin(2 * math.pi * freq * 1.02 * t) * 0.15
        samples.append(s * env[i] * 0.7)
    return _normalize(samples)


def gen_item_collect():
    """道具收集音效：魔法"sparkle"闪烁声"""
    dur = 0.4
    n = int(dur * SAMPLE_RATE)
    samples = []
    env = _envelope_sustain(n, attack=0.01, sustain_len=0.15, release=0.2)
    for i in range(n):
        t = i / SAMPLE_RATE
        # 快速闪烁的频率变化，模拟"叮铃铃"感
        phase = t * 20  # 快速相位
        f1 = 880 + 400 * math.sin(2 * math.pi * 8 * t)  # 闪烁频率
        f2 = 1200 + 300 * math.sin(2 * math.pi * 12 * t)
        s = math.sin(2 * math.pi * f1 * t) * 0.3
        s += math.sin(2 * math.pi * f2 * t) * 0.25
        # 高泛音闪烁
        s += math.sin(2 * math.pi * 2640 * t) * 0.15 * max(0, math.sin(2 * math.pi * 15 * t))
        s += math.sin(2 * math.pi * 3520 * t) * 0.1 * max(0, math.sin(2 * math.pi * 20 * t))
        samples.append(s * env[i] * 0.7)
    return _normalize(samples)


def gen_shield_hit():
    """护盾触发音效：金属"ping"反震声"""
    dur = 0.3
    n = int(dur * SAMPLE_RATE)
    samples = []
    env = _envelope_attack_decay(n, attack=0.003, decay=0.2)
    for i in range(n):
        t = i / SAMPLE_RATE
        freq = 1200 - 400 * (t / dur)
        # 金属感：多个谐波
        s = math.sin(2 * math.pi * freq * t) * 0.4
        s += math.sin(2 * math.pi * freq * 2.7 * t) * 0.2  # 不规则谐波
        s += math.sin(2 * math.pi * freq * 4.1 * t) * 0.1
        # 快速颤音
        s *= (1.0 + 0.5 * math.sin(2 * math.pi * 50 * t) * env[i])
        samples.append(s * env[i] * 0.8)
    return _normalize(samples)


def gen_combo():
    """连击音效：递进的三连音"""
    dur = 0.4
    n = int(dur * SAMPLE_RATE)
    samples = []
    for i in range(n):
        t = i / SAMPLE_RATE
        # 三连音 C5 -> E5 -> G5
        s = 0
        if t < 0.08:
            f = 523.25  # C5
            lt = t
        elif t < 0.2:
            f = 659.25  # E5
            lt = t - 0.1
        elif t < 0.35:
            f = 783.99  # G5
            lt = t - 0.2
        else:
            f = 783.99
            lt = t - 0.2
        s = math.sin(2 * math.pi * f * t) * 0.4
        s += math.sin(2 * math.pi * f * 2 * t) * 0.15
        # 整体包络
        if t < 0.01:
            vol = t / 0.01
        elif t > 0.32:
            vol = (0.4 - t) / 0.08
        else:
            vol = 1.0
        vol = max(0, min(vol, 1.0))
        samples.append(s * vol * 0.8)
    return _normalize(samples)


def gen_thunder():
    """雷电音效：低频轰鸣 + 噪音"""
    dur = 0.8
    n = int(dur * SAMPLE_RATE)
    samples = []
    env = _envelope_attack_decay(n, attack=0.01, decay=0.5)
    # 预生成噪音
    import random
    random.seed(42)
    noise = [random.random() * 2 - 1 for _ in range(n)]
    for i in range(n):
        t = i / SAMPLE_RATE
        # 低频轰鸣
        s = math.sin(2 * math.pi * 50 * t) * 0.4
        s += math.sin(2 * math.pi * 35 * t) * 0.3
        # 噪音分量
        s += noise[i] * 0.25
        # 初始有尖锐的"咔"声
        if t < 0.05:
            s += noise[i] * 0.8 * (1 - t / 0.05)
        samples.append(s * env[i] * 0.7)
    return _normalize(samples)


def gen_click():
    """click: short tick sound"""
    dur = 0.06
    n = int(dur * SAMPLE_RATE)
    samples = []
    env = _envelope_attack_decay(n, attack=0.002, decay=0.03)
    for i in range(n):
        t = i / SAMPLE_RATE
        freq = 1000
        s = math.sin(2 * math.pi * freq * t) * 0.5
        s += math.sin(2 * math.pi * 2000 * t) * 0.3
        samples.append(s * env[i] * 0.6)
    return _normalize(samples)


if __name__ == '__main__':
    os.makedirs(OUT_DIR, exist_ok=True)
    print('开始生成音效...\n')

    generators = {
        'sfx_jump_normal.wav':  gen_jump_normal,
        'sfx_jump_boost.wav':   gen_jump_boost,
        'sfx_land.wav':         gen_land,
        'sfx_score_up.wav':     gen_score_up,
        'sfx_score_down.wav':   gen_score_down,
        'sfx_item_collect.wav': gen_item_collect,
        'sfx_shield_hit.wav':   gen_shield_hit,
        'sfx_combo.wav':        gen_combo,
        'sfx_thunder.wav':      gen_thunder,
        'sfx_click.wav':        gen_click,
    }

    for fname, gen_fn in generators.items():
        samples = gen_fn()
        _save(samples, fname)

    print(f'\n全部 {len(generators)} 个音效文件已生成到: {OUT_DIR}')
