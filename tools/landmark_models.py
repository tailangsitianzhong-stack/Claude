# -*- coding: utf-8 -*-
"""
実在の場所をモチーフにしたマップの名所・その土地らしい小物を Blender で作る(prop_models.py の部品キットと焼き込みを使う)。

  python tools/landmark_models.py <出力ディレクトリ> [名前...]

大洗町: マリンタワー・神磯の鳥居・一の鳥居・拝殿・随神門・フェリー・漁船・消波ブロック・クロマツ
ベルリン: ブランデンブルク門・連邦議会議事堂・テレビ塔・トラバント・菩提樹
ロンドン: タワーブリッジ・ホワイトタワー・2階建てバス・タクシー・郵便ポスト
イラク/クウェート国境: 国境検問所・T-72の残骸・軍用トラックの残骸・油井・送油管・ラクダ・監視塔・標識門
オルチャ渓谷: イトスギ・オリーブ・カサマツ・ヴィタレータ礼拝堂・農家(ポデーレ)・ブドウ畑の列
(座標はゲームの単位: 1≒1.3m。大きな名所は縮尺を詰めてある)
"""
import os, sys, math, json, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import prop_models as pm
from prop_models import P, PAL, prop, car_body, build
BEFORE = set(P)

PAL.update({
  'sandst': ((.8, .74, .6), 'paint'), 'sandstD': ((.66, .6, .48), 'paint'), 'copper': ((.37, .6, .5), 'metal'), 'portland': ((.84, .81, .74), 'paint'),
  'tbblue': ((.5, .7, .82), 'paint'), 'lead': ((.42, .44, .46), 'metal'), 'gold': ((.85, .68, .3), 'metal'), 'busred': ((.78, .1, .1), 'paint'),
  'khaki': ((.6, .55, .4), 'paint'), 'tanD': ((.55, .5, .36), 'paint'), 'cypress': ((.13, .22, .12), 'leaf'), 'olive': ((.47, .53, .38), 'leaf'),
  'pineU': ((.2, .32, .16), 'leaf'), 'terra': ((.7, .38, .24), 'paint'), 'tuffo': ((.78, .68, .52), 'paint'), 'trav': ((.86, .82, .72), 'paint'),
  'navy': ((.1, .22, .5), 'paint'), 'rockD': ((.26, .25, .24), 'paint'), 'stoneG': ((.6, .6, .58), 'paint'), 'pineJ': ((.15, .3, .16), 'leaf'),
  'camel': ((.72, .56, .36), 'paint'), 'tvsil': ((.72, .74, .76), 'metal'), 'trabiB': ((.55, .7, .78), 'paint'), 'trabiC': ((.88, .84, .7), 'paint'),
  'brickL': ((.62, .36, .26), 'paint'), 'signG': ((.1, .42, .24), 'paint'), 'vine': ((.3, .45, .18), 'leaf'), 'shrineW': ((.45, .3, .2), 'paint'),
})

def torii_gen(k, col, top, s, legs=True):
    """明神鳥居(柱間 4.6×s)。col=柱・貫、top=笠木"""
    for x in (-2.3 * s, 2.3 * s):
        k.cyl('main', col, .5 * s, 5 * s, x, 2.5 * s, 0, 'y', 16, .01, d2=.42 * s)
        if legs: k.cyl('main', col, .62 * s, .5 * s, x, .25 * s, 0, 'y', 16, .02)
    n = 12; W = 7.6 * s
    for i in range(n):
        t0, t1 = i / n, (i + 1) / n; x0, x1 = -W / 2 + W * t0, -W / 2 + W * t1
        y0 = (5.45 + .5 * (2 * t0 - 1) ** 4) * s; y1 = (5.45 + .5 * (2 * t1 - 1) ** 4) * s; r = -math.atan2(y1 - y0, x1 - x0)
        k.box('main', top, x1 - x0 + .02, .32 * s, .7 * s, (x0 + x1) / 2, (y0 + y1) / 2 + .1 * s, 0, roll=r, bev=.01)
        k.box('main', col, x1 - x0 + .02, .3 * s, .55 * s, (x0 + x1) / 2, (y0 + y1) / 2 - .2 * s, 0, roll=r, bev=.01)
    k.box('main', col, 6.0 * s, .3 * s, .3 * s, 0, 4.2 * s, 0, bev=.02); k.box('main', col, .3 * s, .9 * s, .3 * s, 0, 4.75 * s, 0, bev=.02)

# ================================================================ 大洗町
@prop('marine_tower')
def _(k):
    """大洗マリンタワー(高さ約60m→46): 三角柱の白い塔・上部に張り出した展望室(ガラスの帯)・斜めに切った頂部・足元の建物"""
    k.box('main', 'white', 16, 5, 11, 0, 2.5, 0, bev=.08); k.box('main', 'glassL', 15.6, 2.6, .1, 0, 2.2, 5.52, bev=0)
    k.box('main', 'grey', 17, .4, 12, 0, 5.2, 0, bev=.05)
    k.cyl('main', 'white', 8.2, 36, 0, 23, 0, 'y', 3, .1, d2=6.6)                      # 三角柱の塔身(先細り)
    for i in range(3):  # 稜の縦の帯
        a = i * 2 * math.pi / 3 + math.pi / 2; k.box('main', 'grey', .3, 36, .3, math.cos(a) * 3.7, 23, math.sin(a) * 3.7, bev=0)
    k.cyl('main', 'white', 10.5, 2.0, 0, 41.5, 0, 'y', 3, .1)
    k.cyl('main', 'glass', 10.9, 4.2, 0, 44.6, 0, 'y', 3, .02)                       # 展望室のガラス
    for i in range(12): a = i * 2 * math.pi / 12; k.box('main', 'white', .2, 4.2, .2, math.cos(a) * 3.2, 44.6, math.sin(a) * 3.2, bev=0)
    k.cyl('main', 'white', 10.6, 1.0, 0, 47.2, 0, 'y', 3, .08)
    k.prism('main', 'white', [(-4.5, 47.6), (4.5, 47.6), (4.5, 49.0), (-4.5, 52.5)], -2.8, 2.8, 'x', .05, 1)   # 斜めの頂部
    k.cyl('main', 'grey', .25, 5, 0, 54, -2, 'y', 6, 0)
    return dict(circ=4.6, boxes=[[0, 0, 16, 11, 5.4]])

@prop('torii_sea')
def _(k):
    """神磯の鳥居: 海の岩礁の上に立つ石の鳥居と、波に洗われる黒い岩"""
    torii_gen(k, 'stoneG', 'stoneG', .8, legs=False)
    rnd = random.Random(3)
    for i in range(16):
        a = rnd.random() * 6.28; d = rnd.random() * 5
        k.blob('main', 'rockD', .8 + rnd.random() * 1.4, math.cos(a) * d, -.6 + rnd.random() * .5, math.sin(a) * d * .7, sy=.55, sub=2, rough=.35, seed=i)
    return dict(ground=-1.0)

@prop('torii_big')
def _(k):
    torii_gen(k, 'conc', 'conc', 2.3)                                                  # 一の鳥居(鉄筋コンクリート・高さ約15.6m)
    return dict(circles=[[-5.3, 0, .6, 13], [5.3, 0, .6, 13]])

@prop('torii_wood')
def _(k):
    torii_gen(k, 'shrineW', 'black', 1.0)
    return dict(circles=[[-2.3, 0, .35, 6], [2.3, 0, .35, 6]])

def irimoya(k, col, W, D, y, h, ov=1.0, rise=.5):
    """入母屋屋根: 寄棟の下部+妻のある上部。反りは端の持ち上げで表現"""
    n = 8
    for side in (-1, 1):  # 前後の大きな斜面(端が反る)
        for i in range(n):
            x0 = -W / 2 - ov + (W + 2 * ov) * i / n; x1 = x0 + (W + 2 * ov) / n; e = abs((x0 + x1) / 2) / (W / 2 + ov)
            lift = rise * e ** 3
            k.seg('main', col, x1 - x0 + .03, .22, side * (D / 2 + ov), y + lift, side * .3, y + h * .75, (x0 + x1) / 2, bev=.02)
    k.box('main', col, W * .6, .5, .9, 0, y + h * .78, 0, bev=.08)                    # 棟
    for sx in (-1, 1):
        k.prism('main', 'shrineW', [(-D * .28, y + h * .45), (D * .28, y + h * .45), (0, y + h * .78)], sx * W * .3 - .05, sx * W * .3 + .05, 'x', 0, 1)   # 妻
        k.box('main', col, .5, .5, .5, sx * W * .32, y + h * .8, 0, bev=.1)            # 鬼板

@prop('shrine_hall')
def _(k):
    """拝殿: 石の基壇・木の柱と壁・入母屋の大屋根・向拝(正面の張り出し)・階段・注連縄"""
    k.box('main', 'stone', 15, 1.2, 11, 0, .6, 0, bev=.04)
    W, D = 12, 8
    for x in (-6, -3, 0, 3, 6):
        for z in (-4, 4): k.cyl('main', 'shrineW', .45, 4.6, x, 3.5, z, 'y', 10, .01)
    k.box('main', 'shrineW', 12, 3.8, 7.6, 0, 3.1, 0, bev=.02); k.box('main', 'white', 11.6, .8, 7.8, 0, 4.6, 0, bev=0)
    for x in (-4.5, -1.5, 1.5, 4.5): k.box('main', 'black', 2.4, 2.6, .1, x, 2.6, 3.86, bev=0)   # 格子戸
    k.box('main', 'shrineW', 13, .4, 9, 0, 5.85, 0, bev=.02)
    irimoya(k, 'lead', W + .5, D + .5, 6.0, 4.0, 1.2)
    k.box('main', 'shrineW', 5, .3, 3, 0, 5.4, 5.6, bev=.02)                              # 向拝
    for x in (-2.2, 2.2): k.cyl('main', 'shrineW', .35, 4.2, x, 3.3, 6.8, 'y', 8, 0)
    k.seg('main', 'lead', 5.6, .2, 7.6, 5.4, 4.6, 6.8, 0, bev=.02)
    for i in range(4): k.box('main', 'stone', 4, .3, .5, 0, .15 + i * .3, 7.4 - i * .45, bev=.02)
    k.tube('main', 'straw', [(-2.2, 5.0, 6.9), (0, 4.6, 7.0), (2.2, 5.0, 6.9)], .14)
    return dict(box=[15, 11, 8])

@prop('zuishinmon')
def _(k):
    """随神門: 朱塗りではない木の楼門風の門(屋根付き)"""
    for x in (-3, -1.2, 1.2, 3):
        for z in (-1.2, 1.2): k.cyl('main', 'shrineW', .4, 4.2, x, 2.1, z, 'y', 8, 0)
    for x in (-3, 3): k.box('main', 'shrineW', 1.6, 3.6, 2.2, x * .72, 1.9, 0, bev=.02)
    k.box('main', 'shrineW', 7.4, .4, 3.2, 0, 4.4, 0, bev=.02)
    irimoya(k, 'lead', 7, 3, 4.6, 2.8, .9)
    return dict(boxes=[[-2.2, 0, 2, 2.6, 6], [2.2, 0, 2, 2.6, 6]])

@prop('ferry')
def _(k):
    """大型フェリー(縮尺0.6・長さ約100): 船体(青い帯)・何層もの客室甲板(窓の列)・ブリッジ・煙突・救命艇"""
    L, B = 100, 15
    hull = [(-L / 2, -4), (L / 2 - 8, -4), (L / 2, 2), (L / 2 + 2, 6), (-L / 2 + 1, 6), (-L / 2, 2)]
    k.prism('main', 'white', [(z, y) for z, y in hull], -B / 2, B / 2, 'x', .3, 2)
    k.box('main', 'navy', B + .1, 1.6, L - 6, 0, 2.6, -1, bev=.05)
    k.box('main', 'red', B + .1, .8, L - 4, 0, -2.4, -1, bev=.05)
    for d in range(4):  # 客室の甲板(上ほど短い)
        y = 6 + d * 3; l = L - 22 - d * 10
        k.box('main', 'white', B - 1 - d * .6, 3, l, 0, y + 1.5, -6 + d * 3, bev=.15)
        for sx in (-1, 1):
            k.box('main', 'glass', .1, 1.1, l - 4, sx * ((B - 1 - d * .6) / 2 + .02), y + 1.7, -6 + d * 3, bev=0)
    k.box('main', 'glass', B - 3.2, 1.3, .1, 0, 16.8, 25.5, bev=0)
    k.box('main', 'white', B + 2, .8, 4, 0, 17, 22, bev=.1)                              # ブリッジの張り出し
    k.prism('main', 'white', [(-20, 18), (-12, 18), (-13, 25), (-19, 25)], -2, 2, 'x', .2, 2)  # 煙突
    k.box('main', 'navy', 4.1, 1.8, 6.4, 0, 23, -16, bev=0)
    for z in (-10, -2, 6, 14):
        for sx in (-1, 1): k.box('main', 'yellow', 1.2, 1.2, 4, sx * (B / 2 - .4), 10.4, z, bev=.3)
    return dict(box=[B, L + 4, 25], ground=-3)

@prop('fishing_boat')
def _(k):
    L, B = 11, 3.4
    k.prism('main', 'white', [(-L / 2, -.8), (L / 2 - 2, -.8), (L / 2, .4), (L / 2 + .6, 1.6), (-L / 2, 1.4)], -B / 2, B / 2, 'x', .12, 2)
    k.box('main', 'blue', B + .05, .3, L - 1, 0, .6, 0, bev=.05)
    k.box('main', 'white', 2.4, 2, 2.6, 0, 2.4, -1.5, bev=.08); k.box('main', 'glass', 2.42, .6, 2.4, 0, 2.9, -1.5, bev=0)
    k.cyl('main', 'white', .14, 4.5, 0, 4, .8, 'y', 6, 0); k.box('main', 'white', 2.4, .08, .08, 0, 5.4, .8, bev=0)
    for i in range(5): k.cyl('main', 'lampOff', .3, .4, 0, 4.2, -3.6 + i * 1.7, 'y', 8, 0)
    k.tube('main', 'iron', [(0, 4.2, -4.0), (0, 4.2, 3.2)], .02)
    return dict(box=[B, L, 3], ground=-.6)

@prop('tetrapods')
def _(k):
    rnd = random.Random(5)
    for i in range(7):
        x, z = (i % 4) * 2.2 - 3.3 + rnd.uniform(-.3, .3), (i // 4) * 2.2 - 1 + rnd.uniform(-.3, .3); y = .7 + (i // 4) * .2
        for (dx, dy, dz) in ((0, 1, 0), (.94, -.33, 0), (-.47, -.33, .82), (-.47, -.33, -.82)):
            a = rnd.random() * 6.28
            k.cyl('main', 'conc', .9, 1.4, x + dx * .6, y + dy * .6, z + dz * .6, (dx * math.cos(a) - dz * math.sin(a), dy, dx * math.sin(a) + dz * math.cos(a)), 8, .02, d2=.5)
    return dict(box=[9, 4.5, 1.8])

@prop('pine_jp')
def _(k):
    """クロマツ: 傾いて曲がる幹・横に広がる平たい葉の層"""
    pts = [(0, 0, 0), (.4, 2, .1), (1.2, 4, .2), (1.6, 5.6, .5), (1.4, 7, .8)]
    for a, b in zip(pts[:-1], pts[1:]): k.tube('main', 'bark', [a, b], .28)
    rnd = random.Random(8)
    for i, (x, y, z) in enumerate([(1.4, 7.4, .8), (2.8, 6.2, -.4), (-.2, 6.4, 1.6), (2.2, 5, 1.8), (.4, 5.2, -1.2), (1.8, 8.2, .4)]):
        k.tube('main', 'bark', [(1.3, min(y, 6.5) - .6, .5), (x, y - .3, z)], .1)
        k.blob('main', ['pineJ', 'leaf3'][i % 2], 1.3 + rnd.random() * .5, x, y, z, sy=.38, sub=2, rough=.35, seed=i + 20)
    return dict(circ=.4)

# ================================================================ ベルリン
@prop('brandenburg')
def _(k):
    """ブランデンブルク門(縮尺0.75): 2列×6本のドーリア式円柱・5つの通路・エンタブラチュア(トリグリフ)・
    アッティカ(浮彫)・頂上のクアドリガ(緑青の銅)・両脇の衛兵所"""
    S = .75; W, D = 65.5 / 1.3 * S, 11 / 1.3 * S                                           # 約38×6.3
    xs = [-W / 2 + W / 12 + i * W / 6 for i in range(6)]
    k.box('main', 'sandstD', W + 2, .9, D + 2, 0, .45, 0, bev=.05)
    for x in xs:
        for z in (-D / 2 + .9, D / 2 - .9):
            k.cyl('main', 'sandst', 1.65, 10.8, x, 6.3, z, 'y', 16, .02, d2=1.4)        # 円柱
            k.box('main', 'sandst', 2.1, .5, 2.1, x, 11.95, z, bev=.03)
    for x in xs: k.box('main', 'sandst', 1.4, 10.8, D - 2.6, x, 6.3, 0, bev=.03)       # 柱どうしを結ぶ壁
    k.box('main', 'sandst', W + 1.2, 1.4, D + .6, 0, 12.9, 0, bev=.05)                  # アーキトレーブ
    k.box('main', 'sandstD', W + 1.4, 1.3, D + .8, 0, 14.25, 0, bev=.04)                # フリーズ
    for i in range(30):
        x = -W / 2 + .5 + i * W / 29
        for sz in (-1, 1): k.box('main', 'sandst', .5, 1.1, .1, x, 14.25, sz * (D / 2 + .42), bev=0)  # トリグリフ
    k.box('main', 'sandst', W + 2, .5, D + 1.4, 0, 15.15, 0, bev=.05)                   # コーニス
    k.box('main', 'sandst', W * .62, 3.4, D * .9, 0, 17.1, 0, bev=.05)                  # アッティカ
    k.box('main', 'sandstD', W * .5, 2.0, .2, 0, 17.0, D * .45 + .1, bev=0); k.box('main', 'sandstD', W * .5, 2.0, .2, 0, 17.0, -D * .45 - .1, bev=0)
    for st in range(3): k.box('main', 'sandst', W * .28 - st * 1.2, .6, D * .7 - st * .5, 0, 19.1 + st * .6, 0, bev=.04)   # 階段状の台座
    # クアドリガ: 4頭の馬と戦車と女神(勝利の女神ヴィクトリア)
    y = 20.6
    for i, x in enumerate((-2.4, -.8, .8, 2.4)):
        k.blob('main', 'copper', .75, x, y + 1.3, -.4, sy=.7, sub=2, rough=.08, seed=i)   # 胴
        k.box('main', 'copper', .35, 1.3, .5, x, y + 2.3, .6, pitch=.5, bev=.1)        # 首
        k.box('main', 'copper', .3, .4, .7, x, y + 2.9, 1.0, bev=.1)                    # 頭
        for (lx, lz, p) in ((-.2, .4, -.4), (.2, .4, .3), (-.2, -1.0, .2), (.2, -1.0, -.2)): k.box('main', 'copper', .16, 1.3, .16, x + lx, y + .55, lz, pitch=p, bev=0)
    k.box('main', 'copper', 2.2, 1.2, 1.2, 0, y + 1.2, -2.3, bev=.2)                    # 戦車
    k.cyl('main', 'copper', .5, 3, 0, y + 3.2, -2.5, 'y', 8, 0)                          # 女神
    k.blob('main', 'copper', .3, 0, y + 4.9, -2.5, sub=1, rough=0)
    k.tube('main', 'copper', [(.3, y + 3.6, -2.5), (.6, y + 6.2, -2.1)], .08); k.box('main', 'copper', .9, .9, .15, .6, y + 6.4, -2.1, bev=.05)  # 杖と鷲の飾り
    for sx in (-1, 1):  # 衛兵所(両脇の小神殿)
        x = sx * (W / 2 + 6)
        k.box('main', 'sandst', 7, 7.5, 9, x, 3.75, 0, bev=.05); k.box('main', 'sandstD', 7.6, .6, 9.6, x, 7.8, 0, bev=.04)
        for z in (-3, -1, 1, 3): k.cyl('main', 'sandst', .9, 6.4, x - sx * 3.6, 3.6, z, 'y', 12, 0)
        k.prism('main', 'sandst', [(-4.8, 8.1), (4.8, 8.1), (0, 9.6)], x - 3.8, x + 3.8, 'x', .03, 1)
    return dict(boxes=[[x, 0, 1.8, D, 13] for x in xs] + [[-W / 2 - 6, 0, 7.2, 9.2, 9], [W / 2 + 6, 0, 7.2, 9.2, 9]])

@prop('reichstag')
def _(k):
    """連邦議会議事堂(縮尺0.45): 四隅の塔・西正面の6本柱のポルティコと破風・ガラスのドーム(らせん通路の帯と鏡の円錐)"""
    W, D, H = 62, 42, 20
    k.box('main', 'sandstD', W + 2, 1.6, D + 2, 0, .8, 0, bev=.05)
    k.box('main', 'sandst', W, H, D, 0, H / 2 + 1.6, 0, bev=.08)
    for fl in range(3):
        for i in range(int(W / 3)):
            for sz in (-1, 1): k.box('main', 'glass', 1.2, 2.6, .1, -W / 2 + 2 + i * 3, 5 + fl * 5.6, sz * (D / 2 + .02), bev=0)
        for i in range(int(D / 3)):
            for sx in (-1, 1): k.box('main', 'glass', .1, 2.6, 1.2, sx * (W / 2 + .02), 5 + fl * 5.6, -D / 2 + 2 + i * 3, bev=0)
    for sx in (-1, 1):
        for sz in (-1, 1):
            k.box('main', 'sandst', 11, H + 6, 11, sx * (W / 2 - 3), (H + 6) / 2 + 1.6, sz * (D / 2 - 3), bev=.08)
            k.box('main', 'sandstD', 11.6, 1, 11.6, sx * (W / 2 - 3), H + 7.6, sz * (D / 2 - 3), bev=.05)
    k.box('main', 'sandstD', W + .8, 1.2, D + .8, 0, H + 1.6, 0, bev=.05)
    # 西正面(-x)のポルティコ
    x0 = -W / 2 - 3.5
    k.box('main', 'sandst', 7, 1.6, 22, x0, 1.8, 0, bev=.04)
    for i in range(6): k.cyl('main', 'sandst', 1.5, 14, x0 - 1.5, 9.6, -8.5 + i * 3.4, 'y', 14, 0, d2=1.3)
    k.box('main', 'sandst', 7.6, 2.2, 22.5, x0, 17.7, 0, bev=.04); k.box('main', 'sandstD', .2, 1.0, 16, x0 - 3.82, 17.7, 0, bev=0)  # 碑文の帯
    k.prism('main', 'sandst', [(-11.6, 18.8), (11.6, 18.8), (0, 23.4)], x0 - 3.8, x0 + 3.6, 'x', .04, 1)
    for i in range(8): k.box('main', 'sandstD', 1.2, .25, 20 - i * .6, x0 - 4 - i * .6, .12 + i * .2, 0, bev=0)
    # ドーム
    y = H + 2.2; R = 9.5
    k.lathe('main', 'glassL', [(0, y), (R, y), (R * .97, y + 3), (R * .85, y + 6.5), (R * .6, y + 9.5), (R * .25, y + 11.2), (0, y + 11.5)], 0, 0, 0, 24, cap=False)
    for i in range(24):
        a = i * 2 * math.pi / 24
        k.tube('main', 'steel', [(math.cos(a) * r, h, math.sin(a) * r) for r, h in ((R, y), (R * .97, y + 3), (R * .85, y + 6.5), (R * .6, y + 9.5), (R * .25, y + 11.2))], .07)
    for h, r in ((y + 3, R * .97), (y + 6.5, R * .85), (y + 9.5, R * .6)): k.torus('main', 'steel', r, .08, 0, h, 0, 'y', 32, 4)
    k.lathe('main', 'chrome', [(.4, y), (3, y + 9)], 0, 0, 0, 16, cap=False)            # 鏡の円錐
    k.cyl('main', 'steel', 6.5, .3, 0, y + 11.6, 0, 'y', 20, 0)
    return dict(box=[W + 2, D + 2, H + 14], boxes=[[x0, 0, 7.4, 23, 22]])

@prop('fernsehturm')
def _(k):
    """ベルリンのテレビ塔(368m→283。遠景用): 先細りのコンクリートの塔身・銀色の球(展望台)・赤白のアンテナ"""
    k.lathe('main', 'conc', [(0, 0), (14, 0), (14, 4), (10, 6), (7, 20), (5.2, 80), (4.2, 150), (3.6, 156), (0, 156)], 0, 0, 0, 20)
    k.blob('main', 'tvsil', 12.5, 0, 168, 0, sub=3, rough=0)
    k.cyl('main', 'glass', 25.6, 2.5, 0, 167, 0, 'y', 32, 0)
    k.lathe('main', 'conc', [(0, 180), (2.6, 180), (2.2, 196), (0, 196)], 0, 0, 0, 12)
    for i in range(8): k.cyl('main', 'red' if i % 2 == 0 else 'white', 2.0 - i * .15, 11, 0, 201.5 + i * 11, 0, 'y', 10, 0)
    return dict()

@prop('trabant_b')
def _(k): car_body(k, 2.7, 1.2, 1.08, 'trabiB'); return dict(box=[1.25, 2.8, 1.15])
@prop('trabant_c')
def _(k): car_body(k, 2.7, 1.2, 1.08, 'trabiC'); return dict(box=[1.25, 2.8, 1.15])

@prop('linden')
def _(k):
    """菩提樹(ウンター・デン・リンデンの並木): まっすぐな幹・卵形の樹冠"""
    k.cyl('main', 'bark', .5, 4.5, 0, 2.25, 0, 'y', 8, 0, d2=.32)
    rnd = random.Random(11)
    for i in range(7):
        a = i * 2.1; r = .9 if i < 6 else 0
        k.blob('main', ['leaf1', 'leaf2', 'leaf3'][i % 3], 1.5 + rnd.random() * .4, math.cos(a) * r, 5.4 + (i % 3) * 1.1 + (2 if i == 6 else 0), math.sin(a) * r, sy=1.1, sub=2, rough=.28, seed=i + 40)
    return dict(circ=.4)

# ================================================================ ロンドン
@prop('tower_bridge')
def _(k):
    """タワーブリッジ(縮尺約0.6・主塔間36): 水中の橋脚・ゴシック様式の2本の主塔(四隅の小塔と尖塔、道路が抜けるアーチ)・
    上部の2本の歩道橋(水色のトラス)・跳ね橋の路面・両岸へ下がる吊り橋の鎖。橋は z 方向、路面 y=0"""
    for zc in (-18, 18):
        k.box('main', 'stoneG', 14, 6, 12, 0, -3.5, zc, bev=.1)                          # 橋脚
        for sx in (-1, 1):
            k.box('main', 'portland', 3, 7, 10, sx * 5, 3.5, zc, bev=.05)               # 道路の両脇の脚
            for sz in (-1, 1):
                k.box('main', 'portland', 2.6, 34, 2.6, sx * 5.7, 17, zc + sz * 4.4, bev=.05)  # 四隅の小塔
                k.cyl('main', 'lead', 3.4, 6, sx * 5.7, 37, zc + sz * 4.4, 'y', 8, .02, d2=0)  # 尖塔
                k.cyl('main', 'gold', .2, 1.5, sx * 5.7, 40.6, zc + sz * 4.4, 'y', 4, 0)
        k.box('main', 'portland', 10, 25, 7, 0, 21.5, zc, bev=.05)                       # 塔の本体(道路の上)
        k.cyl('main', 'lead', 9, 7, 0, 37.5, zc, 'y', 4, .02, d2=0)                       # 中央の尖った屋根
        for fl in range(4):
            for sx in (-1, 1):
                k.box('main', 'glass', .1, 2.4, 1.2, sx * 5.02, 13 + fl * 5, zc - 1.4, bev=0); k.box('main', 'glass', .1, 2.4, 1.2, sx * 5.02, 13 + fl * 5, zc + 1.4, bev=0)
            for sz in (-1, 1): k.box('main', 'glass', 1.4, 2.4, .1, 0, 13 + fl * 5, zc + sz * 3.52, bev=0)
        k.box('main', 'portland', 10.6, .6, 7.6, 0, 7.3, zc, bev=.03)                    # 道路のアーチの上の帯
    # 上部の歩道橋(水色のトラス) 2本
    for sx in (-1, 1):
        x = sx * 2.4
        for y in (28.5, 31.5): k.box('main', 'tbblue', 1.4, .6, 29.6, x, y, 0, bev=.03)
        for i in range(16):
            z0 = -14.8 + i * 29.6 / 16; z1 = z0 + 29.6 / 16
            k.seg('main', 'tbblue', .25, .25, z0, 28.5, z1, 31.5, x - .55, bev=0); k.seg('main', 'tbblue', .25, .25, z0, 28.5, z1, 31.5, x + .55, bev=0)
            k.box('main', 'tbblue', 1.3, 3, .25, x, 30, z0, bev=0)
        for zz in (-14.8, 14.8): k.seg('main', 'tbblue', .8, .8, zz, 28.5, zz * .82, 24.5, x, bev=.02)   # 塔から張り出す腕
    # 跳ね橋の路面と欄干
    k.box('main', 'dgrey', 8, .9, 36, 0, -.45, 0, bev=.03)
    for sx in (-1, 1):
        k.box('main', 'tbblue', .35, 1.1, 60, sx * 4.1, .55, 0, bev=.02)
        for i in range(30): k.box('main', 'tbblue', .12, 1.0, .12, sx * 4.1, .5, -29 + i * 2, bev=0)
    k.box('main', 'dgrey', 8, .9, 12, 0, -.45, 24, bev=.02); k.box('main', 'dgrey', 8, .9, 12, 0, -.45, -24, bev=.02)
    # 吊り橋の鎖(主塔の上部から岸へ)
    for sz in (-1, 1):
        for sx in (-1, 1):
            pts = []
            for i in range(9):
                t = i / 8; z = sz * (22.4 + 8.6 * t); y = 22 * (1 - t) + 3 * t - 8 * math.sin(math.pi * t) * .6
                pts.append((sx * 4.5, y, z))
            k.tube('main', 'tbblue', pts, .4)
            for i in range(1, 8): z = pts[i][2]; k.cyl('main', 'tbblue', .12, pts[i][1], sx * 4.5, pts[i][1] / 2, z, 'y', 4, 0)
    return dict(boxes=[[sx * 5.3, zc, 3.6, 10.4, 34] for sx in (-1, 1) for zc in (-18, 18)] + [[sx * 4.15, 0, .45, 60, 1.1] for sx in (-1, 1)])   # 主塔の脚と路面の両側の欄干

@prop('white_tower')
def _(k):
    """ロンドン塔のホワイトタワー(縮尺0.75): 白い切石の四角い天守・控え壁・小さなアーチ窓・胸壁・四隅の小塔(1つは円筒)と鉛のキューポラ"""
    W, D, H = 27, 24, 17
    k.box('main', 'portland', W, H, D, 0, H / 2, 0, bev=.06)
    for i in range(5):
        for sz in (-1, 1): k.box('main', 'portland', 1.2, H, .6, -W / 2 + 2 + i * (W - 4) / 4, H / 2, sz * (D / 2 + .3), bev=.03)
        for sx in (-1, 1): k.box('main', 'portland', .6, H, 1.2, sx * (W / 2 + .3), H / 2, -D / 2 + 2 + i * (D - 4) / 4, bev=.03)
    for fl, y in enumerate((5, 10, 14)):
        for i in range(4):
            for sz in (-1, 1): k.box('main', 'black', .9, 1.8 if fl else 1.2, .1, -W / 2 + 5 + i * (W - 10) / 3 + (W - 10) / 6 - 1.5, y, sz * (D / 2 + .02), bev=0)
            for sx in (-1, 1): k.box('main', 'black', .1, 1.8 if fl else 1.2, .9, sx * (W / 2 + .02), y, -D / 2 + 5 + i * (D - 10) / 3, bev=0)
    for i in range(int(W / 1.2)):
        for sz in (-1, 1): k.box('main', 'portland', .7, .8, .5, -W / 2 + .6 + i * 1.2, H + .4, sz * (D / 2 - .25), bev=.02)
    for i in range(int(D / 1.2)):
        for sx in (-1, 1): k.box('main', 'portland', .5, .8, .7, sx * (W / 2 - .25), H + .4, -D / 2 + .6 + i * 1.2, bev=.02)
    for j, (sx, sz) in enumerate(((-1, -1), (1, -1), (-1, 1), (1, 1))):
        x, z = sx * (W / 2 - 1.5), sz * (D / 2 - 1.5)
        if j == 0: k.cyl('main', 'portland', 5.4, H + 5, x - .8, (H + 5) / 2, z - .8, 'y', 20, .02)
        else: k.box('main', 'portland', 4.4, H + 5, 4.4, x, (H + 5) / 2, z, bev=.05)
        xx, zz = (x - .8, z - .8) if j == 0 else (x, z)
        k.lathe('main', 'lead', [(0, H + 5), (2.4, H + 5), (2.6, H + 5.6), (2.0, H + 7), (.9, H + 8.2), (.3, H + 9.2), (0, H + 9.4)], xx, 0, zz, 16)  # キューポラ
        k.cyl('main', 'gold', .1, 2, xx, H + 10.2, zz, 'y', 4, 0); k.box('main', 'gold', .8, .3, .05, xx, H + 10.8, zz, bev=0)
    k.box('main', 'woodD', 4, 6, 3, 2, 4, -D / 2 - 2.5, bev=.03); k.seg('main', 'woodD', 2.4, .4, -D / 2 - 9, 0, -D / 2 - 4, 6, 2, bev=.02)  # 入口の木の階段
    return dict(box=[W + 1, D + 1, H + 5], boxes=[[2, -D / 2 - 6, 3, 9, 6]])

@prop('dbus')
def _(k):
    """ロンドンの赤い2階建てバス: 丸みのある車体・上下2列の窓・前面の行先表示・ホイール"""
    L, W, H = 8.6, 2.0, 3.3
    k.box('main', 'busred', W, H - .3, L, 0, H / 2 + .25, 0, bev=.25)
    for y in (1.55, 2.95):
        for sx in (-1, 1): k.box('main', 'glass', .05, .75, L - 1.2, sx * (W / 2 + .01), y, -.2, bev=0)
    k.box('main', 'glass', W - .3, 1.1, .05, 0, 1.6, L / 2 + .01, bev=0); k.box('main', 'glass', W - .3, .7, .05, 0, 2.95, L / 2 + .01, bev=0)
    k.box('main', 'black', 1.2, .3, .06, 0, 3.45, L / 2 + .02, bev=0); k.box('main', 'lampY', 1.0, .2, .07, 0, 3.45, L / 2 + .02, bev=0)
    k.box('main', 'black', W + .05, .12, L, 0, 2.25, 0, bev=0)
    for z in (-2.7, 2.6):
        for sx in (-1, 1): k.wheel('main', sx * (W / 2 - .2), .45, z, .9, .3, 'busred')
    for sx in (-1, 1): k.box('main', 'lampW', .3, .2, .05, sx * .7, .7, L / 2 + .02, bev=0)
    return dict(box=[W + .1, L + .1, H + .2])

@prop('cab')
def _(k):
    car_body(k, 3.4, 1.35, 1.38, 'black', kei=False)
    k.box('main', 'lampY', .5, .12, .3, 0, 1.42, .3, bev=.03)                             # TAXI の灯り
    return dict(box=[1.4, 3.5, 1.45])

@prop('pillar_box')
def _(k):
    k.lathe('main', 'busred', [(0, 0), (.36, 0), (.36, .1), (.3, .2), (.3, 1.25), (.36, 1.3), (.34, 1.42), (.2, 1.55), (0, 1.58)], 0, 0, 0, 16)
    k.box('main', 'black', .28, .05, .05, 0, 1.15, .29, bev=0); k.box('main', 'gold', .12, .14, .03, 0, .85, .3, bev=0)
    return dict(circ=.4)

@prop('plane_tree')
def _(k):
    """プラタナス(ロンドンの街路樹): まだらの幹・大きく広がる樹冠"""
    k.tube('main', 'barkP', [(0, 0, 0), (.1, 3, 0), (.2, 4.5, .1)], .3)
    for a in range(4): k.tube('main', 'barkP', [(.2, 4.3, .1), (math.cos(a * 1.6) * 1.8, 6.2, math.sin(a * 1.6) * 1.8)], .14)
    rnd = random.Random(13)
    for i in range(7):
        a = i * .9; r = 1.6 if i < 6 else 0
        k.blob('main', ['leaf1', 'leaf2', 'leaf3'][i % 3], 1.6 + rnd.random() * .5, math.cos(a) * r, 6.6 + (i % 2) * .8 + (1 if i == 6 else 0), math.sin(a) * r, sy=.8, sub=2, rough=.3, seed=i + 60)
    return dict(circ=.45)

# ================================================================ イラク/クウェート国境
@prop('border_post')
def _(k):
    """国境検問所(アブダリ/サフワン): 車線をまたぐ大屋根(柱・梁)・料金所のようなブース・遮断機・照明・標識"""
    W, D = 34, 14
    k.box('main', 'white', W, 1.4, D, 0, 8.2, 0, bev=.1); k.box('main', 'signG', W + .1, .6, D + .1, 0, 8.2, 0, bev=.05)
    for x in (-15, -5, 5, 15):
        for z in (-5, 5): k.cyl('main', 'white', .9, 7.6, x, 3.8, z, 'y', 12, .02)
    for x in (-10, 0, 10):
        k.box('main', 'cream', 2.2, 2.8, 4.5, x, 1.6, 0, bev=.08); k.box('main', 'glass', 2.25, 1.0, 4.0, x, 2.1, 0, bev=0); k.box('main', 'conc', 2.6, .2, 9, x, .1, 0, bev=.02)
        for sz in (-1, 1): k.box('main', 'white', 4.2, .14, .14, x + 3.2, 1.1, sz * 3.6, bev=0)
    for x in (-15, 15):
        for i in range(4): k.box('main', 'lampW', 3, .1, .8, x * .5 + (i - 1.5) * 6, 7.45, 0, bev=0)
    return dict(boxes=[[x, z, 1, 1, 8] for x in (-15, -5, 5, 15) for z in (-5, 5)] + [[x, 0, 2.6, 9, 3] for x in (-10, 0, 10)])

@prop('border_arch')
def _(k):
    """国境の標識門: 道路の両側の塔と、それをつなぐ横長の門(アーチの飾り・旗竿)"""
    for sx in (-1, 1):
        k.box('main', 'sandst', 3.2, 11, 3.2, sx * 13, 5.5, 0, bev=.08); k.box('main', 'sandstD', 3.8, .8, 3.8, sx * 13, 11.4, 0, bev=.05)
        k.lathe('main', 'sandst', [(0, 11.8), (1.6, 11.8), (1.5, 12.6), (.8, 13.6), (0, 14)], sx * 13, 0, 0, 12)
        k.cyl('main', 'grey', .14, 8, sx * 16, 4, 0, 'y', 6, 0); k.box('main', 'green' if sx < 0 else 'red', 1.8, 1.1, .03, sx * 16 + .95 * sx, 7.3, 0, bev=0)
    k.box('main', 'sandst', 23, 3, 2.4, 0, 9.5, 0, bev=.06); k.box('main', 'signG', 12, 1.8, .1, 0, 9.5, 1.25, bev=0)
    return dict(boxes=[[-13, 0, 3.4, 3.4, 12], [13, 0, 3.4, 3.4, 12]])

@prop('t72_wreck')
def _(k):
    """T-72 の残骸(焼けて錆びた車体・吹き飛んだ砲塔が横に落ちている・外れた履帯)"""
    k.prism('main', 'rust', [(-3.4, .45), (2.8, .45), (3.4, 1.0), (2.6, 1.5), (-3.4, 1.6)], -1.45, 1.45, 'x', .06, 1)
    for sx in (-1, 1):
        k.box('main', 'burnt', .55, .8, 6.6, sx * 1.65, .55, 0, bev=.1)
        for i in range(6): k.cyl('main', 'iron', .78, .45, sx * 1.65, .42, -2.6 + i * 1.04, 'x', 12, .02)
    k.box('main', 'burnt', 1.2, .4, 1.2, 0, 1.75, -.4, bev=.1)                              # 砲塔の跡のリング
    k.lathe('main', 'rust', [(0, 0), (1.5, 0), (1.45, .4), (1.1, .8), (0, .9)], 3.2, .0, -3.0, 14)   # 落ちた砲塔
    k.cyl('main', 'rust', .2, 5, 3.0, .35, -.2, (-.4, .05, 1), 8, 0)
    k.box('main', 'burnt', .5, .12, 3.5, -2.6, .06, 2.6, yaw=.6, bev=0)                     # 外れた履帯
    return dict(boxes=[[0, 0, 3.6, 6.8, 2], [3.2, -3.0, 3, 3, 1]])

@prop('truck_mil')
def _(k):
    """軍用トラックの残骸(カーキ・焼け跡): キャブ・幌の骨組み・3軸"""
    k.box('main', 'khaki', 2.3, 1.8, 2.0, 0, 1.9, 2.6, bev=.1); k.box('main', 'glass', 2.0, .6, .05, 0, 2.4, 3.62, bev=0)
    k.box('main', 'burnt', 2.2, 1.0, 1.4, 0, 1.4, 4.0, bev=.08)
    k.box('main', 'burnt', 2.4, .3, 5.2, 0, 1.25, -1.2, bev=.03)
    for sx in (-1, 1): k.box('main', 'khaki', .08, .7, 5.2, sx * 1.18, 1.75, -1.2, bev=0)
    for i in range(4): k.tube('main', 'iron', [(-1.15, 2.1, -3.4 + i * 1.5), (-1.0, 3.3, -3.4 + i * 1.5), (1.0, 3.3, -3.4 + i * 1.5), (1.15, 2.1, -3.4 + i * 1.5)], .04)
    for z in (3.0, -1.0, -2.6):
        for sx in (-1, 1): k.wheel('main', sx * 1.0, .5, z, 1.0, .35, 'rust')
    return dict(box=[2.5, 8, 3])

@prop('wellhead')
def _(k):
    """油井の坑口装置(クリスマスツリー): 弁と配管・コンクリートの台・柵"""
    k.box('main', 'conc', 4, .3, 4, 0, .15, 0, bev=.03)
    k.cyl('main', 'yellow', .6, 2.4, 0, 1.5, 0, 'y', 10, .02)
    for y in (1.0, 1.8, 2.5): k.cyl('main', 'red', .9, .25, 0, y, 0, 'y', 12, .02); k.torus('main', 'red', .35, .05, .5, y, 0, 'x', 10, 4)
    k.cyl('main', 'yellow', .4, 2.4, 1.2, 1.8, 0, 'x', 8, 0); k.cyl('main', 'steel', .4, 4, 3.2, 1.8, 0, 'x', 8, 0)
    for (x, z) in ((-2, -2), (2, -2), (-2, 2), (2, 2)): k.cyl('main', 'steel', .08, 1.2, x * 1.1, .6, z * 1.1, 'y', 4, 0)
    for (a, b) in (((-2.2, -2.2), (2.2, -2.2)), ((2.2, -2.2), (2.2, 2.2)), ((2.2, 2.2), (-2.2, 2.2)), ((-2.2, 2.2), (-2.2, -2.2))):
        for y in (.5, 1.1): k.tube('main', 'steel', [(a[0], y, a[1]), (b[0], y, b[1])], .03)
    return dict(box=[4.6, 4.6, 3.2])

@prop('pipeline')
def _(k):
    k.cyl('main', 'steel', 1.0, 12, 0, 1.2, 0, 'z', 14, .02)
    for z in (-4.5, 0, 4.5): k.box('main', 'conc', 1.4, .9, .6, 0, .45, z, bev=.03); k.box('main', 'steel', 1.3, .15, .3, 0, .7, z, bev=0)
    return dict(box=[1.4, 12, 1.8])

@prop('camel')
def _(k):
    k.blob('main', 'camel', .9, 0, 2.0, 0, sy=.75, sub=2, rough=.06, seed=2); k.blob('main', 'camel', .55, 0, 2.6, -.1, sy=.9, sub=2, rough=.05, seed=3)
    k.tube('main', 'camel', [(0, 2.0, .7), (0, 2.6, 1.2), (0, 3.0, 1.35)], .2); k.box('main', 'camel', .3, .3, .7, 0, 3.0, 1.6, bev=.1)
    for (x, z) in ((-.35, .55), (.35, .55), (-.35, -.6), (.35, -.6)): k.cyl('main', 'camel', .18, 1.7, x, .85, z, 'y', 6, 0, d2=.12)
    return dict(circ=.8)

@prop('watchtower')
def _(k):
    for sx in (-1, 1):
        for sz in (-1, 1): k.tube('main', 'steel', [(sx * 1.4, 0, sz * 1.4), (sx * .9, 7, sz * .9)], .1)
    for y in (2.4, 4.8):
        for (a, b) in (((-1, -1), (1, -1)), ((1, -1), (1, 1)), ((1, 1), (-1, 1)), ((-1, 1), (-1, -1))):
            s = 1.4 - y / 7 * .5; k.tube('main', 'steel', [(a[0] * s, y, a[1] * s), (b[0] * s, y, b[1] * s)], .05)
    k.box('main', 'khaki', 2.8, 2.2, 2.8, 0, 8.1, 0, bev=.05); k.box('main', 'glass', 2.85, .7, 2.85, 0, 8.4, 0, bev=0)
    k.box('main', 'tanD', 3.4, .25, 3.4, 0, 9.3, 0, bev=.04)
    return dict(circ=1.6)

@prop('gantry')
def _(k):
    """高速道路の標識門(6車線をまたぐ緑の案内標識)"""
    for sx in (-1, 1): k.cyl('main', 'steel', .5, 7.5, sx * 14, 3.75, 0, 'y', 8, 0)
    for y in (6.8, 7.6): k.box('main', 'steel', 28.4, .25, .25, 0, y, 0, bev=0)
    for x in (-8, 6):
        k.box('main', 'signG', 9, 2.6, .1, x, 7.2, .2, bev=0)
        for i in range(3): k.box('main', 'white', 6 - i * 1.2, .18, .02, x - .6, 7.9 - i * .55, .26, bev=0)
        k.box('main', 'white', .9, .9, .02, x + 3.4, 7.2, .26, bev=0)
    return dict(circles=[[-14, 0, .4, 7.5], [14, 0, .4, 7.5]])

# ================================================================ オルチャ渓谷(トスカーナ)
@prop('cypress')
def _(k):
    """イトスギ: 細く尖った濃い緑の樹形(高さ約15m)"""
    k.cyl('main', 'bark', .35, 1.4, 0, .7, 0, 'y', 6, 0)
    rnd = random.Random(21)
    for i in range(9):
        t = i / 8; y = 1.4 + t * 9; r = .95 * math.sin(math.pi * (.15 + .8 * t)) ** .8 * (1 - t * .45) + .15
        k.blob('main', 'cypress', r, rnd.uniform(-.08, .08), y, rnd.uniform(-.08, .08), sy=1.9, sub=2, rough=.22, seed=i + 70)
    return dict(circ=.4)

@prop('olive')
def _(k):
    """オリーブ: ねじれた低い幹・銀緑色のまばらな樹冠"""
    k.tube('main', 'barkP', [(0, 0, 0), (.3, .8, .1), (.1, 1.5, -.1)], .3); k.tube('main', 'barkP', [(.1, 1.3, 0), (-.9, 2.3, .4)], .18); k.tube('main', 'barkP', [(.1, 1.4, 0), (.9, 2.4, -.3)], .18)
    rnd = random.Random(23)
    for i in range(6): a = i * 1.1; k.blob('main', 'olive', .9 + rnd.random() * .3, math.cos(a) * 1.1, 2.6 + (i % 2) * .5, math.sin(a) * 1.1, sy=.7, sub=2, rough=.4, seed=i + 80)
    return dict(circ=.45)

@prop('umbrella_pine')
def _(k):
    """カサマツ(イタリアカサマツ): 高くまっすぐな幹と、平たく広い笠形の樹冠"""
    k.tube('main', 'bark', [(0, 0, 0), (.3, 5, .1), (.5, 8.5, .2)], .32)
    for a in range(5): k.tube('main', 'bark', [(.5, 8.2, .2), (math.cos(a * 1.25) * 2.4, 9.6, math.sin(a * 1.25) * 2.4)], .14)
    rnd = random.Random(25)
    for i in range(8): a = i * .8; r = 2.6 if i < 7 else 0; k.blob('main', 'pineU', 1.8 + rnd.random() * .4, math.cos(a) * r, 10.2 + rnd.random() * .5, math.sin(a) * r, sy=.42, sub=2, rough=.3, seed=i + 90)
    return dict(circ=.45)

@prop('vitaleta')
def _(k):
    """ヴィタレータ礼拝堂: 白いトラバーチンの正面(付柱・破風・バラ窓のない丸窓)・石の身廊・テラコッタの屋根・後ろの小さな鐘楼"""
    W, D, H = 6.4, 11, 7.2
    k.box('main', 'tuffo', W, H, D, 0, H / 2, -.2, bev=.05)
    # 屋根(切妻・棟は z 方向)
    for sx in (-1, 1):
        k.box('main', 'terra', W / 2 / math.cos(.6) + .5, .25, D + .2, sx * W / 4, H + 1.0, -.2, roll=sx * .6, bev=.03)
    fz = D / 2 - .2 + .3                                                                  # 正面(+z)
    k.box('main', 'trav', W + .6, H + .4, .6, 0, (H + .4) / 2, fz, bev=.04)
    for x in (-W / 2, -W / 6, W / 6, W / 2): k.box('main', 'trav', .55, H - .4, .3, x, (H - .4) / 2 + .2, fz + .4, bev=.03)   # 付柱
    k.box('main', 'trav', W + 1, .5, .5, 0, H + .1, fz + .3, bev=.03)
    for i in range(10):  # 破風(三角形を薄板で)
        t0 = i / 10; w = (W + 1) * (1 - t0); k.box('main', 'trav', w, .24, .55, 0, H + .45 + t0 * 2.3, fz + .1, bev=0)
    k.box('main', 'woodD', 1.5, 2.8, .1, 0, 1.4, fz + .32, bev=0); k.box('main', 'trav', 2.2, .35, .3, 0, 3.0, fz + .45, bev=.02)
    k.cyl('main', 'glass', .9, .1, 0, 4.6, fz + .32, 'z', 16, 0); k.torus('main', 'trav', .5, .08, 0, 4.6, fz + .35, 'z', 16, 4)
    k.box('main', 'tuffo', 2.0, 4.2, 2.0, 0, H + 1.8, -D / 2 + .8, bev=.04)                # 鐘楼
    k.box('main', 'black', 2.02, 1.2, .9, 0, H + 3.0, -D / 2 + .8, bev=0); k.box('main', 'black', .9, 1.2, 2.02, 0, H + 3.0, -D / 2 + .8, bev=0)
    k.cyl('main', 'terra', 2.9, 1.2, 0, H + 4.5, -D / 2 + .8, 'y', 4, .02, d2=0)
    k.box('main', 'tuffo', 7.5, .2, 1.8, 0, .1, fz + 1.3, bev=.02)
    return dict(box=[W + 1, D + 1.4, H + 2])

@prop('podere')
def _(k):
    """トスカーナの農家(ポデーレ): 切石と漆喰の母屋・寄棟のテラコッタ屋根・鳩小屋の塔・アーチのロッジア・外階段"""
    k.box('main', 'tuffo', 14, 7, 9, 0, 3.5, 0, bev=.06)
    k.box('main', 'terra', 15, .3, 10, 0, 7.15, 0, bev=.03)
    for sz in (-1, 1): k.box('main', 'terra', 15.2, .25, 5.6, 0, 8.3, sz * 2.45, pitch=-sz * .42, bev=.02)
    k.box('main', 'tuffo', 4, 11, 4, 4.5, 5.5, -1.5, bev=.06)                              # 鳩小屋の塔
    for sz in (-1, 1): k.box('main', 'terra', 4.8, .25, 2.7, 4.5, 11.5, -1.5 + sz * 1.1, pitch=-sz * .42, bev=.02)
    for i in range(3): k.box('main', 'black', .5, .5, .05, 3.6 + i * .9, 9.6, .52, bev=0)
    for i in range(3): k.box('main', 'black', 1.2, 2.2, .1, -5 + i * 2.2, 1.6, 4.52, bev=0) if i != 1 else None
    for i in range(4): k.box('main', 'woodD', .9, 1.2, .1, -5.4 + i * 2.2, 5, 4.52, bev=0); k.box('main', 'woodD', .1, 1.2, .9, 7.02, 5, -3 + i * 2, bev=0)
    k.box('main', 'tuffo', 5, 4, 3, -3.5, 2, 6, bev=.04); k.box('main', 'black', 3.8, 2.6, 3.02, -3.5, 1.6, 6, bev=0)   # ロッジア
    k.box('main', 'terra', 5.6, .25, 3.6, -3.5, 4.2, 6.2, pitch=.2, bev=.02)
    for i in range(8): k.box('main', 'tuffo', 1.3, .4, .6, 3.2, .2 + i * .42, 7.6 - i * .36, bev=.02)
    return dict(boxes=[[0, 0, 14, 9, 9], [4.5, -1.5, 4, 4, 12], [-3.5, 6, 5, 3, 4.5]])

@prop('vine_row')
def _(k):
    for z in (-4, -2, 0, 2, 4): k.cyl('main', 'woodD', .08, 1.6, 0, .8, z, 'y', 4, 0)
    for y in (.7, 1.2): k.tube('main', 'iron', [(0, y, -4), (0, y, 4)], .01)
    rnd = random.Random(31)
    for i in range(14): k.blob('main', 'vine', .32 + rnd.random() * .12, rnd.uniform(-.1, .1), 1.0 + rnd.uniform(-.1, .2), -3.8 + i * .58, sy=1.2, sub=1, rough=.35, seed=i + 100)
    return dict()

# ================================================================ 追加の名所・小物
@prop('hms_belfast')
def _(k):
    """軽巡洋艦ベルファスト(テムズ川に係留・縮尺0.5): 灰色の船体と迷彩・艦橋・2本の煙突・4基の3連装砲塔・マスト"""
    L, B = 72, 7.6
    k.prism('main', 'grey', [(-L / 2, -2.5), (L / 2 - 6, -2.5), (L / 2, 1), (L / 2 + 1.5, 3.2), (-L / 2 + 1, 2.6), (-L / 2, 1)], -B / 2, B / 2, 'x', .15, 2)
    k.box('main', 'dgrey', B + .05, .9, L - 6, 0, -1.8, -1, bev=.03)
    for (z, l, c) in ((-14, 10, 'dgrey'), (8, 8, 'ltblue'), (20, 6, 'dgrey')): k.box('main', c, B + .06, 2.2, l, 0, 1.3, z, bev=0)   # 迷彩
    k.box('main', 'grey', 6, 3, 30, 0, 4.2, 0, bev=.1)
    k.box('main', 'grey', 5, 4, 7, 0, 7.6, 10, bev=.08); k.box('main', 'grey', 6, 1.4, 4, 0, 10.2, 11, bev=.06); k.box('main', 'glass', 6.05, .6, 3.4, 0, 10.4, 11, bev=0)
    for z in (2, -6): k.cyl('main', 'grey', 2.6, 6, 0, 8.6, z, 'y', 14, .05, d2=2.3); k.cyl('main', 'black', 2.4, .4, 0, 11.6, z, 'y', 14, 0)
    k.tube('main', 'grey', [(0, 9, 12), (0, 20, 11.5)], .25); k.tube('main', 'grey', [(0, 8, -9), (0, 17, -9.5)], .2)
    k.box('main', 'grey', 4, .2, .2, 0, 17, 11.6, bev=0)
    for (z, y, r) in ((24, 3.8, 0), (18, 5.2, 0), (-16, 5.2, math.pi), (-23, 3.8, math.pi)):
        k.lathe('main', 'grey', [(0, y), (2.2, y), (2.0, y + 1.6), (0, y + 1.7)], 0, 0, z, 12)
        for dx in (-.6, 0, .6): k.cyl('main', 'grey', .35, 6, dx, y + .8, z + (3 if r == 0 else -3), 'z', 6, 0)
    return dict(box=[B, L + 2, 6], ground=-1.0)

@prop('city_hall')
def _(k):
    """旧ロンドン市庁舎(傾いた卵形のガラスの建物・縮尺0.6)"""
    prof = [(0, 0), (11, 0), (13.5, 5), (14.2, 10), (13.6, 15), (11.5, 20), (8, 24.5), (3.5, 27), (0, 27.6)]
    o = k.lathe('main', 'glassL', prof, 0, 0, 0, 28)
    import bpy
    o.rotation_euler = (math.radians(-8), 0, 0); o.location = pm.G(0, 0, -1.5)
    for i, (r, h) in enumerate(prof[1:-1]):
        t = k.torus('main', 'steel', r + .08, .12, 0, h, 0, 'y', 28, 4); t.rotation_euler = o.rotation_euler; t.location = o.location
    return dict(circ=12.5)

@prop('dock_crane')
def _(k):
    """岸壁の古いクレーン(セント・キャサリン・ドック/シャッド・テムズ): 鉄の脚・回転台・腕"""
    for sx in (-1, 1):
        for sz in (-1, 1): k.box('main', 'black', .4, 6, .4, sx * 1.5, 3, sz * 1.5, bev=0)
    k.box('main', 'black', 3.6, .4, 3.6, 0, 6.1, 0, bev=0); k.box('main', 'black', 2.4, 2.2, 3, 0, 7.4, 0, bev=.05)
    k.seg('main', 'black', .4, .5, -1, 7.6, 9, 14, 0, bev=0); k.tube('main', 'iron', [(0, 14, 9), (0, 9, 9.2)], .03); k.box('main', 'iron', .6, .6, .6, 0, 8.7, 9.2, bev=.05)
    return dict(box=[3.6, 3.6, 8])

@prop('suzuran')
def _(k):
    """商店街のすずらん灯: 柱から左右に下がる2つの灯と、商店街の旗"""
    k.cyl('main', 'grey', .2, 6, 0, 3, 0, 'y', 8, 0)
    for sx in (-1, 1):
        k.tube('main', 'grey', [(0, 5.4, 0), (sx * .6, 5.8, 0), (sx * .9, 5.4, 0)], .04)
        k.lathe('main', 'lampW', [(0, 4.6), (.26, 4.8), (.3, 5.05), (.12, 5.2), (0, 5.25)], sx * .9, 0, 0, 10)
    k.box('main', 'white', .04, 1.4, .6, 0, 3.6, .35, bev=0); k.box('main', 'red', .05, .3, .62, 0, 4.2, .35, bev=0)
    return dict(circ=.25)

@prop('nobori')
def _(k):
    rnd = random.Random(41)
    for i in range(3):
        x = i * 1.1; c = ['red', 'blue', 'yellow'][i]
        k.cyl('main', 'white', .05, 3.4, x, 1.7, 0, 'y', 4, 0)
        k.box('main', c, .5, 2.4, .02, x + .3, 2.0, 0, bev=0); k.box('main', 'white', .2, 1.8, .03, x + .3, 2.0, 0, bev=0)
    return dict()

@prop('hesco')
def _(k):
    for i in range(4):
        k.box('main', 'khaki', 1.1, 1.3, 1.1, -1.65 + i * 1.1, .65, 0, bev=.03)
        for y in (.2, .65, 1.1): k.box('main', 'iron', 1.12, .02, 1.12, -1.65 + i * 1.1, y, 0, bev=0)
    return dict(box=[4.4, 1.2, 1.3])

@prop('greenhouse')
def _(k):
    """アブダリの農場のビニールハウス(かまぼこ形)"""
    for i in range(9):
        z = -8 + i * 2; k.torus('main', 'steel', 2.6, .05, 0, 0, z, 'z', 16, 4)
    prof = [(math.cos(a) * 2.6, math.sin(a) * 2.6) for a in [i * math.pi / 10 for i in range(11)]]
    for j in range(10):
        (x0, y0), (x1, y1) = prof[j], prof[j + 1]
        k.grid('main', 'canvasW', [[(x0, y0, -8.2), (x0, y0, 8.2)], [(x1, y1, -8.2), (x1, y1, 8.2)]])
    return dict(box=[5.4, 16.6, 2.8])

@prop('u_sign')
def _(k):
    k.cyl('main', 'grey', .12, 3.4, 0, 1.7, 0, 'y', 6, 0)
    k.box('main', 'blue', .9, .9, .08, 0, 3.6, 0, bev=.02); k.box('main', 'white', .14, .55, .1, -.18, 3.62, 0, bev=0); k.box('main', 'white', .14, .55, .1, .18, 3.62, 0, bev=0); k.box('main', 'white', .5, .14, .1, 0, 3.4, 0, bev=0)
    for sx in (-1, 1): k.box('main', 'grey', .1, .9, 4, sx * 1.5, .45, -2, bev=0)            # 地下への階段の手すり
    return dict()

@prop('berliner_dom')
def _(k):
    """ベルリン大聖堂(遠景用): 緑青の大ドーム・四隅の小ドーム・砂岩の本体"""
    k.box('main', 'sandst', 70, 30, 60, 0, 15, 0, bev=.2)
    k.lathe('main', 'sandst', [(0, 30), (17, 30), (17, 42), (0, 42)], 0, 0, 0, 24)
    k.lathe('main', 'copper', [(0, 42), (18, 42), (17, 50), (14, 58), (9, 64), (3, 67), (0, 67.5)], 0, 0, 0, 24)
    k.lathe('main', 'copper', [(0, 67), (2.5, 67), (2, 73), (.4, 77), (0, 78)], 0, 0, 0, 12)
    for sx in (-1, 1):
        for sz in (-1, 1):
            k.box('main', 'sandst', 12, 40, 12, sx * 30, 20, sz * 25, bev=.1)
            k.lathe('main', 'copper', [(0, 40), (6, 40), (5, 45), (2, 49), (0, 50)], sx * 30, 0, sz * 25, 16)
    return dict()

@prop('bvg_bus')
def _(k):
    """ベルリンの黄色い2階建てバス(BVG)"""
    PAL['bvgY'] = ((.95, .78, .1), 'paint')
    L, W, H = 8.6, 2.0, 3.3
    k.box('main', 'bvgY', W, H - .3, L, 0, H / 2 + .25, 0, bev=.2)
    for y in (1.55, 2.95):
        for sx in (-1, 1): k.box('main', 'glass', .05, .75, L - 1.2, sx * (W / 2 + .01), y, -.2, bev=0)
    k.box('main', 'glass', W - .3, 1.1, .05, 0, 1.6, L / 2 + .01, bev=0); k.box('main', 'glass', W - .3, .7, .05, 0, 2.95, L / 2 + .01, bev=0)
    k.box('main', 'black', 1.2, .3, .06, 0, 3.45, L / 2 + .02, bev=0); k.box('main', 'lampY', 1.0, .2, .07, 0, 3.45, L / 2 + .02, bev=0)
    for z in (-2.7, 2.6):
        for sx in (-1, 1): k.wheel('main', sx * (W / 2 - .2), .45, z, .9, .3, 'grey')
    return dict(box=[W + .1, L + .1, H + .2])

@prop('siegessaule')
def _(k):
    """戦勝記念塔(遠景用): 赤い花崗岩の台座・砂岩の柱(金の帯)・金色の勝利の女神"""
    k.lathe('main', 'sandstD', [(0, 0), (14, 0), (14, 6), (11, 6), (11, 14), (0, 14)], 0, 0, 0, 16)
    k.lathe('main', 'sandst', [(0, 14), (4.2, 14), (3.6, 54), (0, 54)], 0, 0, 0, 16)
    for y in (26, 34, 42): k.torus('main', 'gold', 4.0 - (y - 14) * .012, .5, 0, y, 0, 'y', 16, 4)
    k.lathe('main', 'sandst', [(0, 54), (5, 54), (5, 56), (0, 56)], 0, 0, 0, 16)
    k.cyl('main', 'gold', 2.4, 7, 0, 60, 0, 'y', 10, .05, d2=1.4); k.blob('main', 'gold', 1.0, 0, 64.5, 0, sub=1, rough=0)
    for sx in (-1, 1): k.box('main', 'gold', 4, 1.6, .3, sx * 2.2, 63, -.6, roll=sx * .5, bev=.1)
    return dict()

@prop('shard')
def _(k):
    """ザ・シャード(遠景用・310m→240): 傾いたガラスの面が集まる細長いピラミッド"""
    k.lathe('main', 'glassL', [(0, 0), (30, 0), (24, 60), (16, 130), (8, 195), (2.5, 232), (0, 240)], 0, 0, 0, 4)
    for i in range(4):
        a = i * math.pi / 2 + math.pi / 4; k.tube('main', 'steel', [(math.cos(a) * r, h, math.sin(a) * r) for r, h in ((30, 0), (24, 60), (16, 130), (8, 195), (2.5, 232))], .5)
    return dict()

@prop('gherkin')
def _(k):
    """30セント・メリー・アクス(ガーキン・遠景用): 卵形のガラスの塔と、らせんの濃い帯"""
    prof = [(r, h) for r, h in ((0, 0), (17, 0), (21, 30), (22, 60), (19, 100), (12, 125), (4, 138), (0, 140))]
    k.lathe('main', 'glassL', prof, 0, 0, 0, 24)
    for i in range(6):
        pts = []
        for j in range(15):
            t = j / 14; h = 140 * t; r = 0
            for (r0, h0), (r1, h1) in zip(prof[:-1], prof[1:]):
                if h0 <= h <= h1 and h1 > h0: r = r0 + (r1 - r0) * (h - h0) / (h1 - h0)
            a = i * math.pi / 3 + t * 4; pts.append((math.cos(a) * (r + .3), h, math.sin(a) * (r + .3)))
        k.tube('main', 'glass', pts, 1.6)
    return dict()

@prop('walkie')
def _(k):
    """20フェンチャーチ・ストリート(ウォーキートーキー・遠景用): 上ほど広がるガラスの塔"""
    k.prism('main', 'glassL', [(-16, 0), (16, 0), (22, 90), (18, 120), (-14, 124), (-20, 95)], -18, 18, 'x', .2, 1)
    return dict()

@prop('stpauls')
def _(k):
    """セント・ポール大聖堂(遠景用): ドラムと列柱・鉛のドーム・頂塔と金の十字、西正面の2本の塔"""
    k.box('main', 'portland', 90, 26, 30, 0, 13, 0, bev=.2); k.box('main', 'portland', 30, 26, 70, 0, 13, 0, bev=.2)
    k.lathe('main', 'portland', [(0, 26), (16, 26), (16, 40), (14, 40), (14, 48), (0, 48)], 0, 0, 0, 24)
    k.lathe('main', 'lead', [(0, 48), (15, 48), (14.5, 54), (12, 62), (7, 68), (2, 71), (0, 71)], 0, 0, 0, 24)
    k.lathe('main', 'portland', [(0, 71), (3, 71), (2.5, 80), (0, 80)], 0, 0, 0, 12); k.cyl('main', 'gold', 1.2, 5, 0, 83, 0, 'y', 8, 0)
    for sz in (-1, 1): k.box('main', 'portland', 9, 46, 9, -40, 23, sz * 10, bev=.1); k.cyl('main', 'lead', 7, 8, -40, 50, sz * 10, 'y', 12, .1, d2=0)
    return dict()

# ================================================================ 実在の車をモデルにした車(名前・ロゴは付けず形で表す)
PAL.update({'pearl': ((.94, .94, .91), 'paint'), 'beige2': ((.8, .74, .6), 'paint'), 'brg': ((.08, .25, .15), 'paint'), 'navy2': ((.12, .16, .3), 'paint')})

def veh(k, col, W, body, cab, axles, wd=.55, roof=None, lights=None, bev=.08):
    """側面形(z,y)の車体 body とキャビン cab=[前下,前上,後上,後下] から車を作る。axles=前後の車軸の z"""
    k.prism('main', col, body, -W / 2, W / 2, 'x', bev, 2)
    k.prism('main', roof or col, cab, -W / 2 + .07, W / 2 - .07, 'x', .05, 1)
    cx = sum(p[0] for p in cab) / 4; cy = sum(p[1] for p in cab) / 4
    win = [(cx + (p[0] - cx) * .84, cy + (p[1] - cy) * .72) for p in cab]; bp = (win[1][0] + win[2][0]) / 2
    for sx in (-1, 1):
        a, b = sorted((sx * (W / 2 - .075), sx * (W / 2 - .055)))
        k.prism('main', 'glass', [win[0], win[1], (bp + .05, win[1][1]), (bp + .05, win[0][1])], a, b, 'x', 0, 1)
        k.prism('main', 'glass', [(bp - .05, win[3][1]), (bp - .05, win[2][1]), win[2], win[3]], a, b, 'x', 0, 1)
    for (p0, p1, sg) in ((cab[0], cab[1], 1), (cab[2], cab[3], -1)):
        dz, dy = p1[0] - p0[0], p1[1] - p0[1]; n = math.hypot(dz, dy); oz, oy = dy / n * .025 * sg, -dz / n * .025 * sg
        k.seg('main', 'glass', W - .34, .02, p0[0] + dz * .1 + oz, p0[1] + dy * .1 + oy, p1[0] - dz * .1 + oz, p1[1] - dy * .1 + oy, 0, bev=0)
    zf = max(p[0] for p in body); zr = min(p[0] for p in body); (fy, ry_) = lights or (.55, .6)
    for sx in (-1, 1):
        k.box('main', 'lampW', .26, .12, .05, sx * (W / 2 - .2), fy, zf + .01, bev=.01)
        k.box('main', 'lampR', .22, .14, .05, sx * (W / 2 - .18), ry_, zr - .01, bev=.01)
        k.box('main', col, .07, .08, .14, sx * (W / 2 + .03), cab[0][1] + .1, cab[0][0] - .12, bev=.02)
        for z in axles: k.wheel('main', sx * (W / 2 - .12), wd / 2, z, wd, .22, 'alu')
    k.box('main', 'dgrey', W - .5, .12, .05, 0, fy - .12, zf + .02, bev=.01); k.box('main', 'white', .42, .12, .02, 0, fy - .25, zf + .04, bev=0)
    k.box('main', 'black', W + .02, .1, (axles[0] - axles[-1]) - wd, 0, wd / 2, (axles[0] + axles[-1]) / 2, bev=.02)

def pickup_bed(k, col, W, z0, z1, y0, h):
    k.box('main', 'dgrey', W - .1, .08, z1 - z0, 0, y0 + .04, (z0 + z1) / 2, bev=0)
    for sx in (-1, 1): k.box('main', col, .07, h, z1 - z0, sx * (W / 2 - .035), y0 + h / 2, (z0 + z1) / 2, bev=.02)
    k.box('main', col, W, h, .07, 0, y0 + h / 2, z0 + .035, bev=.02)

V = {
  'prius': lambda k, c: (veh(k, c, 1.35, [(-1.75, .25), (1.75, .25), (1.78, .48), (1.5, .62), (.7, .72), (-1.5, .84), (-1.76, .62)], [(.74, .72), (-.1, 1.12), (-.75, 1.1), (-1.55, .84)], [1.05, -1.05], .5, lights=(.55, .7)), dict(box=[1.4, 3.6, 1.2])),
  'nbox': lambda k, c: (veh(k, c, 1.13, [(-1.3, .22), (1.3, .22), (1.32, .55), (1.1, .7), (-1.3, .72)], [(1.05, .72), (.78, 1.36), (-1.25, 1.38), (-1.3, .74)], [.85, -.85], .46), dict(box=[1.15, 2.7, 1.4])),
  'hiace': lambda k, c: (veh(k, c, 1.32, [(-1.8, .28), (1.8, .28), (1.82, .6), (1.75, .8), (-1.8, .8)], [(1.72, .82), (1.5, 1.5), (-1.78, 1.52), (-1.8, .82)], [1.15, -1.25], .52, lights=(.62, .66)), dict(box=[1.35, 3.7, 1.55])),
  'golf': lambda k, c: (veh(k, c, 1.36, [(-1.62, .25), (1.62, .25), (1.65, .5), (1.4, .66), (.6, .72), (-1.55, .74), (-1.64, .55)], [(.62, .72), (0, 1.1), (-1.2, 1.1), (-1.55, .76)], [1.0, -1.0], .5), dict(box=[1.4, 3.35, 1.15])),
  'eclass': lambda k, c: (veh(k, c, 1.42, [(-1.85, .26), (1.85, .26), (1.88, .52), (1.6, .68), (.75, .74), (-1.35, .76), (-1.8, .7), (-1.86, .5)], [(.78, .74), (.15, 1.12), (-.75, 1.12), (-1.4, .78)], [1.15, -1.1], .52), dict(box=[1.45, 3.8, 1.15])),
  'mini': lambda k, c: (veh(k, c, 1.33, [(-1.45, .24), (1.45, .24), (1.48, .5), (1.3, .66), (.7, .7), (-1.45, .72)], [(.75, .7), (.45, 1.08), (-1.38, 1.08), (-1.45, .74)], [.95, -.95], .48, roof='white', bev=.12), dict(box=[1.35, 3.0, 1.1])),
  'rangerover': lambda k, c: (veh(k, c, 1.5, [(-1.9, .35), (1.9, .35), (1.92, .75), (1.7, .9), (-1.9, .92)], [(1.2, .92), (.75, 1.38), (-1.8, 1.4), (-1.88, .94)], [1.3, -1.3], .62, roof='black', lights=(.78, .82)), dict(box=[1.55, 3.9, 1.45])),
  'landcruiser': lambda k, c: (veh(k, c, 1.45, [(-1.8, .4), (1.8, .4), (1.83, .85), (1.7, .98), (-1.8, 1.0)], [(1.05, .98), (.75, 1.5), (-1.78, 1.52), (-1.8, 1.0)], [1.15, -1.15], .64, lights=(.8, .85), bev=.05), k.wheel('main', 0, 1.0, -1.92, .62, .22, 'black'), dict(box=[1.5, 3.8, 1.55])),
  'panda': lambda k, c: (veh(k, c, 1.15, [(-1.38, .24), (1.38, .24), (1.4, .55), (1.25, .66), (.65, .68), (-1.38, .7)], [(.7, .68), (.42, 1.1), (-1.3, 1.1), (-1.38, .72)], [.85, -.85], .45, bev=.05), dict(box=[1.2, 2.85, 1.12])),
  'fiat500': lambda k, c: (veh(k, c, 1.0, [(-1.15, .22), (1.15, .22), (1.18, .45), (1.0, .6), (.4, .62), (-1.1, .62), (-1.17, .42)], [(.45, .62), (.15, .98), (-.55, .98), (-.95, .64)], [.72, -.72], .4, bev=.14), dict(box=[1.05, 2.4, 1.0])),
}
def hilux(k, c, gun=False):
    veh(k, c, 1.4, [(-2, .42), (2, .42), (2.03, .78), (1.8, .95), (-.78, .95), (-.78, .62), (-2, .62)], [(1.2, .95), (.75, 1.42), (-.7, 1.42), (-.75, .95)], [1.35, -1.25], .62, lights=(.82, .8))
    pickup_bed(k, c, 1.4, -2, -.78, .62, .5)
    if gun:  # 荷台の機関銃(テクニカル)
        k.cyl('main', 'iron', .12, 1.0, 0, 1.15, -1.4, 'y', 6, 0); k.box('main', 'iron', .25, .3, .9, 0, 1.75, -1.3, bev=.02)
        k.cyl('main', 'iron', .09, 1.6, 0, 1.78, -.4, 'z', 6, 0); k.box('main', 'iron', .5, .45, .05, 0, 1.6, -1.6, bev=0)
    return dict(box=[1.45, 4.1, 1.5])
def carry(k, c):
    k.prism('main', c, [(1.3, .3), (1.33, .62), (1.25, 1.3), (.45, 1.32), (.4, .62), (.4, .3)], -.57, .57, 'x', .06, 2)
    k.box('main', 'glass', 1.0, .5, .03, 0, 1.02, 1.3, pitch=.1, bev=0)
    for sx in (-1, 1): k.box('main', 'glass', .03, .42, .6, sx * .58, 1.0, .85, bev=0); k.box('main', 'lampW', .2, .12, .04, sx * .38, .55, 1.34, bev=0)
    k.box('main', 'dgrey', 1.14, .1, 2.6, 0, .3, 0, bev=.02); pickup_bed(k, c, 1.14, -1.3, .38, .38, .32)
    for sx in (-1, 1):
        for z in (.95, -.8): k.wheel('main', sx * .45, .21, z, .42, .18, 'alu')
    return dict(box=[1.15, 2.7, 1.35])
def ape(k, c):
    k.prism('main', c, [(.95, .25), (1.05, .7), (.95, 1.35), (.3, 1.4), (.2, .25)], -.45, .45, 'x', .12, 2)
    k.box('main', 'glass', .7, .45, .03, 0, 1.05, 1.0, pitch=.15, bev=0); k.box('main', 'lampW', .16, .12, .04, 0, .72, 1.07, bev=0)
    k.box('main', 'dgrey', .9, .08, 1.4, 0, .45, -.5, bev=0); pickup_bed(k, c, .9, -1.2, .2, .45, .35)
    k.wheel('main', 0, .2, .75, .4, .14, 'alu')
    for sx in (-1, 1): k.wheel('main', sx * .42, .2, -.8, .4, .14, 'alu')
    return dict(box=[.95, 2.3, 1.4])

VARIANTS = [('prius', 'pearl'), ('prius', 'silver'), ('nbox', 'white'), ('nbox', 'black'), ('hiace', 'white'), ('golf', 'red'), ('golf', 'silver'), ('eclass', 'black'), ('eclass', 'silver'),
            ('mini', 'brg'), ('mini', 'red'), ('rangerover', 'black'), ('landcruiser', 'beige2'), ('landcruiser', 'white'), ('panda', 'red'), ('fiat500', 'ltblue')]
for (shape, col) in VARIANTS:
    def _mk(shape, col):
        @prop('v_%s_%s' % (shape, col))
        def _(k): return V[shape](k, col)[-1]
    _mk(shape, col)
@prop('v_hilux_white')
def _(k): return hilux(k, 'white')
@prop('v_technical')
def _(k): return hilux(k, 'beige2', gun=True)
@prop('v_carry_white')
def _(k): return carry(k, 'white')
@prop('v_ape')
def _(k): return ape(k, 'ltblue')

# ================================================================ ゴラン高原・アルデンヌ高地
PAL.update({'basalt': ((.17, .16, .16), 'paint'), 'basaltL': ((.3, .29, .28), 'paint'), 'snow': ((.92, .94, .97), 'paint'), 'slate': ((.22, .23, .26), 'paint'),
            'shale': ((.42, .4, .38), 'paint'), 'spruce': ((.08, .16, .1), 'leaf'), 'turbW': ((.9, .91, .92), 'paint'), 'signY': ((.95, .8, .1), 'paint')})

@prop('wind_turbine')
def _(k):
    """ゴラン高原の風力発電機(資料: 台地の上の風力発電所。白い円筒の塔と3枚羽根)。縮尺を詰めて高さ約40。rotor が回る"""
    k.cyl('main', 'turbW', 2.4, 36, 0, 18, 0, 'y', 16, .02, d2=1.4)
    k.box('main', 'turbW', 2, 2, 5, 0, 37, .6, bev=.4)
    k.blob('rotor', 'turbW', 1.0, 0, 37, 3.4, sy=1, sub=2, rough=0)
    for i in range(3):
        a = i * 2 * math.pi / 3
        k.box('rotor', 'turbW', .9, 17, .25, math.sin(a) * 8.6, 37 + math.cos(a) * 8.6, 3.6, roll=-a, bev=.08)
    return dict(circ=1.3, pivots={'rotor': [0, 37, 3.6, 'z']})

@prop('minesign')
def _(k):
    """地雷原の柵と警告標識(資料: ゴラン高原には未処理の地雷原が残り、道の脇は立入禁止)。杭・有刺鉄線・黄色地に赤い三角の板"""
    for x in (-2, 2): k.cyl('main', 'rust', .1, 1.4, x, .7, 0, 'y', 5, 0)
    for y in (.4, .8, 1.2): k.tube('main', 'iron', [(-2, y, 0), (0, y - .05, 0), (2, y, 0)], .015)
    k.box('main', 'signY', .7, .5, .03, 0, 1.0, .06, bev=0)
    for i in range(4): k.box('main', 'red', .34 - i * .08, .06, .02, 0, .86 + i * .06, .08, bev=0)          # 赤い三角(段で描く)
    return dict(box=[4.2, .4, 1.4])

@prop('basalt_rocks')
def _(k):
    rnd = random.Random(61)
    for i in range(5): k.blob('main', 'basalt' if i % 2 else 'basaltL', .5 + rnd.random() * .7, rnd.uniform(-1.5, 1.5), .2, rnd.uniform(-1.2, 1.2), sy=.6, sub=2, rough=.35, seed=i + 120)
    return dict(circ=1.8)

@prop('ruin_block')
def _(k):
    """クネイトラの廃墟(資料: 1967〜73年の戦いで破壊され放棄された町)。崩れた鉄筋コンクリートの床版・残った柱と壁の一部"""
    k.box('main', 'conc', 9, 3.2, .3, 0, 1.6, -3.8, bev=.05); k.box('main', 'conc', .3, 2.4, 7, -4.4, 1.2, 0, bev=.05)
    for x, z in ((-4, -3.6), (0, -3.6), (4, -3.6), (-4, 3), (4, 3)): k.box('main', 'conc', .4, 3 if x < 2 else 1.6, .4, x, 1.5 if x < 2 else .8, z, bev=.03)
    k.box('main', 'conc', 9, .3, 4, -.3, 2.2, -1.6, roll=.12, bev=.04)                 # 傾いて落ちた上の階の床
    k.box('main', 'conc', 6, .3, 5, 1.3, .5, 1.8, pitch=.25, roll=-.1, bev=.04)
    rnd = random.Random(62)
    for i in range(10): k.blob('main', 'conc', .3 + rnd.random() * .4, rnd.uniform(-4, 4), .2, rnd.uniform(-3, 4), sy=.6, sub=1, rough=.3, seed=i + 130)
    for i in range(4): k.tube('main', 'rust', [(rnd.uniform(-4, 4), 2.2, -3.6), (rnd.uniform(-4, 4), 3.4, -3.4)], .03)  # 鉄筋
    return dict(box=[9.4, 8, 3.4])

@prop('spruce_snow')
def _(k):
    """アルデンヌのトウヒ(資料: 森の台地。冬のバルジの戦いの戦場)。濃い緑の円錐の層に雪が積もる"""
    k.cyl('main', 'bark', .35, 2, 0, 1, 0, 'y', 8, 0, d2=.2)
    for i in range(6):
        r = 1.9 - i * .28; y = 1.4 + i * 1.0
        k.lathe('main', 'spruce', [(0, y + 1.7), (r * .3, y + 1.25), (r, y + .05), (r * .85, y), (0, y)], 0, 0, 0, 10)
        k.lathe('main', 'snow', [(0, y + 1.72), (r * .28, y + 1.3), (r * .82, y + .42), (r * .7, y + .36), (0, y + 1.2)], 0, 0, 0, 10, cap=False)
    return dict(circ=.45)

@prop('church_ard')
def _(k):
    """アルデンヌの村の教会(資料: 灰色の頁岩の石積み、厚いスレート屋根)。身廊・西の塔と尖ったスレートの尖塔・雪"""
    k.box('main', 'shale', 7, 6.5, 14, 0, 3.25, 0, bev=.05)
    for sz in (-1, 1): k.box('main', 'slate', 4.6, .25, 15, sz * 1.9, 7.6, 0, roll=sz * .62, bev=.03); k.box('main', 'snow', 4.5, .08, 14.8, sz * 1.92, 7.78, 0, roll=sz * .62, bev=0)
    k.box('main', 'shale', 4.2, 12, 4.2, 0, 6, -8.6, bev=.05)
    k.cyl('main', 'slate', 5.4, 9, 0, 16.5, -8.6, 'y', 8, .02, d2=0); k.cyl('main', 'gold', .1, 1.6, 0, 21.6, -8.6, 'y', 4, 0); k.box('main', 'gold', .8, .1, .1, 0, 21.8, -8.6, bev=0)
    for i in range(4): k.box('main', 'glass', .1, 2.2, .9, 3.52, 3.5, -4.5 + i * 3, bev=0); k.box('main', 'glass', .1, 2.2, .9, -3.52, 3.5, -4.5 + i * 3, bev=0)
    k.box('main', 'woodD', 1.4, 2.6, .1, 0, 1.3, -10.72, bev=0)
    return dict(boxes=[[0, 0, 7, 14, 7], [0, -8.6, 4.2, 4.2, 12]])

@prop('foxhole')
def _(k):
    """バルジの戦いの塹壕(たこつぼ)(資料: 森には当時の塹壕のくぼみが今も残る)。掘り上げた土の縁・丸太の屋根・土嚢"""
    for a in range(10): ang = a / 10 * 6.283; k.blob('main', 'snow' if a % 3 else 'woodD', .55, math.cos(ang) * 1.6, .15, math.sin(ang) * 1.3, sy=.5, sub=1, rough=.3, seed=a + 140)
    for i in range(4): k.cyl('main', 'bark', .22, 3.2, -.6 + i * .4, .45, 0, 'x', 8, 0)
    for i in range(3): k.box('main', 'khaki', .9, .32, .5, -1 + i * .95, .3, -1.4, bev=.08)
    return dict(circ=1.8)

@prop('log_pile')
def _(k):
    for r in range(3):
        for i in range(4 - r): k.cyl('main', 'bark', .5, 4, -.75 + i * .5 + r * .25, .25 + r * .43, 0, 'z', 10, .02)
    k.box('main', 'snow', 1.6, .12, 4, 0, 1.35, 0, bev=.05)
    return dict(box=[2.2, 4.2, 1.4])

@prop('undof_post')
def _(k):
    """国連兵力引き離し監視軍(UNDOF)の監視所(資料: 1974年の兵力引き離し協定で設置)。白いプレハブ・見張り台・フェンス・旗竿"""
    k.box('main', 'white', 6, 2.6, 2.6, 0, 1.3, 0, bev=.05); k.box('main', 'white', 6, 2.6, 2.6, 0, 1.3, 3.2, bev=.05)
    k.box('main', 'black', 2.4, .9, .05, 0, 2.1, -1.32, bev=0)
    for sx in (-1, 1):
        for sz in (-1, 1): k.cyl('main', 'white', .2, 5, 5 + sx * .9, 2.5, 1.6 + sz * .9, 'y', 6, 0)
    k.box('main', 'white', 2.4, 1.6, 2.4, 5, 5.6, 1.6, bev=.04); k.box('main', 'glass', 2.42, .5, 2.42, 5, 5.9, 1.6, bev=0)
    k.cyl('main', 'grey', .1, 7, -4, 3.5, 0, 'y', 6, 0); k.box('main', 'ltblue', 1.6, 1, .03, -3.15, 6.4, 0, bev=0)
    return dict(boxes=[[0, 1.6, 6.2, 6, 2.8], [5, 1.6, 2.4, 2.4, 7]])

LANDMARKS = [n for n in P if n not in BEFORE]

if __name__ == '__main__':
    OUT = sys.argv[1]; ONLY = sys.argv[2:]
    mine = ONLY or LANDMARKS
    os.makedirs(OUT, exist_ok=True)
    for n in mine:
        buf = bytearray(); out = {}; build(n, buf, out)
        open(os.path.join(OUT, n + '.bin'), 'wb').write(bytes(buf)); json.dump(out[n], open(os.path.join(OUT, n + '.json'), 'w'))
