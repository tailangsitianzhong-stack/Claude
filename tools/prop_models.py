# -*- coding: utf-8 -*-
"""
TANK 3D のマップ用の小物(車・信号・街灯・木・屋台・油井・風車…)を Blender(bpy)で作り、ゲーム用データに書き出す。

  python tools/prop_models.py <出力ディレクトリ> [小物名...]

- 形はゲーム座標(x=右, y=上, z=前, 1unit≒1.3m)で記述(tank_models.py の部品キットを利用)
- 部品ごとに色(パレット)を持たせ、Cycles で AO(陰影・接地の暗がり)を掛けた色を「頂点色」に焼き込む(テクスチャ不要で軽い)
- 動く部分(風車の羽根・油井の天秤など)は part を分けて、ゲーム側で回転させる
出力: 小物ごとに <名前>.bin + <名前>.json
"""
import os, sys, math, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh
import numpy as np
from mathutils import Vector, Euler, noise
from tank_models import G, Kit

OUT = sys.argv[1] if len(sys.argv) > 1 else '.'
ONLY = sys.argv[2:]

# 色(sRGB 0..1)と素材の種類: paint=塗装/つや消し metal=金属 glass=ガラス emit=発光 leaf=葉 rubber=ゴム
PAL = {
  'white': ((.92, .92, .9), 'paint'), 'silver': ((.68, .7, .72), 'paint'), 'black': ((.08, .08, .09), 'paint'), 'red': ((.62, .08, .07), 'paint'),
  'blue': ((.12, .24, .52), 'paint'), 'ltblue': ((.55, .72, .82), 'paint'), 'yellow': ((.92, .76, .2), 'paint'), 'cream': ((.9, .86, .74), 'paint'),
  'green': ((.16, .38, .22), 'paint'), 'grey': ((.55, .56, .57), 'paint'), 'dgrey': ((.25, .26, .27), 'paint'), 'conc': ((.66, .65, .62), 'paint'),
  'shaleS': ((.47, .45, .43), 'paint'), 'shaleD': ((.35, .33, .32), 'paint'), 'road': ((.3, .29, .28), 'paint'),
  'stone': ((.7, .66, .58), 'paint'), 'stoneD': ((.5, .47, .42), 'paint'), 'wood': ((.48, .33, .2), 'paint'), 'woodL': ((.68, .52, .34), 'paint'),
  'woodD': ((.3, .2, .12), 'paint'), 'rust': ((.42, .22, .12), 'paint'), 'rustL': ((.6, .36, .2), 'paint'), 'burnt': ((.14, .12, .11), 'paint'),
  'vermil': ((.82, .22, .12), 'paint'), 'canvasR': ((.72, .14, .12), 'paint'), 'canvasG': ((.14, .45, .25), 'paint'), 'canvasW': ((.94, .92, .86), 'paint'),
  'tentB': ((.12, .1, .09), 'paint'), 'tentS': ((.5, .38, .26), 'paint'), 'strawD': ((.62, .5, .26), 'paint'), 'mud': ((.3, .24, .18), 'paint'), 'straw': ((.82, .68, .38), 'paint'), 'wool': ((.9, .88, .82), 'paint'),
  'skin': ((.12, .1, .09), 'paint'), 'fruitR': ((.8, .15, .1), 'paint'), 'fruitO': ((.95, .55, .1), 'paint'), 'fruitG': ((.4, .7, .2), 'paint'),
  'steel': ((.42, .43, .45), 'metal'), 'chrome': ((.75, .76, .78), 'metal'), 'iron': ((.12, .12, .12), 'metal'), 'alu': ((.8, .8, .82), 'metal'),
  'glass': ((.07, .1, .13), 'glass'), 'glassL': ((.35, .45, .5), 'glass'), 'water': ((.18, .32, .36), 'glass'),
  'rubber': ((.05, .05, .05), 'rubber'),
  'lampW': ((1, .95, .82), 'emit'), 'lampY': ((1, .78, .35), 'emit'), 'lampR': ((1, .15, .08), 'emit'), 'lampG': ((.2, 1, .55), 'emit'), 'lampOff': ((.12, .12, .1), 'paint'),
  'leaf1': ((.24, .42, .16), 'leaf'), 'leaf2': ((.32, .5, .2), 'leaf'), 'leaf3': ((.2, .34, .14), 'leaf'), 'pine': ((.12, .26, .14), 'leaf'), 'palm': ((.3, .48, .18), 'leaf'), 'bark': ((.36, .27, .2), 'paint'),
  'barkP': ((.5, .4, .3), 'paint'),
}

class PK(Kit):
    """小物用の部品キット: 回転体・円環・葉の塊・板の並びを追加"""
    def lathe(s, part, col, prof, x, y, z, segs=16, bev=0, cap=True):
        bm = bmesh.new(); rings = []
        for (r, h) in prof:
            ring = [bm.verts.new(G(x + r * math.cos(a), y + h, z + r * math.sin(a))) for a in [i * 2 * math.pi / segs for i in range(segs)]]
            rings.append(ring)
        for i in range(len(rings) - 1):
            for j in range(segs):
                k = (j + 1) % segs
                try: bm.faces.new((rings[i][j], rings[i][k], rings[i + 1][k], rings[i + 1][j]))
                except ValueError: pass
        if cap:
            for ring in (rings[0], rings[-1]):
                if len(set(v.co.to_tuple(4) for v in ring)) > 2:
                    try: bm.faces.new(ring)
                    except ValueError: pass
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        me = bpy.data.meshes.new('l'); bm.to_mesh(me); bm.free()
        return s._add(me, part, col, bev)
    def torus(s, part, col, R, r, x, y, z, axis='x', segs=20, rsegs=6):
        bm = bmesh.new(); rings = []
        av = {'x': Vector((1, 0, 0)), 'y': Vector((0, 1, 0)), 'z': Vector((0, 0, 1))}[axis]
        for i in range(segs):
            a = i * 2 * math.pi / segs; ring = []
            for j in range(rsegs):
                b = j * 2 * math.pi / rsegs; rr = R + r * math.cos(b); yy = r * math.sin(b)
                # 輪はローカルの (u,v) 面、軸方向に yy
                if axis == 'x': p = (yy, rr * math.cos(a), rr * math.sin(a))
                elif axis == 'y': p = (rr * math.cos(a), yy, rr * math.sin(a))
                else: p = (rr * math.cos(a), rr * math.sin(a), yy)
                ring.append(bm.verts.new(G(x + p[0], y + p[1], z + p[2])))
            rings.append(ring)
        for i in range(segs):
            for j in range(rsegs):
                bm.faces.new((rings[i][j], rings[(i + 1) % segs][j], rings[(i + 1) % segs][(j + 1) % rsegs], rings[i][(j + 1) % rsegs]))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        me = bpy.data.meshes.new('t'); bm.to_mesh(me); bm.free()
        return s._add(me, part, col, 0)
    def blob(s, part, col, rad, x, y, z, sy=1, sub=2, rough=.25, seed=0):  # 葉の塊: 凹凸のある球
        bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=sub, radius=rad)
        for v in bm.verts:
            n = noise.noise(v.co * 2.2 + Vector((seed, seed * 1.7, seed * .3)))
            v.co *= 1 + rough * n; v.co.z *= sy
        bmesh.ops.translate(bm, vec=G(x, y, z), verts=bm.verts)
        me = bpy.data.meshes.new('bl'); bm.to_mesh(me); bm.free()
        return s._add(me, part, col, 0)
    def grid(s, part, col, pts):  # 点の格子(行×列)から面を張る(布・屋根の膜)
        bm = bmesh.new(); V = [[bm.verts.new(G(*p)) for p in row] for row in pts]
        for i in range(len(V) - 1):
            for j in range(len(V[0]) - 1): bm.faces.new((V[i][j], V[i][j + 1], V[i + 1][j + 1], V[i + 1][j]))
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        me = bpy.data.meshes.new('g'); bm.to_mesh(me); bm.free()
        o = s._add(me, part, col, 0); sol = o.modifiers.new('sol', 'SOLIDIFY'); sol.thickness = .04; return o
    def wheel(s, part, x, y, z, d, w, rim='alu', axis='x', segs=18):
        s.cyl(part, 'rubber', d, w, x, y, z, axis, segs, .03); s.cyl(part, rim, d * .62, w + .02, x, y, z, axis, segs, .01)
        s.cyl(part, 'dgrey', d * .2, w + .04, x, y, z, axis, 10, 0)
    def spokes(s, part, col, R, x, y, z, n=12, r=.008):
        for i in range(n):
            a = i * 2 * math.pi / n
            s.tube(part, col, [(x, y, z), (x, y + R * math.sin(a), z + R * math.cos(a))], r)

# ---------------------------------------------------------------- 小物の定義(戻り値: 当たり判定などのメタ情報)
P = {}
def prop(name):
    def deco(f): P[name] = f; return f
    return deco

def car_body(k, L, W, H, col, kei=False, lamps=True):
    """車体: 側面形を押し出した胴体+キャビン(窓)+屋根+灯火類+タイヤ"""
    if kei:
        body = [(-L/2, .22), (L/2, .22), (L/2 + .02, .5), (L/2 - .25, .62), (-L/2, .62)]
        cab = [(L/2 - .3, .63), (L/2 - .7, H - .05), (-L/2 + .05, H - .05), (-L/2 + .02, .63)]
    else:
        body = [(-L/2, .22), (L/2, .22), (L/2 + .03, .5), (L/2 - .25, .66), (.55, .74), (-1.25, .74), (-L/2 + .02, .66)]
        cab = [(.62, .74), (.05, H - .05), (-.95, H - .06), (-1.35, .75)]
    k.prism('main', col, body, -W/2, W/2, 'x', .06, 2)
    k.prism('main', col, cab, -W/2 + .07, W/2 - .07, 'x', .04, 1)                     # キャビン(車体色。窓ガラスは外側に貼る)
    cx = sum(p[0] for p in cab) / 4; cy = sum(p[1] for p in cab) / 4
    win = [(cx + (p[0] - cx) * .82, cy + (p[1] - cy) * .7) for p in cab]                # 側窓: キャビンの形を縮めたもの
    bpil = (win[1][0] + win[2][0]) / 2                                                  # Bピラーで前後の窓に分ける
    for sx in (-1, 1):
        x0 = sx * (W/2 - .075); x1 = sx * (W/2 - .055)
        k.prism('main', 'glass', [win[0], (win[1][0], win[1][1]), (bpil + .05, win[1][1]), (bpil + .05, win[0][1])], min(x0, x1), max(x0, x1), 'x', 0, 1)
        k.prism('main', 'glass', [(bpil - .05, win[3][1]), (bpil - .05, win[2][1]), win[2], win[3]], min(x0, x1), max(x0, x1), 'x', 0, 1)
    for (p0, p1, sgn) in ((cab[0], cab[1], 1), (cab[2], cab[3], -1)):                    # 前後のガラス(傾斜面に沿った薄板)
        dz, dy = p1[0] - p0[0], p1[1] - p0[1]; n = math.hypot(dz, dy); oz, oy = dy / n * .025 * sgn, -dz / n * .025 * sgn
        k.seg('main', 'glass', W - .34, .02, p0[0] + dz * .08 + oz, p0[1] + dy * .08 + oy, p1[0] - dz * .08 + oz, p1[1] - dy * .08 + oy, 0, bev=0)
    for sx in (-1, 1):  # ミラー・灯火
        k.box('main', 'lampW' if lamps else 'dgrey', .28, .1, .04, sx * (W/2 - .22), .52, L/2 + .02, bev=.01)
        k.box('main', 'lampR' if lamps else 'black', .24, .12, .04, sx * (W/2 - .2), .55, -L/2 - .01, bev=.01)
        k.box('main', col, .2, .08, .14, sx * (W/2 - .03), cab[0][1] + .08, cab[0][0] - .12, bev=.02)
    k.box('main', 'dgrey', W - .5, .12, .04, 0, .4, L/2 + .02, bev=.01)          # グリル
    k.box('main', 'white', .42, .12, .02, 0, .32, L/2 + .03, bev=0); k.box('main', 'white', .42, .12, .02, 0, .36, -L/2 - .02, bev=0)  # ナンバー
    for sz in (L/2 - .62, -L/2 + .62):
        for sx in (-1, 1): k.wheel('main', sx * (W/2 - .12), .27, sz, .54, .2, 'alu')
    k.box('main', 'black', W + .02, .1, L - .4, 0, .27, 0, bev=.02)                 # 車体下(ホイールハウスの影)

for colname in ('white', 'silver', 'black', 'red', 'blue'):
    def _mk(cn):
        @prop('car_' + cn)
        def _(k):
            car_body(k, 3.6, 1.36, 1.12, cn); return dict(box=[1.4, 3.7, 1.2])
        @prop('kei_' + cn)
        def _(k):
            car_body(k, 2.6, 1.12, 1.3, cn, kei=True); return dict(box=[1.15, 2.7, 1.35])
    _mk(colname)

@prop('car_burnt')
def _(k):
    car_body(k, 3.6, 1.36, 1.1, 'burnt', lamps=False)
    return dict(box=[1.4, 3.7, 1.2])

@prop('bike')
def _(k):
    for z in (-.42, .42):
        k.torus('main', 'rubber', .3, .025, 0, .33, z, 'x', 20, 5); k.spokes('main', 'chrome', .29, 0, .33, z, 12, .006)
    for a, b in [((0, .33, -.42), (0, .62, -.05)), ((0, .62, -.05), (0, .55, .32)), ((0, .33, -.42), (0, .33, .0)), ((0, .33, 0), (0, .62, -.05)), ((0, .33, 0), (0, .55, .32)), ((0, .55, .32), (0, .33, .42)), ((0, .55, .32), (0, .82, .36))]:
        k.tube('main', 'ltblue', [a, b], .02)
    k.box('main', 'black', .12, .05, .22, 0, .68, -.1, bev=.02); k.tube('main', 'chrome', [(-.24, .84, .38), (.24, .84, .38)], .015)
    k.box('main', 'chrome', .32, .2, .26, 0, .74, .56, bev=.01)   # 前かご
    return dict()

@prop('signal_g')
def _(k): return signal(k, 'lampG', 'lampOff', 'lampOff')
@prop('signal_r')
def _(k): return signal(k, 'lampOff', 'lampOff', 'lampR')
def signal(k, c1, c2, c3):
    """信号機: 柱・腕・横型の灯器(フード付き)・歩行者用信号"""
    k.cyl('main', 'grey', .24, 5, 0, 2.5, 0, 'y', 12, .02, d2=.2); k.cyl('main', 'grey', .4, .2, 0, .1, 0, 'y', 12, .02)
    k.tube('main', 'grey', [(0, 4.6, 0), (0, 4.75, .8), (0, 4.75, 3.2)], .07)
    k.box('main', 'dgrey', 1.0, .34, .24, 0, 4.75, 3.0, yaw=math.pi / 2, bev=.04)
    for i, c in enumerate((c1, c2, c3)):
        z = 3.0; x = 0; y = 4.75; ox = (i - 1) * .32
        k.cyl('main', c, .24, .04, -.02, y, z - ox, (1, 0, 0), 14, 0)
        k.cyl('main', 'dgrey', .3, .16, -.09, y + .02, z - ox, (1, 0, 0), 14, 0, cap=False)
    k.box('main', 'dgrey', .3, .62, .2, -.16, 2.6, 0, bev=.03)
    k.box('main', 'lampOff', .22, .22, .02, -.27, 2.76, 0, yaw=math.pi / 2, bev=0); k.box('main', 'lampR' if c1 == 'lampG' else 'lampG', .22, .22, .02, -.27, 2.48, 0, yaw=math.pi / 2, bev=0)
    return dict(circ=.3)

@prop('ped_bridge')
def _(k):
    """歩道橋(車道をx方向にまたぐ): 主桁・床版・高欄(縦格子)・両端の踊り場と、歩道に沿って下りる階段(段・側桁・手すり)・柱"""
    y = 4.9; L = 25.6; X = L / 2
    k.box('main', 'ltblue', L, .55, 2.4, 0, y, 0, bev=.04); k.box('main', 'conc', L, .08, 2.1, 0, y + .3, 0, bev=0)
    for sz in (-1, 1):
        k.box('main', 'ltblue', L, .08, .1, 0, y + 1.3, sz * 1.15, bev=.02)
        for i in range(int(L / .5)): k.box('main', 'ltblue', .04, 1.0, .04, -X + .25 + i * .5, y + .8, sz * 1.15, bev=0)
    k.box('main', 'white', 5, .5, .04, 0, y + .05, -1.22, bev=0); k.box('main', 'white', 5, .5, .04, 0, y + .05, 1.22, bev=0)  # 橋名板
    for sx in (-1, 1):
        x = sx * X
        k.box('main', 'ltblue', 2.6, .5, 2.6, x, y, .1, bev=.03); k.box('main', 'conc', 2.3, .08, 2.3, x, y + .28, .1, bev=0)
        for zz in (-1, 1): k.cyl('main', 'ltblue', .45, y, x + .9 * zz, y / 2, -.9, 'y', 12, .02)
        n = 16; z0, z1 = 1.4, 10.4
        for i in range(n):  # 段(踊り場から+z方向へ下りる)
            t = (i + .5) / n; k.box('main', 'conc', 2.0, .16, (z1 - z0) / n + .02, x, y - t * y + .08, z0 + t * (z1 - z0), bev=.01)
        for xx in (-1.05, 1.05):
            k.seg('main', 'ltblue', .1, .45, z0, y - .15, z1, .05, x + xx)
            k.seg('main', 'ltblue', .06, .06, z0, y + .95, z1, 1.0, x + xx)
            for i in range(1, 6): t = i / 6; k.box('main', 'ltblue', .04, .9, .04, x + xx, y * (1 - t) + .45, z0 + t * (z1 - z0), bev=0)
        k.cyl('main', 'ltblue', .4, y * .55, x, y * .27, 4.6, 'y', 10, .02)
    return dict(circles=[[-X - .9, -.9, .35, y], [-X + .9, -.9, .35, y], [X - .9, -.9, .35, y], [X + .9, -.9, .35, y]], boxes=[[-X, 5.9, 2.3, 9.2, 2.6], [X, 5.9, 2.3, 9.2, 2.6]])

@prop('pole_jp')
def _(k): return pole_jp(k, False)
@prop('pole_jp_t')
def _(k): return pole_jp(k, True)
def pole_jp(k, trans):
    """電柱: 先細りのコンクリート柱・腕金・碍子・足場ボルト・変圧器"""
    k.cyl('main', 'conc', .34, 11, 0, 5.5, 0, 'y', 12, .02, d2=.24)
    for y, w in ((10.4, 2.0), (9.5, 1.6)):
        k.box('main', 'steel', w, .1, .1, 0, y, 0, bev=.01)
        for x in (-w / 2 + .1, -.3, .3, w / 2 - .1): k.cyl('main', 'white', .1, .16, x, y + .12, 0, 'y', 8, .01)
    for i in range(10): k.cyl('main', 'steel', .03, .3, .12 * (1 if i % 2 else -1), 2.2 + i * .5, 0, 'x', 5, 0)
    if trans:
        k.cyl('main', 'grey', .62, 1.1, .45, 8.2, 0, 'y', 14, .03); k.cyl('main', 'grey', .7, .08, .45, 8.78, 0, 'y', 14, 0)
        k.box('main', 'steel', .7, .08, .2, .3, 7.6, 0, bev=0)
    return dict(circ=.3, wires=[[-.9, 10.5, 0], [.9, 10.5, 0], [0, 9.6, 0], [.7, 9.6, 0]])

@prop('vend_r')
def _(k): return vend(k, 'red')
@prop('vend_b')
def _(k): return vend(k, 'blue')
@prop('vend_w')
def _(k): return vend(k, 'white')
def vend(k, col):
    """自動販売機: 本体・商品見本の窓(ボトルの列)・ボタン・コイン口・取り出し口"""
    k.box('main', col, 1.0, 1.8, .75, 0, .9, 0, bev=.04)
    k.box('main', 'glassL', .86, .7, .03, 0, 1.35, .38, bev=0)
    import random; rnd = random.Random(hash(col) & 999)
    for r in range(3):
        for i in range(6):
            k.cyl('main', rnd.choice(['fruitR', 'blue', 'fruitO', 'fruitG', 'white', 'woodL']), .07, .16, -.35 + i * .14, 1.1 + r * .22, .36, 'y', 8, 0)
            k.box('main', 'lampG', .04, .03, .02, -.35 + i * .14, 1.0 + r * .22, .39, bev=0)
    k.box('main', 'black', .7, .18, .05, 0, .25, .38, bev=.01); k.box('main', 'dgrey', .14, .3, .04, .3, .75, .39, bev=.01)
    k.box('main', 'lampW', .86, .04, .02, 0, 1.73, .39, bev=0)
    return dict(box=[1.05, .8, 1.8])

@prop('guardrail')
def _(k):
    """ガードレール4m分: 波形のビーム(断面形を押し出し)と支柱"""
    prof = [(-.0, .62), (.06, .66), (.06, .74), (0, .78), (.06, .82), (.06, .9), (0, .94), (-.04, .94), (-.04, .62)]
    k.prism('main', 'white', [(z, y) for (z, y) in prof], -1.55, 1.55, 'x', .01, 1)
    for x in (-1.2, 1.2): k.cyl('main', 'white', .12, .95, x, .47, -.06, 'y', 8, .01)
    return dict(box=[3.1, .3, 1])

@prop('lamp_jp')
def _(k):
    k.cyl('main', 'grey', .2, 7.6, 0, 3.8, 0, 'y', 10, .02, d2=.14)
    k.tube('main', 'grey', [(0, 7.4, 0), (0, 7.9, .4), (0, 7.95, 1.6)], .06)
    k.box('main', 'grey', .4, .14, .8, 0, 7.9, 1.8, bev=.04); k.box('main', 'lampW', .3, .02, .6, 0, 7.82, 1.8, bev=0)
    return dict(circ=.25)

@prop('lamp_eu')
def _(k):
    """洋風の街灯: 鋳鉄の柱(回転体)・腕・ガラスの灯籠・笠"""
    k.lathe('main', 'iron', [(.0, 0), (.32, 0), (.3, .2), (.16, .3), (.14, .9), (.18, 1.0), (.1, 1.1), (.08, 3.4), (.12, 3.5), (.06, 3.6), (0, 3.6)], 0, 0, 0, 14)
    k.lathe('main', 'iron', [(0, 3.6), (.2, 3.6), (.26, 3.65), (.2, 3.7), (0, 3.7)], 0, 0, 0, 8)
    k.box('main', 'lampY', .3, .46, .3, 0, 3.95, 0, bev=.02)
    for x in (-.16, .16):
        for z in (-.16, .16): k.box('main', 'iron', .03, .5, .03, x, 3.95, z, bev=0)
    k.cyl('main', 'iron', .02, .55, 0, 4.42, 0, 'y', 4, 0, d2=.6); k.cyl('main', 'iron', .08, .12, 0, 4.72, 0, 'y', 8, 0)
    return dict(circ=.3)

@prop('bench')
def _(k):
    """公園のベンチ(資料: 鋳鉄の両脇の脚(ひじ掛け付き)に木の板を渡す。長さ約1.8m・座面の高さ約45cm・背もたれ付き)。
    長さ1.4・座面.35(1unit=1.3m)。部品: 鋳鉄の脚(前脚・後脚・ひじ掛け・座の受け)・座板5枚・背板3枚・中央の補強・ボルト"""
    L = 1.4
    for i in range(5): k.box('main', 'wood', L, .035, .07, 0, .35, -.16 + i * .08, bev=.008)           # 座板
    for i in range(3): k.box('main', 'wood', L, .07, .03, 0, .48 + i * .1, -.25 - i * .018, pitch=.18, bev=.008)   # 背板
    for x in (-L / 2 + .06, L / 2 - .06):
        k.tube('main', 'iron', [(x, 0, .2), (x, .2, .17), (x, .33, .15)], .03)                            # 前脚
        k.tube('main', 'iron', [(x, 0, -.24), (x, .33, -.2), (x, .55, -.27), (x, .72, -.31)], .03)        # 後脚と背の支え
        k.tube('main', 'iron', [(x, .33, .17), (x, .33, -.2)], .025)                                      # 座の受け
        k.tube('main', 'iron', [(x, .52, -.24), (x, .54, .05), (x, .5, .18), (x, .34, .18)], .025)        # ひじ掛け
        k.box('main', 'iron', .06, .03, .1, x, 0.015, .2, bev=.005); k.box('main', 'iron', .06, .03, .1, x, .015, -.24, bev=.005)   # 足
    k.tube('main', 'iron', [(0, .33, .14), (0, .2, 0), (0, .33, -.18)], .02)                              # 中央の補強
    k.cyl('main', 'iron', .05, .3, 0, .1, 0, 'y', 6, 0)
    return dict(box=[1.45, .55, .8])

@prop('bin')
def _(k):
    k.lathe('main', 'green', [(0, 0), (.24, 0), (.27, .05), (.27, .85), (.29, .9), (0, .9)], 0, 0, 0, 14); k.cyl('main', 'iron', .2, .02, 0, .91, 0, 'y', 10, 0)
    return dict(circ=.35)

@prop('phone_booth')
def _(k):
    """赤い電話ボックス: 窓枠の格子・王冠形の屋根・看板"""
    k.box('main', 'red', 1, .14, 1, 0, .07, 0, bev=.02)
    for x in (-.45, .45):
        for z in (-.45, .45): k.box('main', 'red', .1, 2.2, .1, x, 1.2, z, bev=.02)
    for f in range(4):
        a = f * math.pi / 2; c, s_ = math.cos(a), math.sin(a)
        k.box('main', 'glassL', .8 if f % 2 == 0 else .03, 1.6, .03 if f % 2 == 0 else .8, s_ * .46, 1.25, c * .46, bev=0)
        for i in range(4): k.box('main', 'red', .82 if f % 2 == 0 else .05, .04, .05 if f % 2 == 0 else .82, s_ * .47, .55 + i * .45, c * .47, bev=0)
        k.box('main', 'cream', .6 if f % 2 == 0 else .03, .14, .03 if f % 2 == 0 else .6, s_ * .5, 2.2, c * .5, bev=0)
    k.box('main', 'red', 1.08, .22, 1.08, 0, 2.38, 0, bev=.04); k.lathe('main', 'red', [(.56, 2.49), (.4, 2.62), (0, 2.66)], 0, 0, 0, 4)
    return dict(box=[1.05, 1.05, 2.7])

@prop('bus_burnt')
def _(k):
    k.box('main', 'burnt', 2.6, 2.5, 10.6, 0, 1.75, 0, bev=.1)
    for z in range(-4, 5):
        for sx in (-1, 1): k.box('main', 'black', .05, .9, .9, sx * 1.31, 2.3, z * 1.1, bev=0)
    k.box('main', 'black', 2.3, .9, .05, 0, 2.3, 5.31, bev=0)
    for z in (-3.6, 3.4):
        for sx in (-1, 1): k.wheel('main', sx * 1.05, .5, z, 1.0, .35, 'rust')
    k.box('main', 'rust', 2.4, .3, 10, 0, 3.05, 0, bev=.05)
    return dict(box=[2.7, 10.8, 3.2])

@prop('ad_column')
def _(k):
    """広告塔(モリス柱): 台座・ポスターを貼った円柱(色違いの帯)・コーニス・ドーム屋根と頂華"""
    k.lathe('main', 'green', [(0, 0), (.75, 0), (.75, .25), (.62, .4), (0, .4)], 0, 0, 0, 16)
    k.cyl('main', 'cream', 1.1, 2.6, 0, 1.7, 0, 'y', 16, 0)
    import random; rnd = random.Random(4)
    for i in range(8):
        a = i * 2 * math.pi / 8 + .2; c, s_ = math.cos(a), math.sin(a)
        k.box('main', rnd.choice(['red', 'yellow', 'blue', 'white', 'fruitO', 'ltblue', 'green', 'black']), .36, .9 + rnd.random() * .5, .02, c * .555, 1.5 + rnd.random() * .5, s_ * .555, yaw=math.atan2(c, s_), bev=0)
    k.lathe('main', 'green', [(0, 3.0), (.62, 3.0), (.72, 3.12), (.68, 3.2), (.5, 3.3), (.3, 3.6), (.08, 3.8), (0, 3.85)], 0, 0, 0, 16)
    k.blob('main', 'green', .1, 0, 3.92, 0, sub=1, rough=0)
    return dict(circ=.7)

# ---- 欧州の旧市街 ----
@prop('stall_r')
def _(k): return stall(k, 'canvasR')
@prop('stall_g')
def _(k): return stall(k, 'canvasG')
def stall(k, ccol):
    """市場の屋台: 木の柱・台・果物の木箱・縞の日よけ(布の帯を交互に)"""
    for x in (-1.3, 1.3):
        for z in (-.8, .8): k.box('main', 'woodD', .1, 2.3 + (.3 if z < 0 else 0), .1, x, (2.3 + (.3 if z < 0 else 0)) / 2, z, bev=.01)
    k.box('main', 'wood', 2.8, .08, 1.5, 0, .9, 0, bev=.02); k.box('main', 'woodD', 2.7, .75, .05, 0, .5, .74, bev=.01)
    import random; rnd = random.Random(len(ccol))
    for i in range(4):
        x = -1 + i * .66; k.box('main', 'woodL', .55, .22, .5, x, 1.05, -.1, bev=.01)
        for j in range(5): k.blob('main', rnd.choice(['fruitR', 'fruitO', 'fruitG']), .07, x - .18 + (j % 3) * .18, 1.2, -.18 + (j // 3) * .16, sub=1, rough=.05)
    n = 8
    for i in range(n):  # 日よけ: 前に下がる斜めの布(帯ごとに色を交互に)
        x = -1.5 + (i + .5) * 3 / n
        k.seg('main', ccol if i % 2 else 'canvasW', 3 / n + .01, .03, -1.0, 2.62, 1.05, 2.15, x, bev=0)
        k.box('main', ccol if i % 2 else 'canvasW', 3 / n + .01, .25, .02, x, 2.0, 1.06, bev=0)
    return dict(box=[3, 2.2, 2.6])

@prop('cart')
def _(k):
    """荷車: 板張りの荷台と側板・スポーク付きの大きな車輪・2本の轅(ながえ)・積み荷"""
    for i in range(6): k.box('main', 'wood', 1.3, .06, .3, 0, .82, -1 + i * .32, bev=.01)
    for sx in (-1, 1):
        for i in range(3): k.box('main', 'woodL', .05, .1, 2.0, sx * .66, .95 + i * .14, -.2, bev=.01)
        for z in (-1.1, -.45, .2, .75): k.box('main', 'woodD', .07, .55, .07, sx * .7, 1.05, z, bev=.01)   # 側板の柱
        k.box('main', 'woodD', .14, .3, .34, sx * .62, .68, -.2, bev=.02)                                # 車軸受け
        k.torus('main', 'woodD', .5, .04, sx * .76, .55, -.2, 'x', 18, 5); k.cyl('main', 'woodD', .16, .2, sx * .76, .55, -.2, 'x', 10, .01)
        k.spokes('main', 'woodD', .48, sx * .76, .55, -.2, 10, .02)
        k.tube('main', 'woodL', [(sx * .5, .8, .7), (sx * .45, .2, 2.4)], .04)
    k.cyl('main', 'iron', .05, 1.6, 0, .55, -.2, 'x', 6, 0)
    k.lathe('main', 'woodL', [(0, 0), (.24, 0), (.29, .3), (.24, .6), (0, .6)], -.25, .85, -.6, 12); k.blob('main', 'straw', .32, .3, 1.0, -.1, sy=.7, sub=2, rough=.15)
    return dict(box=[1.7, 3.4, 1.5])

@prop('barrels')
def _(k):
    for x, z in ((0, 0), (.62, .1), (.3, .55)):
        k.lathe('main', 'wood', [(0, 0), (.26, 0), (.31, .25), (.32, .45), (.31, .65), (.26, .9), (0, .9)], x, 0, z, 16)
        for y, r in ((.12, .285), (.45, .325), (.78, .285)): k.torus('main', 'iron', r, .015, x, y, z, 'y', 18, 4)
    return dict(circ=.85)

@prop('cafe_r')
def _(k): return cafe(k, 'canvasR')
@prop('cafe_g')
def _(k): return cafe(k, 'canvasG')
def cafe(k, ccol):
    """カフェの席: 丸テーブル・ビストロチェア3脚・八角形のパラソル(骨付き)"""
    k.lathe('main', 'iron', [(0, 0), (.25, 0), (.06, .05), (.04, .7), (.4, .72), (.4, .75), (0, .75)], 0, 0, 0, 14)
    for i in range(3):
        a = i * 2.1; x, z = math.cos(a) * .7, math.sin(a) * .7
        k.cyl('main', 'woodL', .38, .04, x, .46, z, 'y', 12, 0)
        for j in range(4):
            b = j * math.pi / 2 + .5; k.cyl('main', 'iron', .025, .46, x + math.cos(b) * .14, .23, z + math.sin(b) * .14, 'y', 4, 0)
        k.tube('main', 'iron', [(x + math.cos(a) * .16, .46, z + math.sin(a) * .16), (x + math.cos(a) * .2, .85, z + math.sin(a) * .2)], .015)
    k.cyl('main', 'woodL', .05, 2.4, 0, 1.4, 0, 'y', 6, 0)
    segs = 8; rings = [(0, 2.6), (.6, 2.45), (1.3, 2.2), (1.5, 2.12)]
    k.lathe('main', ccol, [(r, h) for r, h in rings], 0, 0, 0, segs, cap=False)
    for i in range(segs):
        a = i * 2 * math.pi / segs; k.tube('main', 'woodD', [(0, 2.6, 0), (math.cos(a) * 1.5, 2.12, math.sin(a) * 1.5)], .015)
    return dict(circ=.95)

@prop('quay_rail')
def _(k):
    """川岸の護岸の上端(4m分): 笠石と、鋳鉄の手すり(親柱・縦格子・槍形の飾り・上下の横桟)"""
    k.box('main', 'stoneD', 4.02, .3, 1.0, 0, .05, 0, bev=.04)
    k.box('main', 'stone', 4.02, .5, .9, 0, -.35, .05, bev=.02)
    k.box('main', 'iron', .12, 1.1, .12, -1.94, .75, 0, bev=.01); k.blob('main', 'iron', .08, -1.94, 1.36, 0, sub=1, rough=0)
    for y in (.32, .98): k.box('main', 'iron', 4.0, .05, .04, 0, y, 0, bev=0)
    for i in range(20):
        x = -1.8 + i * .2; k.cyl('main', 'iron', .025, .78, x, .62, 0, 'y', 4, 0); k.cyl('main', 'iron', .05, .1, x, 1.06, 0, 'y', 4, 0, d2=0)
    return dict()

@prop('boat')
def _(k):
    """手漕ぎボート: 断面を並べた木の船体(舷側の板・竜骨)・腰掛け板・オール"""
    secs = []
    for i in range(9):
        t = i / 8; z = -2.0 + 4.0 * t; w = .78 * math.sin(math.pi * (.08 + .84 * t)) ** .7; sh = .1 + .25 * (2 * t - 1) ** 2
        secs.append([(-w, .55 + sh, z), (-w * .85, .22, z), (-w * .35, .02, z), (w * .35, .02, z), (w * .85, .22, z), (w, .55 + sh, z)])
    rows = [[secs[i][j] for i in range(9)] for j in range(6)]
    for j in range(5): k.grid('main', 'woodL' if j in (1, 3) else 'wood', [rows[j], rows[j + 1]])
    for sx in (-1, 1): k.tube('main', 'woodD', [secs[i][0 if sx < 0 else 5] for i in range(9)], .03)
    k.tube('main', 'woodD', [(0, .0, -2.05), (0, .0, 2.05)], .04)
    for z in (-.9, .2, 1.2): k.box('main', 'woodL', 1.3 * math.sin(math.pi * (.08 + .84 * (z + 2) / 4)) ** .7, .05, .26, 0, .42, z, bev=.01)
    for sx in (-1, 1): k.tube('main', 'woodL', [(sx * .2, .5, .3), (sx * 1.0, .45, -1.2)], .025); k.box('main', 'woodL', .12, .02, .4, sx * 1.02, .45, -1.3, yaw=sx * .5, bev=0)
    return dict(ground=-.3)

@prop('fountain_eu')
def _(k):
    """噴水: 八角の水盤(回転体)・水面・柱・上段の水盤・頂部の飾り"""
    k.lathe('main', 'stone', [(0, 0), (3.6, 0), (3.6, .55), (3.75, .62), (3.75, .7), (3.3, .7), (3.3, .2), (0, .2)], 0, 0, 0, 8)
    k.cyl('main', 'water', 6.5, .04, 0, .5, 0, 'y', 8, 0)
    k.lathe('main', 'stone', [(0, .2), (.7, .2), (.55, .5), (.4, 1.6), (.5, 1.8), (1.4, 2.0), (1.5, 2.25), (1.36, 2.3), (1.2, 2.12), (.3, 2.12), (.25, 2.9), (.35, 3.1), (.15, 3.4), (0, 3.5)], 0, 0, 0, 16)
    k.cyl('main', 'water', 2.56, .04, 0, 2.22, 0, 'y', 16, 0)
    return dict(circ=3.7)

@prop('stone_bridge')
def _(k):
    """アルデンヌの村の石のアーチ橋(資料: ウール村の橋は頁岩質砂岩の野面積みで3連アーチ。ロシュフォールの石橋など)。
    幅12・長さ24.2、路面 y=0、橋脚は川底(y=-10)まで届く。
    部品: 3連の半円アーチを抜いた側面形の本体・アーチの輪石(両面)・橋脚の上流/下流の水切り・帯石・欄干と笠石・路面"""
    r, yc, yb, L = 3.2, -4.6, -10.0, 12.1
    prof = [(-L, 0), (L, 0), (L, yb)]
    for zc in (8.1, 0.0, -8.1):                               # 底から3つのアーチを切り欠いた側面形(z, y)
        prof += [(zc + r, yb), (zc + r, yc)]
        prof += [(zc + r * math.cos(a), yc + r * math.sin(a)) for a in [i * math.pi / 14 for i in range(1, 14)]]
        prof += [(zc - r, yc), (zc - r, yb)]
    prof += [(-L, yb)]
    k.prism('main', 'shaleS', prof, -6.0, 6.0, 'x', bev=0)
    for zc in (8.1, 0.0, -8.1):                               # 輪石: アーチのまわりに放射状に並ぶ石(両面に少し出す)
        n = 13
        for i in range(n):
            a0, a1 = i * math.pi / n, (i + 1) * math.pi / n
            q = [(zc + rr * math.cos(a), yc + rr * math.sin(a)) for rr, a in ((r, a0), (r + .75, a0 + .01), (r + .75, a1 - .01), (r, a1))]
            for x0 in (-6.12, 6.0): k.prism('main', 'shaleD' if i % 2 else 'shaleS', q, x0, x0 + .12, 'x', bev=0)
    for zp in (4.05, -4.05):                                  # 橋脚の水切り(上流と下流の両側、三角柱+笠)
        for sx in (-1, 1):
            tri = [(sx * 6.0, zp - .85), (sx * 7.5, zp), (sx * 6.0, zp + .85)]
            k.prism('main', 'shaleS', tri, yb, yc + .4, 'y', bev=0)
            k.prism('main', 'shaleD', [(sx * 6.0, zp - .85), (sx * 7.5, zp), (sx * 6.0, zp + .85)], yc + .4, yc + .6, 'y', bev=0)
    for sx in (-1, 1):
        k.box('main', 'shaleD', .2, .28, 24.2, sx * 6.08, -.3, 0, bev=.02)                         # 帯石
        k.box('main', 'shaleS', .6, 1.0, 24.2, sx * 5.7, .5, 0, bev=.03)                           # 欄干
        k.box('main', 'shaleD', .8, .16, 24.4, sx * 5.7, 1.08, 0, bev=.03)                         # 笠石
        for z in (-12.0, 12.0): k.box('main', 'shaleD', .9, 1.4, .9, sx * 5.7, .7, z, bev=.04)     # 親柱
    k.box('main', 'road', 10.8, .05, 24.2, 0, .01, 0, bev=0)                                       # 路面(砂利と轍)
    return dict(boxes=[[sx * 5.7, 0, .6, 24.2, 1.2] for sx in (-1, 1)])
s_cut = []

# ---- 木 ----
@prop('tree_broad')
def _(k):
    """広葉樹: 枝分かれした幹(管)と、凹凸のある葉の塊を枝先に"""
    k.tube('main', 'bark', [(0, 0, 0), (.05, 1.6, 0), (.1, 2.6, .1)], .2)
    import random; rnd = random.Random(7); tips = []
    for i in range(5):
        a = i * 2 * math.pi / 5 + rnd.random() * .5; L = 1.2 + rnd.random() * .6
        e = (math.cos(a) * L, 3.2 + rnd.random() * 1.2, math.sin(a) * L); k.tube('main', 'bark', [(.1, 2.4, .1), (e[0] * .5, 2.9, e[2] * .5), e], .07); tips.append(e)
    for i, e in enumerate(tips + [(0, 4.6, 0), (.3, 4.2, -.4)]):
        k.blob('main', ['leaf1', 'leaf2', 'leaf3'][i % 3], 1.15 + rnd.random() * .4, e[0], e[1] + .2, e[2], sy=.85, sub=2, rough=.3, seed=i)
    return dict(circ=.45)

@prop('tree_conifer')
def _(k):
    k.cyl('main', 'bark', .32, 2, 0, 1, 0, 'y', 8, 0, d2=.2)
    for i in range(6):
        r = 1.9 - i * .28; y = 1.4 + i * .95
        k.lathe('main', 'pine', [(0, y + 1.6), (r * .3, y + 1.2), (r, y + .05), (r * .85, y), (0, y)], 0, 0, 0, 10)
    return dict(circ=.4)

@prop('palm')
def _(k):
    """ヤシ: 節のある曲がった幹(輪を重ねる)・葉軸と小葉からなる垂れた葉・実"""
    pts = [(0, 0, 0)];
    for i in range(1, 13): t = i / 12; pts.append((.9 * t * t, 6.2 * t, .2 * t))
    for i in range(12):
        a, b = pts[i], pts[i + 1]; r = .22 - .07 * i / 12
        k.tube('main', 'barkP', [a, b], r); k.torus('main', 'bark', r + .02, .03, b[0], b[1], b[2], 'y', 12, 4)
    top = pts[-1]
    for i in range(11):
        a = i * 2 * math.pi / 11; L = 2.8 + (i % 3) * .3; rib = []
        for j in range(8):
            t = j / 7; rib.append((top[0] + math.cos(a) * L * t, top[1] + .7 * t - 1.9 * t * t, top[2] + math.sin(a) * L * t))
        k.tube('main', 'palm', rib, .03)
        for j in range(1, 7):
            p = rib[j]; t = j / 7; w = .55 * math.sin(t * math.pi) + .1
            for sd in (-1, 1):
                nx, nz = -math.sin(a) * sd, math.cos(a) * sd
                k.tube('main', ['palm', 'leaf1'][j % 2], [p, (p[0] + nx * w, p[1] - .25, p[2] + nz * w)], .045)
    for i in range(4): k.blob('main', 'woodD', .14, top[0] + math.cos(i * 1.6) * .17, top[1] - .2, top[2] + math.sin(i * 1.6) * .17, sub=1, rough=.05)
    return dict(circ=.4)

@prop('bush')
def _(k):
    for i in range(4): k.blob('main', ['leaf1', 'leaf2', 'leaf3'][i % 3], .55, math.cos(i * 1.7) * .4, .45, math.sin(i * 1.7) * .4, sy=.8, sub=2, rough=.3, seed=i + 9)
    return dict()

# ---- 日本 ----
@prop('torii')
def _(k):
    """鳥居(明神鳥居): 柱・笠木(反りのある上の横木)・島木・貫・額束・根巻"""
    for x in (-2.3, 2.3):
        k.cyl('main', 'vermil', .5, 5, x, 2.5, 0, 'y', 16, .01, d2=.42); k.cyl('main', 'black', .6, .5, x, .25, 0, 'y', 16, .02)
    n = 12; W = 7.6
    for i in range(n):  # 反りのある笠木を短い箱の連なりで
        t0, t1 = i / n, (i + 1) / n; x0, x1 = -W / 2 + W * t0, -W / 2 + W * t1
        y0 = 5.45 + .5 * (2 * t0 - 1) ** 4; y1 = 5.45 + .5 * (2 * t1 - 1) ** 4
        k.box('main', 'black', x1 - x0 + .02, .32, .7, (x0 + x1) / 2, (y0 + y1) / 2 + .1, 0, roll=-math.atan2(y1 - y0, x1 - x0), bev=.01)
        k.box('main', 'vermil', x1 - x0 + .02, .3, .55, (x0 + x1) / 2, (y0 + y1) / 2 - .2, 0, roll=-math.atan2(y1 - y0, x1 - x0), bev=.01)
    k.box('main', 'vermil', 6.0, .3, .3, 0, 4.2, 0, bev=.02); k.box('main', 'vermil', .3, .9, .3, 0, 4.75, 0, bev=.02)
    k.box('main', 'black', .5, .6, .05, 0, 4.75, .17, bev=0)
    return dict(circles=[[-2.3, 0, .35, 6], [2.3, 0, .35, 6]])

@prop('toro')
def _(k):
    """石灯籠: 基礎・竿・中台・火袋(窓)・笠(反り)・宝珠"""
    k.lathe('main', 'stone', [(0, 0), (.55, 0), (.55, .2), (.35, .3), (.2, .35), (.18, 1.2), (.4, 1.3), (.45, 1.45), (0, 1.45)], 0, 0, 0, 6)
    k.box('main', 'stone', .5, .55, .5, 0, 1.72, 0, bev=.03); k.box('main', 'lampOff', .3, .3, .52, 0, 1.75, 0, bev=0); k.box('main', 'lampOff', .52, .3, .3, 0, 1.75, 0, bev=0)
    k.lathe('main', 'stone', [(0, 2.0), (.8, 2.0), (.85, 2.08), (.4, 2.4), (.12, 2.5), (0, 2.5)], 0, 0, 0, 6); k.blob('main', 'stone', .14, 0, 2.62, 0, sub=1, rough=.02)
    return dict(circ=.55)

# ---- 砂漠 ----
@prop('truck_old')
def _(k):
    """古いボンネットトラック: 丸みのあるキャブ・ボンネット・フェンダー・荷台の側板・二重タイヤ(錆と色あせ)"""
    k.prism('main', 'rustL', [(.9, .7), (2.6, .7), (2.7, 1.25), (2.3, 1.45), (.95, 1.5)], -.95, .95, 'x', .12, 2)
    k.prism('main', 'rustL', [(-.3, .7), (.95, .7), (.95, 2.5), (.6, 2.75), (-.3, 2.75)], -1.15, 1.15, 'x', .1, 2)
    k.box('main', 'glass', 2.0, .7, .05, 0, 2.15, .97, pitch=.1, bev=0)
    for sx in (-1, 1):
        k.box('main', 'glass', .05, .6, .7, sx * 1.16, 2.1, .4, bev=0); k.cyl('main', 'chrome', .26, .08, sx * .7, 1.25, 2.72, 'z', 12, 0)
        k.box('main', 'rust', .3, .1, 1.3, sx * 1.0, 1.2, 1.9, bev=.03)
    k.box('main', 'chrome', 2.2, .22, .18, 0, .65, 2.75, bev=.05); k.box('main', 'dgrey', 1.1, .5, .05, 0, 1.0, 2.71, bev=0)
    k.box('main', 'woodD', 2.4, .18, 4.2, 0, 1.05, -2.6, bev=.03)
    for sx in (-1, 1):
        for i in range(3): k.box('main', 'wood', .07, .22, 4.2, sx * 1.18, 1.25 + i * .26, -2.6, bev=.01)
    for i in range(3): k.box('main', 'wood', 2.4, .22, .07, 0, 1.25 + i * .26, -4.68, bev=.01)
    for sx in (-1, 1):
        for z in (-4.62, -3.3, -1.9, -.55): k.box('main', 'woodD', .09, .9, .09, sx * 1.15, 1.5, z, bev=.01)   # 側板の柱(板を荷台につなぐ)
    for sx in (-1, 1):
        k.wheel('main', sx * .98, .48, 1.85, .96, .32, 'rust'); k.wheel('main', sx * .92, .48, -3.3, .96, .32, 'rust'); k.wheel('main', sx * .6, .48, -3.3, .96, .3, 'rust')
    k.box('main', 'iron', .3, .44, 5.5, 0, .76, -1, bev=.02)                                   # 車台(荷台とキャブを載せる)
    return dict(box=[2.5, 7.6, 3])

@prop('pumpjack')
def _(k):
    """油井ポンプ: 台座・サムソンポスト(A字)・天秤(beam)・馬頭・クランクとカウンターウェイト(crank)・減速機・モーター"""
    k.box('main', 'grey', 2.2, .35, 9, 0, .18, 0, bev=.03)
    for sx in (-1, 1):
        k.seg('main', 'yellow', .25, .25, -1.2, .35, 0, 5.2, sx * .55); k.seg('main', 'yellow', .25, .25, 1.4, .35, 0, 5.2, sx * .55)
    k.box('main', 'yellow', 1.4, .3, .4, 0, 5.2, 0, bev=.03)
    k.box('main', 'grey', 1.2, 1.2, 1.6, 0, .95, -3.2, bev=.05); k.cyl('main', 'blue', .8, 1.2, .9, .9, -4.3, 'x', 14, .03)
    k.cyl('main', 'steel', .3, 1.4, 0, .9, 4.0, 'y', 10, .02); k.box('main', 'steel', .6, .4, .6, 0, .2, 4.0, bev=.02)
    # 天秤(支点がこの小物の原点からの (0,5.5,0))
    k.box('beam', 'red', .5, .6, 7.2, 0, 5.6, .2, bev=.04)
    k.prism('beam', 'red', [(3.5, 4.5), (4.1, 4.8), (4.35, 5.6), (4.1, 6.35), (3.5, 6.1)], -.32, .32, 'x', .04, 2)
    k.cyl('beam', 'iron', .05, 3.6, 0, 3.3, 4.25, 'y', 6, 0)
    for sx in (-1, 1): k.seg('beam', 'yellow', .12, .14, -3.2, 5.5, -3.2, 1.3, sx * .45)
    # クランクとカウンターウェイト(回転中心 (0,1.3,-3.2))
    for sx in (-1, 1):
        k.box('crank', 'red', .2, .3, 2.4, sx * .75, 1.3, -3.2, bev=.03)
        k.prism('crank', 'grey', [(-4.4, .9), (-3.4, .5), (-3.0, .9), (-3.0, 1.7), (-3.4, 2.1), (-4.4, 1.7)], sx * .7 - .12, sx * .7 + .12, 'x', .03, 1)
    return dict(box=[2.4, 9.4, 6.5], pivots={'beam': [0, 5.5, 0], 'crank': [0, 1.3, -3.2]})

@prop('tent_bedouin')
def _(k):
    """ベドウィンのテント: 柱で持ち上げてたわませた毛織りの屋根(縞)・張り綱・杭・敷物"""
    nx, nz = 9, 13; W, D = 6.4, 9.6; rows = []
    poles = [(0, -3, 2.3), (0, 0, 2.5), (0, 3, 2.3), (-2.4, -3, 1.6), (2.4, -3, 1.6), (-2.4, 3, 1.6), (2.4, 3, 1.6)]
    for j in range(nz):
        row = []
        for i in range(nx):
            x = -W / 2 + W * i / (nx - 1); z = -D / 2 + D * j / (nz - 1)
            h = max(1.0 + .2 * math.cos(z), max(ph - .35 * math.hypot(x - px, z - pz) ** 1.2 for px, pz, ph in poles))
            if i in (0, nx - 1) or j in (0, nz - 1): h = min(h, 1.05)
            row.append((x, h, z))
        rows.append(row)
    for j in range(nz - 1):  # 帯ごとに色を変える(縞)
        k.grid('main', 'tentB' if j % 3 else 'tentS', [rows[j], rows[j + 1]])
    for px, pz, ph in poles: k.cyl('main', 'woodD', .1, ph, px, ph / 2, pz, 'y', 6, 0)
    for x, z in ((-3.2, -4.8), (3.2, -4.8), (-3.2, 4.8), (3.2, 4.8), (-3.2, 0), (3.2, 0)):
        tx, tz = x * 1.5, z * 1.15; k.tube('main', 'woodL', [(x, 1.0, z), (tx, 0, tz)], .012); k.cyl('main', 'woodD', .05, .3, tx, .1, tz, 'y', 4, 0)
    k.box('main', 'canvasR', 4.2, .02, 6.5, 0, .02, 0, bev=0)
    return dict(box=[6.6, 9.8, 2.6])

@prop('tel_pole')
def _(k):
    """木の電柱(電信柱)(資料: 腕木を通しボルトで留め、斜めの支え(方杖)で補強。腕木のピンにねじ込んだがいし。昇柱用の足場ボルト)。
    部品: 先細りの柱・頂部の笠・腕木2段・方杖・ピンとがいし8個・足場ボルト・根元の黒い防腐処理"""
    k.cyl('main', 'barkP', .3, 8.4, 0, 4.2, 0, 'y', 12, .02, d2=.22)
    k.cyl('main', 'black', .31, .9, 0, .45, 0, 'y', 12, 0)                                              # 根元の防腐処理
    k.lathe('main', 'iron', [(0, 8.38), (.14, 8.38), (.1, 8.5), (0, 8.52)], 0, 0, 0, 8)                  # 頂部の笠
    for y, Lw in ((7.8, 2.2), (7.1, 1.7)):
        k.box('main', 'woodD', Lw, .14, .12, 0, y, .17, bev=.02)                                        # 腕木
        k.cyl('main', 'iron', .05, .4, 0, y, .05, 'z', 6, 0)                                            # 通しボルト
        for sx in (-1, 1): k.tube('main', 'iron', [(sx * .1, y - .55, .14), (sx * Lw * .3, y - .06, .17)], .018)   # 方杖
        xs = (-.95, -.4, .4, .95) if Lw > 2 else (-.72, -.3, .3, .72)
        for x in xs:
            k.cyl('main', 'iron', .03, .16, x, y + .14, .17, 'y', 5, 0)                                  # ピン
            k.lathe('main', 'glassL', [(0, y + .2), (.07, y + .2), (.06, y + .28), (.045, y + .33), (0, y + .35)], x, 0, .17, 10)   # がいし
    for i in range(9): k.cyl('main', 'iron', .03, .32, (-.13 if i % 2 else .13), 2.4 + i * .5, 0, 'x', 5, 0)   # 足場ボルト
    return dict(circ=.35, wires=[[-.95, 8.15, .17], [-.4, 8.15, .17], [.4, 8.15, .17], [.95, 8.15, .17]])

# ---- 丘陵 ----
@prop('windmill')
def _(k):
    """風車: 漆喰の塔(回転体)・窓・扉・回廊・ドーム屋根・羽根(sails: 格子の帆を4枚)"""
    k.lathe('main', 'cream', [(0, 0), (2.5, 0), (2.4, 1), (1.7, 10.5), (1.85, 10.6), (0, 10.6)], 0, 0, 0, 20)
    k.lathe('main', 'woodD', [(0, 10.5), (2.1, 10.5), (2.1, 10.9), (1.6, 12.0), (.9, 12.7), (0, 12.9)], 0, 0, 0, 16)
    k.box('main', 'woodD', 1.1, 2.0, .2, 0, 1.0, -2.45, bev=.02)
    for y in (4, 7.5): k.box('main', 'woodD', .6, .8, .2, 0, y, -2.25 + (y - 4) * .15, bev=.01)
    k.torus('main', 'woodD', 2.35, .06, 0, 3.0, 0, 'y', 28, 4)
    for i in range(16): a = i * 2 * math.pi / 16; k.cyl('main', 'woodD', .06, .8, math.cos(a) * 2.35, 2.6, math.sin(a) * 2.35, 'y', 4, 0)
    k.cyl('main', 'woodD', .3, 1.4, 0, 11, -1.9, 'z', 10, 0)
    for i in range(4):  # 羽根(回転中心 (0,11,-2.6))
        a = i * math.pi / 2; c, s_ = math.cos(a), math.sin(a)
        k.tube('sails', 'woodD', [(0, 11, -2.6), (s_ * 7.2, 11 + c * 7.2, -2.6)], .09)
        for j in range(9):
            t = 1.6 + j * .65; px, py = s_ * t, 11 + c * t
            k.tube('sails', 'woodL', [(px, py, -2.62), (px + c * 1.4, py - s_ * 1.4, -2.62)], .03)
        k.tube('sails', 'woodL', [(s_ * 1.6 + c * 1.4, 11 + c * 1.6 - s_ * 1.4, -2.62), (s_ * 7 + c * 1.4, 11 + c * 7 - s_ * 1.4, -2.62)], .03)
        k.grid('sails', 'canvasW', [[(s_ * 1.7 + c * .1, 11 + c * 1.7 - s_ * .1, -2.66), (s_ * 1.7 + c * 1.3, 11 + c * 1.7 - s_ * 1.3, -2.66)], [(s_ * 6.8 + c * .1, 11 + c * 6.8 - s_ * .1, -2.66), (s_ * 6.8 + c * 1.3, 11 + c * 6.8 - s_ * 1.3, -2.66)]])
    return dict(circ=2.6, pivots={'sails': [0, 11, -2.6, 'z']})

@prop('pylon')
def _(k):
    """送電鉄塔: 4本の脚(先細り)・各段の水平材とX形の斜材・腕金・がいし"""
    H = 20; lv = [0, 4, 8, 11.5, 14.5, 17, 20]; half = lambda y: 2.2 - 1.6 * (y / H)
    for sx in (-1, 1):
        for sz in (-1, 1): k.tube('main', 'steel', [(sx * half(0), 0, sz * half(0)), (sx * half(H), H, sz * half(H))], .1)
    for a, b in zip(lv[:-1], lv[1:]):
        ha, hb = half(a), half(b)
        for f in range(4):
            ang = f * math.pi / 2; c, s_ = math.cos(ang), math.sin(ang)
            P = lambda h, t, y: (c * h + -s_ * h * t, y, s_ * h + c * h * t)
            k.tube('main', 'steel', [P(ha, -1, a), P(hb, 1, b)], .045); k.tube('main', 'steel', [P(ha, 1, a), P(hb, -1, b)], .045)
            k.tube('main', 'steel', [P(hb, -1, b), P(hb, 1, b)], .05)
    for y, w in ((14.5, 6.5), (17, 5)):
        for sx in (-1, 1):
            k.tube('main', 'steel', [(sx * half(y), y, 0), (sx * w, y, 0)], .06); k.tube('main', 'steel', [(sx * half(y), y - 1.2, 0), (sx * w, y, 0)], .04)
            k.cyl('main', 'white', .2, 1.2, sx * (w - .2), y - .7, 0, 'y', 8, .01)
    k.lathe('main', 'steel', [(0, H - .1), (.95, H - .1), (0, H + 1.2)], 0, 0, 0, 4)
    return dict(circ=1.9, wires=[[-6.3, 13.6, 0], [6.3, 13.6, 0], [-4.8, 16.1, 0], [4.8, 16.1, 0]])

@prop('sheep')
def _(k):
    """羊(資料: 成羊の体高(き甲)は約60〜80cm)。体高.55(1unit=1.3m)。
    部品: 毛のかたまりの胴・首・顔(鼻先)・耳・4本の脚(ひざと蹄)・短い尾"""
    k.blob('main', 'wool', .42, 0, .62, -.05, sy=.82, sub=2, rough=.16, seed=3)                        # 胴
    k.blob('main', 'wool', .36, 0, .64, .25, sy=.85, sub=2, rough=.18, seed=5)
    k.blob('main', 'wool', .2, 0, .78, .5, sy=1.0, sub=2, rough=.15, seed=8)                             # 首
    k.box('main', 'skin', .18, .2, .3, 0, .82, .7, pitch=-.45, bev=.06)                                  # 顔
    k.box('main', 'black', .08, .05, .04, 0, .74, .86, pitch=-.45, bev=0)                                 # 鼻
    for sx in (-1, 1):
        k.box('main', 'skin', .16, .05, .07, sx * .14, .92, .66, roll=sx * .4, bev=.02)                    # 耳
        k.box('main', 'black', .03, .03, .02, sx * .08, .88, .78, bev=0)                                   # 目
    for x, z in ((-.13, .28), (.13, .28), (-.13, -.32), (.13, -.32)):
        k.cyl('main', 'skin', .07, .5, x, .31, z, 'y', 6, 0, d2=.06)                                      # 脚(蹄まで)
        k.cyl('main', 'black', .075, .06, x, .03, z, 'y', 6, 0)                                            # 蹄
    k.blob('main', 'wool', .09, 0, .6, -.48, sy=1.4, sub=1, rough=.1, seed=9)                             # 尾
    return dict(circ=.5)

@prop('haybale')
def _(k):
    """ロール状の干し草(資料: 直径1.2〜1.5m、幅1.2m前後。ネットで巻いてある)。直径1.15・幅.95(1unit=1.3m)。
    部品: 少しふくらんだ円筒・巻きの段(ネットの帯)・端面の渦巻き・地面に接する平らな所"""
    k.cyl('main', 'straw', 1.12, .96, 0, .56, 0, 'x', 24, .04)                                        # 本体
    k.cyl('main', 'straw', 1.16, .7, 0, .56, 0, 'x', 24, .03)                                          # 中ほどのふくらみ
    for x in (-.3, 0, .3):                                                                                 # ネットの帯
        k.cyl('main', 'strawD', 1.17, .05, x, .56, 0, 'x', 22, 0)
    for sx in (-1, 1):                                                                                    # 端面の渦巻き(同心の段)
        for r in (.42, .3, .18): k.cyl('main', 'strawD', r * 2, .02, sx * .485, .56, 0, 'x', 18, 0)
    return dict(circ=.62)

@prop('fence_wood')
def _(k):
    """牧場の木の柵(アルデンヌ・トスカーナの農村): 先をとがらせた杭・横木3本(釘で留める)・杭の根元の土"""
    for x in (-1.25, 1.25):
        k.box('main', 'wood', .14, 1.2, .14, x, .6, 0, bev=.02)
        k.prism('main', 'wood', [(-.07, 1.2), (.07, 1.2), (0, 1.32)], x - .07, x + .07, 'x', 0, 1)          # とがった杭の頭
        k.blob('main', 'mud', .13, x, .02, 0, sy=.35, sub=1, rough=.3, seed=int(x * 10) + 180)
    for y in (.35, .7, 1.02):
        k.box('main', 'woodL', 2.7, .1, .05, 0, y, .095, bev=.01)
        for x in (-1.25, 1.25): k.cyl('main', 'iron', .025, .02, x, y, .125, 'z', 5, 0)                     # 釘の頭
    return dict(box=[2.6, .3, 1.2])

# ---------------------------------------------------------------- 焼き込みと書き出し
def make_mat():
    m = bpy.data.materials.new('vc'); nt = m.node_tree; N = nt.nodes; L = nt.links
    for n in list(N): N.remove(n)
    out = N.new('ShaderNodeOutputMaterial'); em = N.new('ShaderNodeEmission'); L.new(em.outputs[0], out.inputs['Surface'])
    at = N.new('ShaderNodeAttribute'); at.attribute_name = 'base'
    ao = N.new('ShaderNodeAmbientOcclusion'); ao.samples = 24; ao.inputs['Distance'].default_value = 1.2
    mr = N.new('ShaderNodeMapRange'); mr.inputs['To Min'].default_value = .38; L.new(ao.outputs['AO'], mr.inputs['Value'])
    mu = N.new('ShaderNodeVectorMath'); mu.operation = 'SCALE'; L.new(at.outputs['Color'], mu.inputs[0]); L.new(mr.outputs[0], mu.inputs['Scale'])
    L.new(mu.outputs[0], em.inputs['Color']); return m

def build(name, buf, out):
    for o in list(bpy.data.objects): bpy.data.objects.remove(o)
    for c in (bpy.data.meshes, bpy.data.materials, bpy.data.curves):
        for b in list(c): c.remove(b)
    s_cut.clear()
    k = PK(); meta = P[name](k) or {}
    sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 16
    dg = bpy.context.evaluated_depsgraph_get()
    # 各部品: 色を属性 base に入れてから(ベベル等を適用して)部品(part)×素材の種類ごとに結合
    groups = {}
    lo_ = Vector((1e9,) * 3); hi_ = Vector((-1e9,) * 3)
    for o, _, _ in k.objs:
        for c in o.bound_box: w = o.matrix_world @ Vector(c); lo_ = Vector(map(min, lo_, w)); hi_ = Vector(map(max, hi_, w))
    sub_len = max(.9, (hi_ - lo_).length / 45)                                          # AO用に分割する辺の長さ(大きな名所ほど粗く)
    for o, part, col in k.objs:
        rgb, cat = PAL[col]
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg)); me.transform(o.matrix_world)
        lin = [c ** 2.2 for c in rgb]                                                     # パレットは sRGB。焼き込みはリニアで行う
        a = me.color_attributes.new('base', 'FLOAT_COLOR', 'CORNER'); a.data.foreach_set('color', [*lin, 1] * len(me.loops))
        no = bpy.data.objects.new('j', me); sc.collection.objects.link(no); groups.setdefault((part, cat), []).append(no)
    for o, _, _ in k.objs: bpy.data.objects.remove(o)
    for c in s_cut: bpy.data.objects.remove(c)
    joined = []
    for (part, cat), objs in groups.items():
        bpy.ops.object.select_all(action='DESELECT')
        for o in objs: o.select_set(True)
        bpy.context.view_layer.objects.active = objs[0]
        if len(objs) > 1: bpy.ops.object.join()
        j = bpy.context.view_layer.objects.active; j.name = f'{part}|{cat}'
        bm = bmesh.new(); bm.from_mesh(j.data)                                           # AOの階調のため長い辺を分割
        bmesh.ops.triangulate(bm, faces=bm.faces)
        for _ in range(2):
            long = [e for e in bm.edges if e.calc_length() > sub_len]
            if long: bmesh.ops.subdivide_edges(bm, edges=long, cuts=1, use_grid_fill=False)
            bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if len(f.verts) > 3])
        bm.to_mesh(j.data); bm.free(); j.data.set_sharp_from_angle(angle=math.radians(40))
        joined.append((j, part, cat))
    # 地面(AOで接地部を暗くするため。書き出さない)
    gp = bpy.data.meshes.new('gp'); bmg = bmesh.new(); bmesh.ops.create_grid(bmg, x_segments=1, y_segments=1, size=60); bmg.to_mesh(gp); bmg.free()
    gpo = bpy.data.objects.new('gp', gp); sc.collection.objects.link(gpo); gpo.location = (0, 0, meta.pop('ground', 0) - .001)
    mat = make_mat()
    bpy.ops.object.select_all(action='DESELECT')
    for j, _, _ in joined:
        j.data.materials.clear(); j.data.materials.append(mat); j.data.polygons.foreach_set('material_index', [0] * len(j.data.polygons)); ca = j.data.color_attributes.new('bake', 'FLOAT_COLOR', 'CORNER'); j.data.color_attributes.active_color = ca; j.select_set(True)
    bpy.context.view_layer.objects.active = joined[0][0]
    bpy.ops.object.bake(type='EMIT', target='VERTEX_COLORS')
    parts = []
    for j, part, cat in joined:
        me = j.data; me.calc_loop_triangles(); nl = len(me.loops)
        co = np.zeros(len(me.vertices) * 3, np.float32); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
        vi = np.zeros(nl, np.int32); me.loops.foreach_get('vertex_index', vi)
        nr = np.zeros(nl * 3, np.float32); me.corner_normals.foreach_get('vector', nr); nr = nr.reshape(-1, 3)
        # 発光部品は元の色のまま(AOで暗くしない)
        cl = np.zeros(nl * 4, np.float32); me.color_attributes['base' if cat == 'emit' else 'bake'].data.foreach_get('color', cl); cl = cl.reshape(-1, 4)[:, :3]
        tri = np.zeros(len(me.loop_triangles) * 3, np.int32); me.loop_triangles.foreach_get('loops', tri)
        pos = co[vi][:, [0, 2, 1]]; nrm = nr[:, [0, 2, 1]]
        piv = (meta.get('pivots') or {}).get(part)
        if piv: pos = pos - np.array(piv[:3], np.float32)
        key = np.round(np.hstack([pos * 2000, nrm * 100, cl * 255])).astype(np.int64)
        _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True); tri = inv.reshape(-1)[tri]
        p_, n_, c_ = pos[first], nrm[first], cl[first]
        lo = p_.min(0); scl = np.maximum(p_.max(0) - lo, 1e-6)
        q = np.round((p_ - lo) / scl * 65535).astype(np.uint16); n8 = np.round(np.clip(n_, -1, 1) * 127).astype(np.int8)
        c8 = np.round(np.clip(c_, 0, 1) ** (1 / 2.2) * 255).astype(np.uint8)          # 頂点色は sRGB で保存(PBR側でリニアに戻す)
        big = len(p_) > 65535; idx = tri.astype(np.uint32 if big else np.uint16)
        def put(a):
            while len(buf) % 4: buf.append(0)
            off = len(buf); buf.extend(a.tobytes()); return off
        parts.append(dict(part=part, cat=cat, nv=int(len(p_)), ni=int(len(tri)), lo=lo.tolist(), sc=scl.tolist(), i32=bool(big), p=put(q), n=put(n8), c=put(c8), i=put(idx)))
    meta = {k_: v for k_, v in meta.items() if k_ != 'walls'}
    out[name] = dict(parts=parts, **meta)
    print(name, 'verts', sum(p['nv'] for p in parts))

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    for n in (ONLY or list(P.keys())):  # 小物ごとに <名前>.bin / <名前>.json(pack_props.py でまとめる)
        buf = bytearray(); out = {}; build(n, buf, out)
        open(os.path.join(OUT, n + '.bin'), 'wb').write(bytes(buf)); json.dump(out[n], open(os.path.join(OUT, n + '.json'), 'w'))
