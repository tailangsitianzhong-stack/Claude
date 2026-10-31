# -*- coding: utf-8 -*-
"""
建物の壁の「1区画ぶんのタイル」(窓1つ+壁)を Blender で立体的に作り、色テクスチャと凹凸(ノーマルマップ)に焼く。

  python tools/facade_tiles.py <出力ディレクトリ> [タイル名...]

- 窓の奥行き・窓枠・桟・窓台・よろい戸・花の窓箱・バルコニー・木組みの梁などを実際の形で作る
- 漆喰・レンガ・切石・サイディングなどの細かい凹凸はシェーダーの手続き模様(Bump)で付ける
- 正投影カメラで真正面から2回描く: ①色×陰影(AO) ②接空間の法線(凹凸)。左右・上下に同じ区画を並べて端もつながるようにする
出力: <名前>_a.npy(色) / <名前>_n.npy(法線)(8bit RGB の配列) と tiles.json(各タイルの幅・高さ[ゲームの単位])
"""
import os, sys, math, json, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh
import numpy as np
from mathutils import Vector

OUT = sys.argv[1] if len(sys.argv) > 1 else '.'
ONLY = sys.argv[2:]
PXU = 80  # 1単位あたりの画素数(幅3.2 → 256px)

def lin(c):
    c = c.lstrip('#'); return tuple((int(c[i:i + 2], 16) / 255) ** 2.2 for i in (0, 2, 4))

# ---------------------------------------------------------------- 素材(手続き模様)
MATS = {}
def mat(kind, col, rough=None):
    key = (kind, col)
    if key in MATS: return MATS[key][0]
    m = bpy.data.materials.new(kind); nt = m.node_tree; N = nt.nodes; L = nt.links
    for n in list(N): N.remove(n)
    out = N.new('ShaderNodeOutputMaterial'); em = N.new('ShaderNodeEmission'); L.new(em.outputs[0], out.inputs['Surface'])
    geo = N.new('ShaderNodeNewGeometry'); sep = N.new('ShaderNodeSeparateXYZ'); L.new(geo.outputs['Position'], sep.inputs[0])
    uv = N.new('ShaderNodeCombineXYZ'); L.new(sep.outputs['X'], uv.inputs['X']); L.new(sep.outputs['Z'], uv.inputs['Y']); L.new(sep.outputs['Y'], uv.inputs['Z'])  # 壁面の座標(横, 縦, 奥)
    noise = N.new('ShaderNodeTexNoise'); noise.inputs['Scale'].default_value = 3; noise.inputs['Detail'].default_value = 6; L.new(uv.outputs[0], noise.inputs['Vector'])
    fine = N.new('ShaderNodeTexNoise'); fine.inputs['Scale'].default_value = 40; fine.inputs['Detail'].default_value = 4; L.new(uv.outputs[0], fine.inputs['Vector'])
    height = None; strength = .25; colv = noise.outputs['Fac']; dist = .02
    def math_(op, a, b):
        n = N.new('ShaderNodeMath'); n.operation = op
        for i, v in enumerate((a, b)):
            if isinstance(v, (int, float)): n.inputs[i].default_value = v
            else: L.new(v, n.inputs[i])
        return n.outputs[0]
    if kind in ('brick', 'ashlar', 'tiles'):
        br = N.new('ShaderNodeTexBrick'); L.new(uv.outputs[0], br.inputs['Vector'])
        bw, bh, mo = {'brick': (.24, .075, .012), 'ashlar': (.6, .3, .018), 'tiles': (.1, .1, .006)}[kind]
        br.inputs['Scale'].default_value = 1; br.inputs['Brick Width'].default_value = bw; br.inputs['Row Height'].default_value = bh
        br.inputs['Mortar Size'].default_value = mo; br.inputs['Mortar Smooth'].default_value = .3; br.offset = .5 if kind != 'tiles' else 0
        br.inputs['Color1'].default_value = (1, 1, 1, 1); br.inputs['Color2'].default_value = (.82, .82, .82, 1); br.inputs['Mortar'].default_value = (0, 0, 0, 1)
        height = math_('ADD', math_('MULTIPLY', br.outputs['Fac'], -1), math_('MULTIPLY', fine.outputs['Fac'], .25)); strength = .55 if kind != 'tiles' else .3; dist = .015
        colv = math_('ADD', math_('MULTIPLY', br.outputs['Color'], .6), math_('MULTIPLY', noise.outputs['Fac'], .4))
        mortar = br.outputs['Fac']
    elif kind == 'siding':  # 横張りの板(下端が段になる)
        fr = math_('FRACT', math_('DIVIDE', sep.outputs['Z'], .2), 0)
        height = math_('ADD', fr, math_('MULTIPLY', fine.outputs['Fac'], .1)); strength = .35; dist = .02
    elif kind == 'wood':
        st = N.new('ShaderNodeMapping'); st.inputs['Scale'].default_value = (1, 12, 1); L.new(uv.outputs[0], st.inputs['Vector']); L.new(st.outputs[0], fine.inputs['Vector'])
        height = fine.outputs['Fac']; strength = .3
    elif kind in ('plaster', 'conc'):
        height = math_('ADD', fine.outputs['Fac'], math_('MULTIPLY', noise.outputs['Fac'], .5)); strength = .18 if kind == 'plaster' else .12
    else:
        height = math_('MULTIPLY', fine.outputs['Fac'], .05); strength = .05
    # 色: 基本色 × (模様のゆらぎ) × 陰影(AO)。ガラスは上ほど空が映って明るい
    rgb = N.new('ShaderNodeRGB'); rgb.outputs[0].default_value = (*lin(col), 1)
    var = math_('ADD', .82, math_('MULTIPLY', colv, .36))
    if kind == 'glass': var = math_('ADD', .55, math_('MULTIPLY', math_('FRACT', math_('DIVIDE', sep.outputs['Z'], 3.0001), 0), 1.3))
    if kind in ('brick', 'ashlar'):
        var = math_('ADD', math_('MULTIPLY', var, mortar), math_('MULTIPLY', math_('SUBTRACT', 1, mortar), 1.25))  # 目地は明るい灰
    ao = N.new('ShaderNodeAmbientOcclusion'); ao.samples = 16; ao.inputs['Distance'].default_value = .45
    aor = N.new('ShaderNodeMapRange'); aor.inputs['To Min'].default_value = .35; L.new(ao.outputs['AO'], aor.inputs['Value'])
    c1 = N.new('ShaderNodeVectorMath'); c1.operation = 'SCALE'; L.new(rgb.outputs[0], c1.inputs[0]); L.new(var, c1.inputs['Scale'])
    alb = N.new('ShaderNodeVectorMath'); alb.operation = 'SCALE'; L.new(c1.outputs[0], alb.inputs[0]); L.new(aor.outputs[0], alb.inputs['Scale'])
    # 法線: Bump → (x, 上, 手前) を 0..1 に
    bump = N.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = strength; bump.inputs['Distance'].default_value = dist; L.new(height, bump.inputs['Height'])
    ns = N.new('ShaderNodeSeparateXYZ'); L.new(bump.outputs['Normal'], ns.inputs[0])
    ny = math_('MULTIPLY', ns.outputs['Y'], -1)
    nc = N.new('ShaderNodeCombineXYZ'); L.new(ns.outputs['X'], nc.inputs['X']); L.new(ns.outputs['Z'], nc.inputs['Y']); L.new(ny, nc.inputs['Z'])
    enc = N.new('ShaderNodeVectorMath'); enc.operation = 'MULTIPLY_ADD'; L.new(nc.outputs[0], enc.inputs[0]); enc.inputs[1].default_value = (.5, .5, .5); enc.inputs[2].default_value = (.5, .5, .5)
    MATS[key] = (m, alb.outputs[0], enc.outputs[0], em)
    return m

def set_mode(mode):
    for m, a, n, em in MATS.values():
        L = m.node_tree.links
        for l in list(em.inputs['Color'].links): L.remove(l)
        L.new(a if mode == 'alb' else n, em.inputs['Color'])

# ---------------------------------------------------------------- 形(ゲーム座標: x=右, y=上, z=手前が負。Blender は (x, -z, y))
class T:
    def __init__(s): s.objs = []; s.walls = []; s.holes = []
    def wall(s, m, W, H):  # 壁の大板(後で窓・扉の開口をくり抜く)
        o = s.box(m, -W, -H, 2 * W, 2 * H, -.3, 0, bev=0); s.walls.append(o); return o
    def hole(s, x0, y0, x1, y1, depth, arch=False):
        s.holes.append((x0, y0, x1, y1, depth, arch))
    def _add(s, bm, m, bev=0):
        me = bpy.data.meshes.new('t'); bm.to_mesh(me); bm.free(); o = bpy.data.objects.new('t', me); bpy.context.scene.collection.objects.link(o)
        if bev > 0: b = o.modifiers.new('b', 'BEVEL'); b.width = bev; b.segments = 2; b.limit_method = 'ANGLE'
        o.data.materials.append(m); s.objs.append(o); return o
    def box(s, m, x0, y0, x1, y1, z0, z1, bev=.01):  # x0..x1, y0..y1 の範囲、手前へ z0..z1 だけ出る(負=引っ込む)
        bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1)
        bmesh.ops.scale(bm, vec=Vector((x1 - x0, z1 - z0, y1 - y0)), verts=bm.verts)
        bmesh.ops.translate(bm, vec=Vector(((x0 + x1) / 2, -(z0 + z1) / 2, (y0 + y1) / 2)), verts=bm.verts)
        return s._add(bm, m, min(bev, (x1 - x0) * .3, (y1 - y0) * .3, (z1 - z0) * .3))
    def beam(s, m, xa, ya, xb, yb, w, z0, z1):  # 斜めの梁
        L = math.hypot(xb - xa, yb - ya); bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1)
        bmesh.ops.scale(bm, vec=Vector((L, z1 - z0, w)), verts=bm.verts)
        bmesh.ops.rotate(bm, cent=Vector(), matrix=__import__('mathutils').Matrix.Rotation(-math.atan2(yb - ya, xb - xa), 3, 'Y'), verts=bm.verts)
        bmesh.ops.translate(bm, vec=Vector(((xa + xb) / 2, -(z0 + z1) / 2, (ya + yb) / 2)), verts=bm.verts)
        return s._add(bm, m, .008)
    def blob(s, m, r, x, y, z):
        bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=1, radius=r)
        bmesh.ops.translate(bm, vec=Vector((x, -z, y)), verts=bm.verts); return s._add(bm, m)
    def arch(s, m, x0, x1, y0, yt, z0, z1, segs=12):  # 上が半円の板(アーチの開口・扉)
        r = (x1 - x0) / 2; cx = (x0 + x1) / 2; pts = [(x0, y0), (x1, y0)] + [(cx + r * math.cos(a), yt - r + r * math.sin(a)) for a in [i * math.pi / segs for i in range(segs + 1)]]
        bm = bmesh.new(); vs = [bm.verts.new((p[0], -z0, p[1])) for p in pts]; f = bm.faces.new(vs)
        r_ = bmesh.ops.extrude_face_region(bm, geom=[f]); bmesh.ops.translate(bm, vec=Vector((0, -(z1 - z0), 0)), verts=[e for e in r_['geom'] if isinstance(e, bmesh.types.BMVert)])
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces); return s._add(bm, m)

def window(t, x0, y0, x1, y1, frame, glass, sill=None, cross=True, depth=.16, fw=.07, hbar=.62):
    """窓: 壁の開口(奥へ depth)・ガラス・枠・十字の桟・窓台"""
    t.hole(x0, y0, x1, y1, depth)
    t.box(glass, x0, y0, x1, y1, -depth - .02, -depth, bev=0)
    for (a, b, c, d) in ((x0, y0, x0 + fw, y1), (x1 - fw, y0, x1, y1), (x0, y0, x1, y0 + fw), (x0, y1 - fw, x1, y1)):
        t.box(frame, a, b, c, d, -depth, -depth + .05)
    if cross:
        xm = (x0 + x1) / 2; t.box(frame, xm - fw / 2, y0, xm + fw / 2, y1, -depth, -depth + .045)
        ym = y0 + (y1 - y0) * hbar; t.box(frame, x0, ym - fw / 2, x1, ym + fw / 2, -depth, -depth + .045)
    if sill: t.box(sill, x0 - .1, y0 - .1, x1 + .1, y0, -.02, .1, bev=.015)

def ring(t, m, x0, y0, x1, y1, wd, z0, z1):  # 開口のまわりの額縁(4本の帯)
    for (a, b, c, d) in ((x0 - wd, y0 - wd, x0, y1 + wd), (x1, y0 - wd, x1 + wd, y1 + wd), (x0, y0 - wd, x1, y0), (x0, y1, x1, y1 + wd)):
        t.box(m, a, b, c, d, z0, z1, bev=.01)

def shutters(t, m, x0, y0, x1, y1):
    w = (x1 - x0) / 2 * .95
    for (a, b) in ((x0 - w - .02, x0 - .02), (x1 + .02, x1 + w + .02)):
        t.box(m, a, y0, b, y1, 0, .04)
        n = int((y1 - y0) / .09)
        for i in range(n): t.box(m, a + .04, y0 + .05 + i * .09, b - .04, y0 + .09 + i * .09, .03, .06, bev=.004)  # 羽板

def flowers(t, x0, x1, y, rnd):
    t.box(mat('wood', '#5a3a24'), x0, y, x1, y + .2, 0, .22, bev=.01)
    for i in range(int((x1 - x0) / .09)):
        x = x0 + .05 + i * .09 + rnd.uniform(-.02, .02)
        t.blob(mat('paint', '#3e6a2a'), .07, x, y + .22, .1); t.blob(mat('paint', rnd.choice(['#d23a3a', '#e86aa0', '#f0c040', '#ffffff', '#d85a2a'])), .045, x + .02, y + .3, .06 + rnd.uniform(0, .08))

# ---------------------------------------------------------------- タイルの定義: f(t, W, H, rnd) が1区画の形を作る(原点=左下)
TILES = {}
def tile(name, W, H):
    def deco(f): TILES[name] = (W, H, f); return f
    return deco

EU = [('#d8ccb2', '#4c6a4a', 1, 'plaster'), ('#cfa86e', '#6a4a32', 2, 'plaster'), ('#b9b6ae', None, 0, 'plaster'), ('#d6b2a4', '#4c6a4a', 1, 'plaster'), ('#9a5a44', None, 3, 'brick')]
for i, (wc, sc, sh, wk) in enumerate(EU):
    def _mk(i, wc, sc, sh, wk):
        @tile('eu_f%d' % i, 3.2, 3.0)
        def _(t, W, H, rnd):
            t.wall(mat(wk, wc), W, H)
            t.box(mat('plaster', '#e8e2d6'), -W, -.0, 2 * W, .18, 0, .06, bev=.01)                       # 階の帯(コーニス)
            x0, x1, y0, y1 = W * .3, W * .7, .55, 2.45
            ring(t, mat('plaster', '#ece6da'), x0, y0, x1, y1, .12, 0, .035)                     # 窓の額縁
            if wk == 'brick': t.box(mat('ashlar', '#c8bca2'), x0 - .15, y1, x1 + .15, y1 + .22, 0, .05)   # まぐさ石
            window(t, x0, y0, x1, y1, mat('paint', '#ece8e0'), mat('glass', '#46545c'), sill=mat('plaster', '#e0dacd'))
            if sh in (1, 2): shutters(t, mat('wood', sc), x0, y0, x1, y1)
            if sh == 1 and i == 0: flowers(t, x0, x1, y0 + .02, rnd)
    _mk(i, wc, sc, sh, wk)

@tile('eu_shop', 3.2, 3.6)
def _(t, W, H, rnd):
    t.wall(mat('ashlar', '#9a9286'), W, H)
    t.box(mat('paint', '#7a2a22'), -W, 2.75, 2 * W, 3.25, 0, .08, bev=.015)                              # 看板帯
    t.box(mat('plaster', '#e8e2d6'), -W, 3.25, 2 * W, 3.42, 0, .12, bev=.015)
    t.box(mat('ashlar', '#7a7268'), -W, 0, 2 * W, .3, 0, .05)                                             # 腰石
    window(t, .3, .45, W - .3, 2.55, mat('metal', '#2a2622'), mat('glass', '#38464c'), cross=False, depth=.2, fw=.06)
    t.box(mat('metal', '#2a2622'), W / 2 - .03, .45, W / 2 + .03, 2.55, -.2, -.15)
    t.box(mat('metal', '#2a2622'), .3, 2.15, W - .3, 2.2, -.2, -.15)

OT = ['#efe4cc', '#ead2a8', '#f0d6cc', '#dfe6d6', '#f2ead8']
for i, pc in enumerate(OT):
    def _mk(i, pc):
        @tile('ot_h%d' % i, 3.2, 3.0)
        def _(t, W, H, rnd):
            tim = mat('wood', '#4a3020')
            t.wall(mat('plaster', pc), W, H)
            for y in (0, H): t.box(tim, -W, y - .1, 2 * W, y + .1, 0, .05, bev=.01)                   # 横の梁(上下の区画とつながる)
            for x in (0, W): t.box(tim, x - .1, -H, x + .1, 2 * H, 0, .05, bev=.01)                   # 柱(左右の区画とつながる)
            t.beam(tim, .1, .1, .75, 2.0, .16, 0, .04); t.beam(tim, W - .1, .1, W - .75, 2.0, .16, 0, .04)  # 筋交い
            x0, x1, y0, y1 = 1.0, 2.2, .8, 2.3
            window(t, x0, y0, x1, y1, mat('paint', '#e8e0cc'), mat('glass', '#2c3a40'), cross=True, depth=.12, fw=.06, hbar=.55)
            t.box(tim, x0 - .1, y0 - .1, x1 + .1, y0, 0, .06); t.box(tim, x0 - .1, y1, x1 + .1, y1 + .12, 0, .06)
            if i % 2 == 0: flowers(t, x0 - .05, x1 + .05, y0 - .32, rnd)
    _mk(i, pc)

@tile('ot_st', 3.2, 3.4)
def _(t, W, H, rnd):
    t.wall(mat('ashlar', '#b4a890'), W, H); t.hole(1.05, 0, 2.15, 2.5, .13, arch=True)
    t.arch(mat('wood', '#4a3424'), 1.05, 2.15, 0, 2.5, -.2, -.12)                                      # アーチの扉(奥)
    for i in range(9):  # アーチの迫石(開口のまわりに放射状)
        a = math.pi * i / 8; r = .62; cx, cy = 1.6, 1.95
        x, y = cx + math.cos(a) * r, cy + math.sin(a) * r; t.beam(mat('ashlar', '#c8bca2'), x - math.cos(a) * .1, y - math.sin(a) * .1, x + math.cos(a) * .12, y + math.sin(a) * .12, .2, 0, .05)
    for x in (1.35, 1.6, 1.85): t.box(mat('metal', '#2a2420'), x - .015, .2, x + .015, 2.1, -.12, -.1)
    for x0 in (.15, 2.55): window(t, x0, 1.0, x0 + .5, 1.8, mat('metal', '#3a3430'), mat('glass', '#2c3a40'), cross=False, depth=.15, fw=.04)
    t.box(mat('ashlar', '#a49880'), -W, 0, 2 * W, .25, 0, .05)

JO = [('#6a8aa6', 'curtain'), ('#9aa4ac', 'punch'), ('#c8ccce', 'punch')]
for i, (wc, kind) in enumerate(JO):
    def _mk(i, wc, kind):
        @tile('jp_o%d' % i, 3.2, 3.6)
        def _(t, W, H, rnd):
            if kind == 'curtain':  # カーテンウォール: ガラス面+縦の方立て+階の帯
                t.wall(mat('glass', wc), W, H)
                for x in (0, W / 2, W): t.box(mat('metal', '#2c3640'), x - .05, -H, x + .05, 2 * H, 0, .12, bev=.01)
                t.box(mat('metal', '#3a4650'), -W, -.05, 2 * W, .45, 0, .06, bev=.01)
            else:
                t.wall(mat('tiles' if i == 1 else 'conc', wc), W, H)
                window(t, .3, .7, W - .3, 3.0, mat('metal', '#8a9096'), mat('glass', '#34404c'), cross=True, depth=.14, fw=.05, hbar=.75)
                t.box(mat('metal', '#a0a6aa'), .25, .62, W - .25, .7, -.02, .06)
                t.box(mat('conc', wc), -W, -.02, 2 * W, .18, 0, .03)
    _mk(i, wc, kind)

for i, wc in enumerate(['#efebe2', '#d8d2c6', '#e8e2d8']):
    def _mk(i, wc):
        @tile('jp_m%d' % i, 3.2, 3.0)
        def _(t, W, H, rnd):  # マンション: 掃き出し窓+バルコニー(床・手すり壁・物干し)
            t.wall(mat('tiles', wc), W, H)
            window(t, .25, .02, W - .25, 2.2, mat('metal', '#9aa0a4'), mat('glass', '#3a4a58'), cross=True, depth=.1, fw=.05, hbar=.99)
            t.box(mat('conc', '#d8d6d0'), -W, -.12, 2 * W, .06, 0, .9, bev=.01)                              # バルコニーの床
            t.box(mat('plaster', '#f6f4ee'), -W, .06, 2 * W, 1.05, .82, .9, bev=.01)                         # 手すり壁
            t.box(mat('metal', '#8a9096'), -W, 1.05, 2 * W, 1.11, .8, .92, bev=.01)
            for x in (0, W): t.box(mat('plaster', '#e0ddd5'), x - .06, .06, x + .06, H - .1, 0, .9)          # 隔て板
            t.box(mat('metal', '#c0c4c6'), .3, 2.45, W - .3, 2.48, .3, .33, bev=0)                           # 物干し竿
            if i != 1:
                for k in range(2): x = .8 + k * 1.1 + rnd.uniform(-.1, .1); t.box(mat('paint', rnd.choice(['#7aa0c8', '#e8b0a0', '#f0f0f0', '#a0c890'])), x, 1.7, x + .5, 2.45, .28, .34, bev=0)
    _mk(i, wc)

for i, wc in enumerate(['#efe6d2', '#dcd6cc', '#f4f0e8', '#c8b8a0']):
    def _mk(i, wc):
        @tile('jp_h%d' % i, 3.2, 2.8)
        def _(t, W, H, rnd):  # 戸建て: サイディング・アルミサッシの窓・シャッター箱・面格子
            t.wall(mat('siding', wc), W, H)
            x0, x1, y0, y1 = .7, 2.5, .8, 2.1
            ring(t, mat('paint', '#f4f4f0'), x0, y0, x1, y1, .08, 0, .03)
            window(t, x0, y0, x1, y1, mat('metal', '#b8bcbe'), mat('glass', '#34424c'), cross=False, depth=.08, fw=.05)
            t.box(mat('metal', '#b8bcbe'), (x0 + x1) / 2 - .03, y0, (x0 + x1) / 2 + .03, y1, -.08, -.04)
            t.box(mat('metal', '#8a8a86'), x0 - .12, y1 + .08, x1 + .12, y1 + .36, 0, .2, bev=.02)         # シャッター箱
            if i % 2:
                for k in range(7): x = x0 + .1 + k * (x1 - x0 - .2) / 6; t.box(mat('metal', '#a0a4a6'), x - .015, y0 + .05, x + .015, y1 - .05, .06, .09, bev=0)  # 面格子
            t.box(mat('conc', '#b0aca4'), -W, -.05, 2 * W, .12, 0, .03)
    _mk(i, wc)

# ---------------------------------------------------------------- 実在の場所のタイル
def sash(t, x0, y0, x1, y1, frame, glass, nx=3, ny=4, depth=.14):
    """上げ下げ窓(格子の細かいガラス): ロンドンのジョージアン様式"""
    window(t, x0, y0, x1, y1, frame, glass, cross=False, depth=depth, fw=.06)
    for i in range(1, nx): x = x0 + (x1 - x0) * i / nx; t.box(frame, x - .02, y0, x + .02, y1, -depth, -depth + .04)
    for j in range(1, ny): y = y0 + (y1 - y0) * j / ny; t.box(frame, x0, y - .02 if j != ny // 2 else y - .05, x1, y + .02 if j != ny // 2 else y + .05, -depth, -depth + .05)

for i, (bc, wk) in enumerate([('#c9a86a', 'brick'), ('#9a4a36', 'brick'), ('#b89a70', 'brick')]):
    def _mk(i, bc, wk):
        @tile('ld_br%d' % i, 3.2, 3.0)
        def _(t, W, H, rnd):
            t.wall(mat(wk, bc), W, H)
            x0, x1, y0, y1 = 1.0, 2.2, .45, 2.55
            t.box(mat('brick', '#7a3a2a' if i != 1 else '#c9a86a'), x0 - .08, y1, x1 + .08, y1 + .26, 0, .02)     # 平アーチのまぐさ
            sash(t, x0, y0, x1, y1, mat('paint', '#f2f0ea'), mat('glass', '#34404a'))
            t.box(mat('ashlar', '#d8d2c2'), x0 - .1, y0 - .12, x1 + .1, y0, -.02, .1, bev=.015)
            if i == 2: t.box(mat('ashlar', '#e0dacb'), -W, -.0, 2 * W, .14, 0, .04)
            if i == 0:
                t.box(mat('metal', '#141414'), x0 - .1, y0, x1 + .1, y0 + .05, .12, .3)                       # 鋳鉄のバルコネット
                for k in range(9): x = x0 + (x1 - x0) * k / 8; t.box(mat('metal', '#141414'), x - .012, y0, x + .012, y0 + .45, .26, .29, bev=0)
                t.box(mat('metal', '#141414'), x0 - .1, y0 + .43, x1 + .1, y0 + .47, .25, .3, bev=0)
    _mk(i, bc, wk)

@tile('ld_wh', 3.2, 3.0)
def _(t, W, H, rnd):  # ロンドンの倉庫(シャッド・テムズ): 黄色いレンガ・丸いアーチの窓・鉄の帯
    t.wall(mat('brick', '#a88a5a'), W, H)
    x0, x1, y0, y1 = 1.0, 2.2, .5, 2.4
    t.hole(x0, y0, x1, y1, .18, arch=True)
    t.arch(mat('glass', '#2c3438'), x0, x1, y0, y1, -.2, -.18)
    for k in range(1, 4): x = x0 + (x1 - x0) * k / 4; t.box(mat('metal', '#2a2a28'), x - .02, y0, x + .02, y1 - .3, -.18, -.15)
    for j in range(1, 4): y = y0 + (y1 - y0 - .4) * j / 4; t.box(mat('metal', '#2a2a28'), x0, y - .02, x1, y + .02, -.18, -.15)
    for a in range(9):
        ang = math.pi * a / 8; r = .62; cx, cy = 1.6, y1 - .6
        t.beam(mat('brick', '#8a5a3a'), cx + math.cos(ang) * (r - .02), cy + math.sin(ang) * (r - .02), cx + math.cos(ang) * (r + .2), cy + math.sin(ang) * (r + .2), .14, 0, .02)
    t.box(mat('ashlar', '#c8bca2'), x0 - .1, y0 - .1, x1 + .1, y0, -.02, .08)
    t.box(mat('metal', '#3a3a38'), -W, 2.85, 2 * W, 2.95, 0, .05)

@tile('ld_shop', 3.2, 3.6)
def _(t, W, H, rnd):  # ヴィクトリア朝の店先/パブ: 濃緑の木の看板・付柱・大きなガラス
    t.wall(mat('wood', '#1e3a2a'), W, H)
    t.box(mat('wood', '#1e3a2a'), -W, 2.7, 2 * W, 3.3, 0, .12, bev=.02); t.box(mat('paint', '#c8a050'), .3, 2.85, W - .3, 3.15, .12, .14, bev=0)
    t.box(mat('wood', '#18301f'), -W, 3.3, 2 * W, 3.45, 0, .2, bev=.02)
    for x in (0, W): t.box(mat('wood', '#18301f'), x - .14, 0, x + .14, 2.7, 0, .1, bev=.02)
    window(t, .3, .7, W - .3, 2.55, mat('wood', '#1e3a2a'), mat('glass', '#2a3236'), cross=False, depth=.12, fw=.06)
    for k in range(1, 3): x = .3 + (W - .6) * k / 3; t.box(mat('wood', '#1e3a2a'), x - .03, .7, x + .03, 2.55, -.12, -.08)
    t.box(mat('wood', '#1e3a2a'), .3, 2.15, W - .3, 2.19, -.12, -.08)
    t.box(mat('wood', '#18301f'), .2, 0, W - .2, .7, 0, .06, bev=.02)

for i, (wc, hood) in enumerate([('#e2d4b4', 'tri'), ('#cfd2cc', 'flat'), ('#e6c8a8', 'arch')]):
    def _mk(i, wc, hood):
        @tile('bl_a%d' % i, 3.2, 3.2)
        def _(t, W, H, rnd):  # ベルリンの旧建築(アルトバウ): 漆喰・窓の額縁と庇(三角/水平/弓形)・階の帯
            t.wall(mat('plaster', wc), W, H)
            light = mat('plaster', '#f0ebe0')
            t.box(light, -W, 0, 2 * W, .2, 0, .07, bev=.01)
            x0, x1, y0, y1 = 1.0, 2.2, .7, 2.6
            ring(t, light, x0, y0, x1, y1, .13, 0, .05)
            window(t, x0, y0, x1, y1, mat('paint', '#f4f2ec'), mat('glass', '#3a4650'), cross=True, depth=.16, fw=.07, hbar=.7)
            t.box(light, x0 - .2, y0 - .16, x1 + .2, y0 - .02, -.02, .12, bev=.015)
            if hood == 'tri':
                for k in range(6): w = (x1 - x0 + .5) * (1 - k / 6); t.box(light, (x0 + x1) / 2 - w / 2, y1 + .18 + k * .07, (x0 + x1) / 2 + w / 2, y1 + .25 + k * .07, 0, .1, bev=0)
                t.box(light, x0 - .25, y1 + .13, x1 + .25, y1 + .2, 0, .12, bev=.01)
            elif hood == 'flat': t.box(light, x0 - .25, y1 + .14, x1 + .25, y1 + .32, 0, .14, bev=.02)
            else:
                for a in range(9): ang = math.pi * (.15 + .7 * a / 8); r = .9; cx, cy = 1.6, y1 - .45; t.beam(light, cx + math.cos(ang) * r, cy + math.sin(ang) * r, cx + math.cos(ang) * (r + .18), cy + math.sin(ang) * (r + .18), .2, 0, .08)
            t.box(light, x0, y0 - .7, x1, y0 - .16, 0, .03)
    _mk(i, wc, hood)

@tile('bl_shop', 3.2, 4.0)
def _(t, W, H, rnd):  # 1階: 粗い石積み(ルスティカ)と大きな窓
    t.wall(mat('ashlar', '#a8a294'), W, H)
    window(t, .35, .5, W - .35, 3.2, mat('metal', '#26282a'), mat('glass', '#2e383e'), cross=False, depth=.22, fw=.06)
    t.box(mat('metal', '#26282a'), W / 2 - .03, .5, W / 2 + .03, 3.2, -.22, -.18); t.box(mat('metal', '#26282a'), .35, 2.6, W - .35, 2.65, -.22, -.18)
    t.box(mat('ashlar', '#bcb6a8'), -W, 3.55, 2 * W, 3.85, 0, .14, bev=.02)

@tile('bl_mod', 3.2, 3.4)
def _(t, W, H, rnd):  # パリ広場まわりの新しい石張りの建物: 深い彫りの縦長窓
    t.wall(mat('ashlar', '#d6cdb8'), W, H)
    window(t, .9, .4, 2.3, 2.9, mat('metal', '#5a5a58'), mat('glass', '#3a464e'), cross=False, depth=.35, fw=.05)
    t.box(mat('metal', '#5a5a58'), .9, 1.0, 2.3, 1.04, -.35, -.3)

@tile('oa_shop', 3.2, 3.4)
def _(t, W, H, rnd):  # 大洗の商店: 看板の帯・テント(日よけ)・シャッターの箱・ガラス戸
    t.wall(mat('conc', '#d8d2c4'), W, H)
    t.box(mat('paint', rnd.choice(['#2a5aa8', '#c8302a', '#2a8a5a', '#e0a020'])), -W, 2.5, 2 * W, 3.3, 0, .14, bev=.02)
    t.box(mat('metal', '#9aa0a2'), -W, 2.25, 2 * W, 2.5, 0, .3, bev=.03)
    window(t, .15, .1, W - .15, 2.2, mat('metal', '#b8bcbe'), mat('glass', '#3a444a'), cross=False, depth=.12, fw=.05)
    for k in range(1, 4): x = .15 + (W - .3) * k / 4; t.box(mat('metal', '#b8bcbe'), x - .025, .1, x + .025, 2.2, -.12, -.08)
    t.box(mat('conc', '#a8a49c'), -W, 0, 2 * W, .1, 0, .03)

@tile('oa_old', 3.2, 2.8)
def _(t, W, H, rnd):  # 古い木造の2階: 下見板・格子の引き違い窓・小庇
    t.wall(mat('siding', '#6a4a32'), W, H)
    x0, x1, y0, y1 = .5, 2.7, .7, 2.1
    window(t, x0, y0, x1, y1, mat('wood', '#4a3020'), mat('glass', '#2c3438'), cross=False, depth=.08, fw=.05)
    t.box(mat('wood', '#4a3020'), (x0 + x1) / 2 - .03, y0, (x0 + x1) / 2 + .03, y1, -.08, -.04)
    for k in range(10): x = x0 + .1 + k * (x1 - x0 - .2) / 9; t.box(mat('wood', '#5a3a26'), x - .02, y0 + .05, x + .02, y1 - .05, .04, .08, bev=0)  # 格子
    t.box(mat('metal', '#5a5e62'), -W, 2.3, 2 * W, 2.4, 0, .5, bev=.01)
    t.box(mat('plaster', '#e8e2d4'), -W, 0, 2 * W, .3, 0, .02)

@tile('tc_stone', 3.2, 3.0)
def _(t, W, H, rnd):  # トスカーナの石の家: 不揃いな石積み・緑のよろい戸・石の窓枠
    t.wall(mat('ashlar', '#c4ac84'), W, H)
    x0, x1, y0, y1 = 1.1, 2.1, .7, 2.3
    ring(t, mat('ashlar', '#d8c8a8'), x0, y0, x1, y1, .12, 0, .04)
    window(t, x0, y0, x1, y1, mat('wood', '#5a4632'), mat('glass', '#2c3438'), cross=True, depth=.2, fw=.06, hbar=.6)
    shutters(t, mat('wood', '#4a5a3a'), x0, y0, x1, y1)

@tile('iq_conc', 3.2, 3.0)
def _(t, W, H, rnd):  # イラク/クウェートの平屋根の家・役所: 砂色の漆喰・鉄格子の窓・水平の庇
    t.wall(mat('plaster', '#d2c09a'), W, H)
    x0, x1, y0, y1 = .9, 2.3, .9, 2.2
    window(t, x0, y0, x1, y1, mat('metal', '#5a5048'), mat('glass', '#38403e'), cross=False, depth=.14, fw=.05)
    for k in range(7): x = x0 + .1 + k * (x1 - x0 - .2) / 6; t.box(mat('metal', '#3a3430'), x - .015, y0, x + .015, y1, .02, .05, bev=0)
    t.box(mat('conc', '#c8b690'), x0 - .3, y1 + .05, x1 + .3, y1 + .15, 0, .45, bev=.01)
    t.box(mat('plaster', '#c4b28e'), -W, 0, 2 * W, .25, 0, .03)

# ---------------------------------------------------------------- 描画
def render(name, out):
    W, H, f = TILES[name]
    for o in list(bpy.data.objects): bpy.data.objects.remove(o)
    for c in (bpy.data.meshes, bpy.data.materials): [c.remove(b) for b in list(c)]
    MATS.clear()
    t = T(); f(t, W, H, random.Random(hash(name) & 9999))
    # 壁に開口をくり抜く(隣の区画の分も)
    for w in t.walls:
        for (x0, y0, x1, y1, d, ar) in t.holes:
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    c = T(); o = (c.arch(mat('paint', '#000000'), x0 + dx * W, x1 + dx * W, y0 + dy * H, y1 + dy * H, -d - .01, .05) if ar else
                                  c.box(mat('paint', '#000000'), x0 + dx * W, y0 + dy * H, x1 + dx * W, y1 + dy * H, -d - .01, .05, bev=0))
                    b = w.modifiers.new('h', 'BOOLEAN'); b.object = o; b.operation = 'DIFFERENCE'; b.solver = 'EXACT'; o.hide_render = True
    # 左右・上下に同じ区画を並べる(端の陰影と形をつなげるため)
    base = [o for o in t.objs if o not in t.walls]
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            if dx == 0 and dy == 0: continue
            for o in base:
                if o.dimensions.x > W * 2.5: continue  # 壁の大板は1枚で足りる
                c = o.copy(); c.data = o.data; c.location = Vector((dx * W, 0, dy * H)); bpy.context.scene.collection.objects.link(c)
    sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'
    cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); sc.collection.objects.link(cam); sc.camera = cam
    cam.data.type = 'ORTHO'; cam.data.ortho_scale = max(W, H); cam.location = (W / 2, -5, H / 2); cam.rotation_euler = (math.pi / 2, 0, 0)
    sc.render.resolution_x = int(W * PXU); sc.render.resolution_y = int(H * PXU); sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'OPEN_EXR'; sc.render.image_settings.color_depth = '32'; sc.view_settings.view_transform = 'Standard'
    sc.render.filter_size = 1.2; sc.cycles.use_denoising = False
    res = {}
    for mode, spp in (('alb', 48), ('nrm', 16)):
        set_mode(mode); sc.cycles.samples = spp; p = os.path.join(out, '_tmp.exr'); sc.render.filepath = p; bpy.ops.render.render(write_still=True)
        im = bpy.data.images.load(p); a = np.array(im.pixels[:], np.float32).reshape(im.size[1], im.size[0], 4)[::-1, :, :3]; bpy.data.images.remove(im)
        if mode == 'alb': a = np.clip(a, 0, 1) ** (1 / 2.2)
        res[mode] = (np.clip(a, 0, 1) * 255 + .5).astype(np.uint8)
    np.save(os.path.join(out, name + '_a.npy'), res['alb']); np.save(os.path.join(out, name + '_n.npy'), res['nrm'])   # 画像化は pack_tiles.py で
    os.remove(os.path.join(out, '_tmp.exr'))
    return dict(w=W, h=H)

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True); meta = {}
    jp = os.path.join(OUT, 'tiles.json')
    if os.path.exists(jp): meta = json.load(open(jp))
    for n in (ONLY or list(TILES.keys())): meta[n] = render(n, OUT); print(n, meta[n])
    json.dump(meta, open(jp, 'w'))
