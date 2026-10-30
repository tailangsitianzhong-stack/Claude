# -*- coding: utf-8 -*-
"""
TANK 3D の戦車モデルを Blender(bpy)で生成し、ゲーム用の軽量データに書き出す。

  python tools/tank_models.py <出力ディレクトリ> [車種...]

- 形はゲームと同じ座標系(x=右, y=上, z=前, 1unit≒1.3m)で記述し、Blender 内では (x, z, y) に置き換える
- 全部品にベベル(面取り)をかけ、角度で法線を分けて稜線に光が乗るようにする
- 塗装部品は UV を自動展開し、迷彩・AO(陰影)・エッジの塗装剥げ・砂埃・汚れ筋を Cycles でテクスチャに焼き込む
- 部品は (hull / turret / gun) × 素材 ごとに結合し、転輪類は原型+配置位置として書き出す
出力: <id>.bin(頂点・インデックス) + <id>.json(構成) + <id>_paint.png(焼き込みテクスチャ)
"""
import bpy, bmesh, math, json, os, sys
import numpy as np
from mathutils import Vector, Matrix, Euler

OUT = sys.argv[1] if len(sys.argv) > 1 else '.'
ONLY = sys.argv[2:]
TEX = 1024

def G(x, y, z):  # ゲーム座標 → Blender座標
    return Vector((x, z, y))

# ---------------------------------------------------------------- 部品の生成
class Kit:
    def __init__(s):
        s.objs = []          # (obj, part, mat)
        s.wheels = []        # (proto, side, (x,y,z), r)
        s.protos = {}        # proto名 -> [(obj, mat)]
        s.tracks = []        # (obj, side)
    def _add(s, me, part, mat, bev, seg=1, sharp=40):
        o = bpy.data.objects.new('p', me)
        bpy.context.scene.collection.objects.link(o)
        if bev > 0:
            m = o.modifiers.new('bev', 'BEVEL'); m.width = bev; m.segments = seg; m.limit_method = 'ANGLE'; m.angle_limit = math.radians(30)
            m.harden_normals = False
        s.objs.append((o, part, mat))
        return o
    def box(s, part, mat, w, h, d, x, y, z, yaw=0, pitch=0, roll=0, bev=.025, seg=1):
        bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1)
        bmesh.ops.scale(bm, vec=Vector((w, d, h)), verts=bm.verts)
        R = Euler((pitch, roll, -yaw), 'YXZ').to_matrix().to_4x4()
        bmesh.ops.transform(bm, matrix=R, verts=bm.verts)
        bmesh.ops.translate(bm, vec=G(x, y, z), verts=bm.verts)
        me = bpy.data.meshes.new('b'); bm.to_mesh(me); bm.free()
        return s._add(me, part, mat, min(bev, w * .3, h * .3, d * .3), seg)
    def prism(s, part, mat, pts, a0, a1, axis, bev=.035, seg=2):
        bm = bmesh.new()
        if axis == 'x': P0 = [G(a0, v, u) for u, v in pts]; dv = G(a1 - a0, 0, 0)
        else: P0 = [G(u, a0, v) for u, v in pts]; dv = G(0, a1 - a0, 0)
        vs = [bm.verts.new(p) for p in P0]; f = bm.faces.new(vs)
        r = bmesh.ops.extrude_face_region(bm, geom=[f])
        bmesh.ops.translate(bm, vec=dv, verts=[e for e in r['geom'] if isinstance(e, bmesh.types.BMVert)])
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        me = bpy.data.meshes.new('pr'); bm.to_mesh(me); bm.free()
        return s._add(me, part, mat, bev, seg)
    def cyl(s, part, mat, d, L, x, y, z, axis='z', segs=16, bev=.012, d2=None, cap=True):
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=cap, segments=segs, radius1=d / 2, radius2=(d2 if d2 is not None else d) / 2, depth=L)
        # create_cone は Blender Z 軸(=ゲームy)向き。指定軸へ向ける
        if isinstance(axis, str):
            av = {'x': G(1, 0, 0), 'y': G(0, 1, 0), 'z': G(0, 0, 1)}[axis]
        else: av = G(*axis).normalized()
        R = Vector((0, 0, 1)).rotation_difference(av).to_matrix().to_4x4()
        bmesh.ops.transform(bm, matrix=R, verts=bm.verts)
        bmesh.ops.translate(bm, vec=G(x, y, z), verts=bm.verts)
        me = bpy.data.meshes.new('c'); bm.to_mesh(me); bm.free()
        return s._add(me, part, mat, min(bev, d * .2), 1)
    def tube(s, part, mat, pts, r, res=6):  # ワイヤー・手すり
        cu = bpy.data.curves.new('cv', 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = r; cu.bevel_resolution = 1
        sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
        for i, p in enumerate(pts): sp.points[i].co = (*G(*p), 1)
        o = bpy.data.objects.new('cv', cu); bpy.context.scene.collection.objects.link(o)
        dg = bpy.context.evaluated_depsgraph_get(); me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
        bpy.data.objects.remove(o)
        return s._add(me, part, mat, 0)
    def bolts(s, part, mat, pts, axis, r=.028, L=.05):
        for p in pts: s.cyl(part, mat, r * 2, L, *p, axis=axis, segs=6, bev=0)
    def seg(s, part, mat, w, h, z1, y1, z2, y2, x, bev=.02):
        d = math.hypot(z2 - z1, y2 - y1)
        return s.box(part, mat, w, h, d, x, (y1 + y2) / 2, (z1 + z2) / 2, pitch=math.atan2(y2 - y1, z2 - z1), bev=bev)

# ---------------------------------------------------------------- 共通部品
def wheel_protos(k, rd):
    """転輪(ゴム2枚+塗装ハブ+ボルト)・起動輪(歯付き)・誘導輪・上部転輪の原型。軸はゲームx"""
    P = {}
    def proto(name, build):
        before = len(k.objs); build(); P[name] = k.objs[before:]; del k.objs[before:]
    def road():
        for sx in (-.13, .13): k.cyl('w', 'rubber', rd, .17, sx, 0, 0, 'x', 24, .02)
        k.cyl('w', 'paintS', rd * .82, .1, 0, 0, 0, 'x', 24, .01)
        for sx in (-.22, .22):
            k.cyl('w', 'paintS', rd * .6, .03, sx, 0, 0, 'x', 20, .008)
            k.bolts('w', 'steel', [(sx + .02 * (1 if sx > 0 else -1), math.sin(a) * rd * .2, math.cos(a) * rd * .2) for a in [i * math.pi / 4 for i in range(8)]], 'x', .018, .03)
            k.cyl('w', 'steel', rd * .18, .06, sx * 1.1, 0, 0, 'x', 12, .006)
    def sprocket():
        for sx in (-.14, .14):
            k.cyl('w', 'steel', .56, .07, sx, 0, 0, 'x', 24, .008)
            for i in range(12):
                a = i * math.pi / 6
                k.box('w', 'steel', .07, .1, .1, sx, math.sin(a) * .31, math.cos(a) * .31, pitch=-a, bev=.01)
        k.cyl('w', 'paintS', .34, .4, 0, 0, 0, 'x', 16, .02)
        k.cyl('w', 'steel', .16, .5, 0, 0, 0, 'x', 10, .01)
    def idler():
        for sx in (-.13, .13): k.cyl('w', 'steel', .56, .12, sx, 0, 0, 'x', 24, .012)
        k.cyl('w', 'paintS', .3, .42, 0, 0, 0, 'x', 16, .015)
        for sx in (-.2, .2):
            for i in range(5):
                a = i * math.pi * 2 / 5
                k.box('w', 'steel', .03, .05, .2, sx, math.sin(a) * .13, math.cos(a) * .13, pitch=-a, bev=.006)
    def roller():
        k.cyl('w', 'rubber', .2, .26, 0, 0, 0, 'x', 14, .02); k.cyl('w', 'steel', .08, .32, 0, 0, 0, 'x', 8, .005)
    proto('road', road); proto('sprocket', sprocket); proto('idler', idler); proto('roller', roller)
    k.protos.update(P)

def gear(k, sd, g):
    """片側の走行装置。g: x, n, z0, dz, rd, drv(z,y), idl(z,y), top, rol"""
    x = sd * g['x']; yw = g['rd'] / 2 + .09
    zs = [g['z0'] - i * g['dz'] for i in range(g['n'])]
    for z in zs: k.wheels.append(('road', sd, (x, yw, z), g['rd'] / 2))
    k.wheels.append(('sprocket', sd, (x, g['drv'][1], g['drv'][0]), .33))
    k.wheels.append(('idler', sd, (x, g['idl'][1], g['idl'][0]), .28))
    for z in g.get('rol', []): k.wheels.append(('roller', sd, (x, g['top'] - .1, z), .1))
    # 履帯: 転輪の下・前後の誘導輪/起動輪を回り込み・上部を通る輪の形に、断面をなぞって押し出す
    (dz_, dy), (iz, iy) = g['drv'], g['idl']
    F, Bk = (iz, iy, .28) if iz > dz_ else (dz_, dy, .33), (dz_, dy, .33) if iz > dz_ else (iz, iy, .28)
    pts = []
    zf, zb = max(zs), min(zs)
    pts += [(zb - .1 + (zf - zb + .2) * t / 6, .045) for t in range(7)]
    def arc(cz, cy, r, a0, a1, n=8):
        return [(cz + math.sin(a0 + (a1 - a0) * t / n) * (r + .05), cy - math.cos(a0 + (a1 - a0) * t / n) * (r + .05)) for t in range(n + 1)]
    # 前側: 接地面→前輪の下を回って上へ
    pts += arc(F[0], F[1], F[2], -.2, math.pi, 10)[1:]
    pts += [(F[0] + (Bk[0] - F[0]) * t / 6, g['top'] + .04 - .03 * math.sin(math.pi * t / 6)) for t in range(1, 6)]
    pts += arc(Bk[0], Bk[1], Bk[2], math.pi, 2 * math.pi + .2, 10)
    # 断面(幅 .56, 厚み .09)を輪に沿って押し出す
    bm = bmesh.new(); uv = bm.loops.layers.uv.new(); ring = []; L = 0; prev = None; vs = []
    for i, (z, y) in enumerate(pts):
        if prev: L += math.hypot(z - prev[0], y - prev[1])
        prev = (z, y); vs.append(L)
        ring.append([bm.verts.new(G(x + a, y + b, z)) for a, b in ((-.28, -.045), (.28, -.045), (.28, .045), (-.28, .045))])
    n = len(ring); Lt = L + math.hypot(pts[0][0] - pts[-1][0], pts[0][1] - pts[-1][1])
    for i in range(n):
        j = (i + 1) % n; v0 = vs[i] / 1.25; v1 = (vs[j] if j else Lt) / 1.25
        for e in range(4):
            q = (ring[i][e], ring[j][e], ring[j][(e + 1) % 4], ring[i][(e + 1) % 4])
            f = bm.faces.new(q)
            u0, u1 = (e / 4, (e + 1) / 4)
            for l, (uu, vv) in zip(f.loops, ((u0, v0), (u0, v1), (u1, v1), (u1, v0))): l[uv].uv = (uu, vv)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new('tr'); bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new('track', me); bpy.context.scene.collection.objects.link(o)
    k.tracks.append((o, sd))

def skirts(k, sd, x, y, h, z0, z1, n, heavy, bolt=True):
    L = (z1 - z0) / n
    for i in range(n):
        hv = i >= n - heavy; z = z0 + (i + .5) * L; t = .2 if hv else .06
        k.box('hull', 'paint', t, h + (.12 if hv else 0), L - .04, sd * (x + (.05 if hv else 0)), y - (.04 if hv else 0), z, bev=.02)
        if bolt:
            xx = sd * (x + (.05 if hv else 0) + t / 2)
            k.bolts('hull', 'paint', [(xx, y + (h / 2 - .06), z + d) for d in (-L / 2 + .1, 0, L / 2 - .1)] + [(xx, y - (h / 2 - .06), z + d) for d in (-L / 2 + .1, L / 2 - .1)], 'x', .02, .03)
    k.box('hull', 'rubber', .05, .1, z1 - z0, sd * x, y - h / 2 - .05, (z0 + z1) / 2, bev=.01)  # 下端のゴムフラップ

def smoke(k, part, sd, x, y, z, n, rows=1):
    for r in range(rows):
        for i in range(n):
            k.cyl(part, 'steel', .1, .3, sd * x, y + r * .12, z + i * .12, axis=(sd * .7, .5, .45), segs=10, bev=.008)
            k.cyl(part, 'steel', .07, .02, sd * (x + .14), y + .1 + r * .12, z + i * .12 + .09, axis=(sd * .7, .5, .45), segs=8, bev=0)

def tools(k, sd, x, z0, y):  # 車体側面の工具(シャベル・つるはし)とワイヤー
    k.box('hull', 'steel', .04, .05, .9, sd * x, y, z0, bev=.01); k.box('hull', 'steel', .05, .18, .22, sd * x, y, z0 + .55, bev=.01)
    k.box('hull', 'steel', .04, .04, .8, sd * x, y - .14, z0 - 1.1, bev=.01); k.box('hull', 'steel', .05, .28, .05, sd * x, y - .14, z0 - .72, bev=.01)
    k.tube('hull', 'steel', [(sd * x, y + .1, z0 - 1.8), (sd * x, y + .12, z0 - .6), (sd * x, y + .1, z0 + .9)], .025)

# ---------------------------------------------------------------- 車種
def leo(k):
    k.prism('hull', 'paint', [(-2.85, .45), (2.55, .45), (3.0, 1.12), (-2.95, 1.12)], -.92, .92, 'x')
    k.prism('hull', 'paint', [(-2.98, 1.1), (2.9, 1.1), (3.02, 1.2), (2.15, 1.45), (-2.98, 1.45)], -1.5, 1.5, 'x')
    k.box('hull', 'steel', 2.5, .05, .9, 0, 1.47, -2.3)
    for sd in (-1, 1):
        for i in range(7): k.box('hull', 'steel', .55, .03, .07, sd * .85, 1.48, -1.3 - i * .18, bev=.008)
        k.box('hull', 'glass', .22, .12, .05, sd * 1.25, 1.22, 3.0, bev=.01); k.box('hull', 'steel', .3, .2, .04, sd * 1.25, 1.22, 3.04, bev=.008)
        k.box('hull', 'steel', .16, .16, .22, sd * .6, .62, 2.86, bev=.02)
        k.box('hull', 'white', .55, .38, .04, sd * 1.18, 1.0, 2.99, pitch=-.45, bev=.008)
        for dx in (-.18, 0, .18): k.box('hull', 'red', .09, .38, .05, sd * 1.18 + dx, 1.0, 3.0, pitch=-.45, bev=.004)
        k.box('hull', 'paint', .5, .32, .28, sd * .95, 1.2, -3.06)
        k.box('hull', 'rubber', .5, .4, .03, sd * 1.2, .55, -3.1, bev=.005)
        skirts(k, sd, 1.51, .86, .62, -2.9, 2.75, 8, 3)
        tools(k, sd, 1.52, .5, 1.27)
        gear(k, sd, dict(x=1.2, n=7, z0=1.95, dz=.65, rd=.66, drv=(-2.75, .56), idl=(2.68, .47), top=.92, rol=[-1.4, 0, 1.4]))
    k.box('hull', 'glass', .5, .05, .18, -.5, 1.47, 2.0, bev=.01); k.cyl('hull', 'paint', .62, .07, -.5, 1.47, 1.6, 'y', 20)
    k.tube('hull', 'steel', [(-.9, 1.47, -2.95), (-.9, 1.6, -3.0), (.9, 1.6, -3.0), (.9, 1.47, -2.95)], .025)
    # 砲塔
    T = 'turret'
    k.prism(T, 'paint', [(-1.12, -1.5), (1.12, -1.5), (1.2, .85), (-1.2, .85)], 0, .74, 'y')
    k.prism(T, 'paint', [(-1.04, -2.6), (1.04, -2.6), (1.1, -1.45), (-1.1, -1.45)], .08, .7, 'y')
    k.prism(T, 'paint', [(-1.22, .83), (-.36, .83), (-.36, 1.95), (-1.22, 1.05)], .02, .76, 'y', .04)
    k.prism(T, 'paint', [(1.22, .83), (.36, .83), (.36, 1.95), (1.22, 1.05)], .02, .76, 'y', .04)
    k.box(T, 'paint', 2.18, .05, 2.25, 0, .76, -.32); k.box(T, 'paint', 1.95, .05, 1.05, 0, .72, -2.05)
    for sd in (-1, 1):
        k.box(T, 'paint', .07, .62, 2.0, sd * 1.24, .38, -.25)
        for i in range(9): k.box(T, 'paint', .05, .6, .05, sd * 1.29, .38, -1.15 + i * .22, bev=.012)
        smoke(k, T, sd, 1.05, .84, -.85, 4)
        for i in range(5): k.box(T, 'steel', .03, .3, .03, sd * 1.06, .55, -2.6 + i * .25, bev=.004)
        k.box(T, 'steel', .03, .03, 1.1, sd * 1.06, .7, -2.1, bev=.004)
        k.cyl(T, 'steel', .05, 1.6, sd * .8, 1.5, -2.35, 'y', 6, 0); k.cyl(T, 'steel', .12, .1, sd * .8, .75, -2.35, 'y', 10)
        k.tube(T, 'steel', [(sd * 1.15, .55, .3), (sd * 1.18, .6, .5), (sd * 1.15, .55, .7)], .02)
    k.box(T, 'steel', 2.0, .03, .03, 0, .7, -2.9, bev=.004)
    for i in range(7): k.box(T, 'steel', .03, .3, .03, -.9 + i * .3, .55, -2.9, bev=.004)
    k.box(T, 'paint', .8, .25, .4, -.4, .45, -2.75); k.box(T, 'paint', .6, .2, .35, .45, .42, -2.72)
    k.box(T, 'paint', .42, .34, .62, .62, .92, .42); k.box(T, 'glass', .34, .18, .03, .62, .94, .74, bev=.008)
    k.box(T, 'paint', .38, .06, .3, .62, 1.11, .55, bev=.01)
    k.cyl(T, 'paint', .3, .28, -.6, .92, -.3, 'y', 18); k.box(T, 'paint', .32, .3, .4, -.6, 1.2, -.3); k.box(T, 'glass', .26, .14, .03, -.6, 1.22, -.09, bev=.006)
    k.cyl(T, 'steel', .5, .12, .35, .82, -1.0, 'y', 20); k.box(T, 'paint', .34, .3, .42, .35, 1.02, -1.0); k.cyl(T, 'steel', .06, .8, .35, 1.05, -.45, 'z', 8); k.box(T, 'glass', .1, .1, .03, .35, 1.0, -.78, bev=.005)
    k.cyl(T, 'paint', .6, .06, -.55, .8, -.85, 'y', 20); k.cyl(T, 'paint', .55, .06, .5, .8, -.15, 'y', 20)
    for p in [(-.55, .84, -.6), (.5, .84, .1)]: k.tube(T, 'steel', [(p[0] - .15, p[1], p[2]), (p[0] - .15, p[1] + .08, p[2]), (p[0] + .15, p[1] + .08, p[2]), (p[0] + .15, p[1], p[2])], .015)
    k.box(T, 'paint', .66, .6, .5, 0, .45, 1.12)
    # 砲
    Gn = 'gun'; L = 5.2
    k.box(Gn, 'paint', .5, .42, .4, 0, 0, .25); k.cyl(Gn, 'steel', .16, L, 0, 0, L / 2, 'z', 16)
    for i, (a, b) in enumerate([(.4, 1.7), (1.75, 2.9), (3.55, 4.55), (4.6, 5.0)]):
        k.cyl(Gn, 'paint', .21, b - a, 0, 0, (a + b) / 2, 'z', 20); k.cyl(Gn, 'steel', .22, .03, 0, 0, b, 'z', 20, 0)
    k.cyl(Gn, 'paint', .28, .6, 0, 0, 3.22, 'z', 20, .02, d2=None); k.cyl(Gn, 'steel', .19, .12, 0, 0, 5.12, 'z', 16)
    k.box(Gn, 'steel', .08, .08, .14, 0, .14, 5.0, bev=.01)
    return dict(tur=(0, 1.45, .1), gun=(0, .47, 1.05), len=L)

def mk4(k):
    k.prism('hull', 'paint', [(-2.85, .45), (2.5, .45), (3.0, 1.02), (-2.95, 1.25)], -.95, .95, 'x')
    k.prism('hull', 'paint', [(-2.98, 1.1), (2.88, 1.0), (3.04, 1.08), (.35, 1.58), (-1.55, 1.58), (-2.98, 1.28)], -1.46, 1.46, 'x')
    for i in range(8):
        z = .7 + i * .25; y = 1.58 - (z - .35) * .185 + .02
        k.seg('hull', 'steel', 2.0, .03, z, y, z + .18, y - .02, 0, bev=.008)
    k.box('hull', 'steel', 1.1, .75, .06, 0, .8, -2.97); k.box('hull', 'paint', .05, .7, .07, 0, .8, -2.99, bev=.01)
    k.tube('hull', 'steel', [(-.45, .75, -3.02), (-.45, .85, -3.06), (-.25, .85, -3.06), (-.25, .75, -3.02)], .02)
    for sd in (-1, 1):
        k.box('hull', 'glass', .3, .12, .05, sd * 1.1, 1.05, 3.04, bev=.01); k.box('hull', 'steel', .16, .16, .22, sd * .55, .6, 2.88, bev=.02)
        k.box('hull', 'paint', .6, .4, .3, sd * 1.0, 1.2, -2.98)
        skirts(k, sd, 1.5, .85, .66, -2.85, 2.9, 6, 2)
        tools(k, sd, 1.52, -.2, 1.3)
        gear(k, sd, dict(x=1.2, n=6, z0=2.0, dz=.8, rd=.66, drv=(2.75, .56), idl=(-2.72, .47), top=.92, rol=[-1.2, .2, 1.6]))
    k.box('hull', 'glass', .5, .05, .16, -.55, 1.55, .9, pitch=.2, bev=.01)
    T = 'turret'
    k.prism(T, 'paint', [(-1.2, -2.25), (1.2, -2.25), (1.32, -.2), (.42, 2.4), (-.42, 2.4), (-1.32, -.2)], 0, .5, 'y', .05)
    k.prism(T, 'paint', [(-1.0, -2.1), (1.0, -2.1), (1.1, -.25), (.3, 2.0), (-.3, 2.0), (-1.1, -.25)], .5, .68, 'y', .05)
    n = 15
    for i in range(n):
        x = -1.1 + i * 2.2 / (n - 1)
        for j in range(4): k.cyl(T, 'steel', .045, .1, x, -.06 - j * .1, -2.2, 'y', 6, 0)
        k.cyl(T, 'steel', .14, .14, x, -.5, -2.2, 'y', 8, .02)
    k.box(T, 'steel', 2.3, .05, .05, 0, -.02, -2.2, bev=.01)
    for sd in (-1, 1):
        k.box(T, 'paint', .08, .34, .58, sd * 1.18, .32, .35, yaw=sd * .35); k.box(T, 'glass', .03, .27, .46, sd * 1.22, .32, .36, yaw=sd * .35, bev=.005)
        k.box(T, 'paint', .3, .3, .45, sd * .95, .64, -1.15); k.box(T, 'steel', .2, .12, .3, sd * .95, .84, -1.15)
        smoke(k, T, sd, .95, .6, -.3, 3)
        k.box(T, 'paint', .06, .45, 1.6, sd * 1.25, .25, -1.3)
    k.cyl(T, 'paint', .5, .14, -.55, .72, -.75, 'y', 20); k.box(T, 'paint', .3, .28, .36, -.55, .92, -.75); k.box(T, 'glass', .24, .12, .03, -.55, .94, -.56, bev=.006)
    k.box(T, 'paint', .34, .26, .42, .5, .8, .3); k.box(T, 'glass', .26, .14, .03, .5, .82, .52, bev=.006)
    k.cyl(T, 'steel', .13, .7, .75, .85, -1.3, (0, .9, .45), 12); k.cyl(T, 'steel', .05, .7, -.2, .92, -.55, 'z', 8)
    k.cyl(T, 'steel', .04, 1.5, -.9, 1.4, -1.9, 'y', 6, 0)
    Gn = 'gun'; L = 4.3
    k.box(Gn, 'paint', .42, .34, .5, 0, 0, .1); k.cyl(Gn, 'steel', .16, L, 0, 0, L / 2, 'z', 16)
    for (a, b) in [(.5, 1.6), (1.65, 2.75), (2.8, 3.9)]:
        k.cyl(Gn, 'paint', .22, b - a, 0, 0, (a + b) / 2, 'z', 20); k.cyl(Gn, 'steel', .23, .03, 0, 0, b, 'z', 20, 0)
    k.cyl(Gn, 'steel', .19, .14, 0, 0, L + .05, 'z', 16)
    return dict(tur=(0, 1.58, -.55), gun=(0, .36, 1.75), len=L)

def t10(k):
    k.prism('hull', 'paint', [(-2.68, .42), (2.4, .42), (2.8, 1.0), (-2.72, 1.05)], -.85, .85, 'x')
    k.prism('hull', 'paint', [(-2.72, 1.0), (2.65, .98), (2.8, 1.06), (2.0, 1.35), (-2.72, 1.35)], -1.26, 1.26, 'x')
    k.box('hull', 'steel', 2.0, .04, 1.1, 0, 1.37, -1.9)
    for i in range(6): k.box('hull', 'steel', 2.0, .03, .06, 0, 1.39, -1.4 - i * .17, bev=.006)
    k.box('hull', 'glass', .5, .05, .16, 0, 1.37, 1.85, bev=.01); k.cyl('hull', 'paint', .55, .06, 0, 1.36, 1.5, 'y', 18)
    for sd in (-1, 1):
        k.box('hull', 'glass', .22, .12, .05, sd * .95, 1.1, 2.8, bev=.01); k.box('hull', 'steel', .3, .2, .04, sd * .95, 1.1, 2.84, bev=.008)
        k.box('hull', 'steel', .14, .14, .2, sd * .5, .58, 2.68, bev=.02)
        skirts(k, sd, 1.27, .82, .6, -2.6, 2.7, 5, 1)
        tools(k, sd, 1.28, .3, 1.2)
        gear(k, sd, dict(x=1.0, n=5, z0=1.72, dz=.86, rd=.72, drv=(-2.52, .56), idl=(2.5, .48), top=.92, rol=[-.85, .85]))
    T = 'turret'
    k.prism(T, 'paint', [(-.98, -2.45), (.98, -2.45), (1.08, -.8), (1.14, .85), (.55, 1.5), (-.55, 1.5), (-1.14, .85), (-1.08, -.8)], 0, .6, 'y', .04)
    k.prism(T, 'paint', [(-.9, -2.35), (.9, -2.35), (1.0, -.8), (1.04, .8), (.5, 1.38), (-.5, 1.38), (-1.04, .8), (-1.0, -.8)], .6, .68, 'y', .03)
    for sd in (-1, 1):
        k.box(T, 'paint', .62, .56, .14, sd * .84, .3, 1.2, yaw=sd * -.82)
        k.bolts(T, 'paint', [(sd * (.84 + .05 * i), .3 + .2 * j, 1.28) for i in (-1, 1) for j in (-1, 1)], 'z', .02, .04)
        k.box(T, 'paint', .08, .5, 1.6, sd * 1.15, .3, -.05)
        for i in range(4): k.box(T, 'paint', .09, .52, .03, sd * 1.17, .3, -.75 + i * .45, bev=.006)
        smoke(k, T, sd, 1.1, .5, .45, 4)
        k.box(T, 'glass', .08, .08, .08, sd * 1.0, .68, 1.1, bev=.01); k.box(T, 'glass', .08, .08, .08, sd * .9, .68, -2.3, bev=.01)
        for i in range(4): k.box(T, 'steel', .03, .28, .03, sd * .95, .5, -2.4 + i * .3, bev=.004)
    k.cyl(T, 'paint', .2, .36, .58, .86, .35, 'y', 14); k.box(T, 'paint', .32, .28, .32, .58, 1.16, .35); k.box(T, 'glass', .24, .12, .03, .58, 1.18, .52, bev=.006)
    k.box(T, 'paint', .34, .26, .42, -.55, .8, .7); k.box(T, 'glass', .26, .12, .03, -.55, .82, .92, bev=.006)
    k.cyl(T, 'paint', .45, .08, -.45, .72, -.6, 'y', 18); k.cyl(T, 'steel', .07, .9, -.45, .95, -.3, 'z', 8); k.box(T, 'steel', .14, .14, .3, -.45, .95, -.75, bev=.01)
    k.cyl(T, 'steel', .04, 1.4, .8, 1.3, -2.1, 'y', 6, 0)
    Gn = 'gun'; L = 4.15
    k.box(Gn, 'paint', .46, .38, .36, 0, 0, .15); k.cyl(Gn, 'steel', .15, L, 0, 0, L / 2, 'z', 16)
    for (a, b) in [(.35, 1.5), (1.55, 2.7), (2.75, 3.85)]:
        k.cyl(Gn, 'paint', .2, b - a, 0, 0, (a + b) / 2, 'z', 20); k.cyl(Gn, 'steel', .21, .03, 0, 0, b, 'z', 20, 0)
    k.cyl(Gn, 'steel', .18, .12, 0, 0, L + .04, 'z', 16)
    return dict(tur=(0, 1.35, .15), gun=(0, .36, 1.45), len=L)

def ab(k):
    k.prism('hull', 'paint', [(-2.95, .45), (2.6, .45), (3.1, 1.05), (-3.05, 1.22)], -.95, .95, 'x')
    k.prism('hull', 'paint', [(-3.05, 1.05), (2.95, 1.0), (3.1, 1.07), (2.05, 1.32), (-3.05, 1.32)], -1.42, 1.42, 'x')
    k.box('hull', 'steel', 1.8, .5, .06, 0, .92, -3.07)
    for i in range(7): k.box('hull', 'paint', 1.8, .03, .07, 0, .7 + i * .07, -3.1, bev=.006)
    k.box('hull', 'steel', 2.2, .03, 1.3, 0, 1.34, -2.1)
    for i in range(8): k.box('hull', 'steel', 2.1, .03, .05, 0, 1.36, -1.6 - i * .14, bev=.005)
    k.box('hull', 'glass', .5, .05, .16, 0, 1.34, 2.2, bev=.01); k.cyl('hull', 'paint', .6, .05, 0, 1.33, 1.8, 'y', 18)
    for sd in (-1, 1):
        k.box('hull', 'glass', .2, .12, .05, sd * 1.15, 1.12, 3.1, bev=.01); k.box('hull', 'steel', .3, .2, .04, sd * 1.15, 1.12, 3.13, bev=.008)
        k.box('hull', 'steel', .16, .16, .22, sd * .6, .6, 2.95, bev=.02)
        skirts(k, sd, 1.43, .86, .6, -2.95, 2.95, 7, 2)
        tools(k, sd, 1.44, .2, 1.24)
        gear(k, sd, dict(x=1.12, n=7, z0=2.2, dz=.73, rd=.64, drv=(-2.92, .68), idl=(2.85, .5), top=.95, rol=[-1.1, 1.1]))
    T = 'turret'
    k.prism(T, 'paint', [(-1.2, -2.0), (1.2, -2.0), (1.32, -.4), (1.28, .6), (.75, 1.75), (-.75, 1.75), (-1.28, .6), (-1.32, -.4)], 0, .5, 'y', .04)
    k.prism(T, 'paint', [(-1.12, -1.9), (1.12, -1.9), (1.24, -.4), (1.18, .55), (.62, 1.45), (-.62, 1.45), (-1.18, .55), (-1.24, -.4)], .5, .6, 'y', .03)
    for x in (-1.1, 1.1): k.box(T, 'steel', .04, .45, 1.0, x, .3, -2.5, bev=.006)
    for y in (.1, .52): k.box(T, 'steel', 2.25, .04, .04, 0, y, -3.0, bev=.006)
    for i in range(8): k.box(T, 'steel', .03, .42, .03, -1.05 + i * .3, .31, -3.0, bev=.004)
    k.box(T, 'paint', 1.0, .3, .7, -.45, .25, -2.45); k.cyl(T, 'paint', .32, .9, .55, .25, -2.4, 'x', 14)
    k.box(T, 'paint', .4, .25, .4, .55, .25, -2.8)
    for sd in (-1, 1): smoke(k, T, sd, 1.2, .38, .55, 6, 2)
    k.box(T, 'paint', .42, .3, .5, .62, .72, .95); k.box(T, 'glass', .34, .16, .03, .62, .74, 1.2, bev=.006)
    k.cyl(T, 'paint', .22, .3, -.55, .75, .35, 'y', 14); k.box(T, 'paint', .34, .3, .36, -.55, 1.02, .35); k.box(T, 'glass', .26, .14, .03, -.55, 1.04, .54, bev=.006)
    k.cyl(T, 'steel', .6, .12, .5, .66, -.6, 'y', 20); k.box(T, 'paint', .36, .3, .5, .5, .88, -.6); k.cyl(T, 'steel', .06, .9, .5, .92, -.2, 'z', 8)
    k.cyl(T, 'paint', .55, .06, -.55, .63, -.75, 'y', 18); k.cyl(T, 'steel', .05, .7, -.55, .82, -.45, 'z', 8)
    for sd in (-1, 1): k.cyl(T, 'steel', .04, 1.5, sd * .9, 1.3, -1.8, 'y', 6, 0)
    Gn = 'gun'; L = 4.15
    k.box(Gn, 'paint', .62, .4, .36, 0, 0, .12); k.cyl(Gn, 'steel', .15, L, 0, 0, L / 2, 'z', 16)
    for (a, b) in [(.35, 1.4), (1.45, 2.25), (3.0, 3.95)]:
        k.cyl(Gn, 'paint', .2, b - a, 0, 0, (a + b) / 2, 'z', 20); k.cyl(Gn, 'steel', .21, .03, 0, 0, b, 'z', 20, 0)
    k.cyl(Gn, 'paint', .27, .6, 0, 0, 2.62, 'z', 20, .02); k.cyl(Gn, 'steel', .18, .12, 0, 0, L + .04, 'z', 16)
    k.box(Gn, 'steel', .08, .08, .12, 0, .13, L - .1, bev=.01)
    return dict(tur=(0, 1.32, 0), gun=(0, .33, 1.65), len=L)

TANKS = {'leo': (leo, .66, 'nato'), 'mk4': (mk4, .66, 'sinai'), 't10': (t10, .72, 'jgsdf'), 'ab': (ab, .64, 'tan')}
PAINT = {  # 迷彩の色(リニア色空間)と方式
    'nato': [(.012, .013, .01), (.05, .066, .028), (.11, .068, .03)],
    'sinai': [(.15, .15, .1), (.17, .17, .115), (.16, .16, .11)],
    'jgsdf': [(.04, .055, .025), (.055, .075, .035), (.11, .068, .035)],
    'tan': [(.3, .21, .11), (.34, .25, .13), (.32, .23, .12)],
}

# ---------------------------------------------------------------- 焼き込み用の塗装マテリアル
def paint_material(name, scheme, img):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; N = nt.nodes; L = nt.links
    for n in list(N): N.remove(n)
    out = N.new('ShaderNodeOutputMaterial'); em = N.new('ShaderNodeEmission'); L.new(em.outputs[0], out.inputs['Surface'])
    geo = N.new('ShaderNodeNewGeometry')
    # 迷彩: ワールド座標の3Dノイズ(部品をまたいでも模様がつながる)
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = .55; nz.inputs['Detail'].default_value = 3; nz.inputs['Distortion'].default_value = .6
    L.new(geo.outputs['Position'], nz.inputs['Vector'])
    cr = N.new('ShaderNodeValToRGB'); cr.color_ramp.interpolation = 'CONSTANT'; c = PAINT[scheme]
    cr.color_ramp.elements[0].position = 0; cr.color_ramp.elements[0].color = (*c[0], 1)
    cr.color_ramp.elements[1].position = .45; cr.color_ramp.elements[1].color = (*c[1], 1)
    e = cr.color_ramp.elements.new(.58); e.color = (*c[2], 1)
    L.new(nz.outputs['Fac'], cr.inputs['Fac'])
    base = cr.outputs['Color']
    # 細かい塗装ムラ
    fn = N.new('ShaderNodeTexNoise'); fn.inputs['Scale'].default_value = 18; fn.inputs['Detail'].default_value = 6
    L.new(geo.outputs['Position'], fn.inputs['Vector'])
    fm = N.new('ShaderNodeMapRange'); fm.inputs['To Min'].default_value = .85; fm.inputs['To Max'].default_value = 1.12; L.new(fn.outputs['Fac'], fm.inputs['Value'])
    mv = N.new('ShaderNodeVectorMath'); mv.operation = 'SCALE'; L.new(base, mv.inputs[0]); L.new(fm.outputs[0], mv.inputs['Scale']); base = mv.outputs[0]
    # 砂埃: 下の方と上向きの面ほど砂色に
    sep = N.new('ShaderNodeSeparateXYZ'); L.new(geo.outputs['Position'], sep.inputs[0])
    hgt = N.new('ShaderNodeMapRange'); hgt.inputs['From Min'].default_value = .2; hgt.inputs['From Max'].default_value = 1.3; hgt.inputs['To Min'].default_value = .75; hgt.inputs['To Max'].default_value = 0
    L.new(sep.outputs['Z'], hgt.inputs['Value'])
    nsep = N.new('ShaderNodeSeparateXYZ'); L.new(geo.outputs['Normal'], nsep.inputs[0])
    up = N.new('ShaderNodeMapRange'); up.inputs['From Min'].default_value = .6; up.inputs['From Max'].default_value = 1; up.inputs['To Max'].default_value = .35
    L.new(nsep.outputs['Z'], up.inputs['Value'])
    dn = N.new('ShaderNodeTexNoise'); dn.inputs['Scale'].default_value = 3; L.new(geo.outputs['Position'], dn.inputs['Vector'])
    dm = N.new('ShaderNodeMath'); dm.operation = 'ADD'; L.new(hgt.outputs[0], dm.inputs[0]); L.new(up.outputs[0], dm.inputs[1])
    dmm = N.new('ShaderNodeMath'); dmm.operation = 'MULTIPLY'; dmm.use_clamp = True; L.new(dm.outputs[0], dmm.inputs[0]); L.new(dn.outputs['Fac'], dmm.inputs[1])
    dust = N.new('ShaderNodeMix'); dust.data_type = 'RGBA'; dust.inputs['B'].default_value = (.36, .27, .16, 1)
    L.new(dmm.outputs[0], dust.inputs['Factor']); L.new(base, dust.inputs['A']); base = dust.outputs['Result']
    # 塗装の剥げ: 尖った稜線(pointiness)に金属色を少し出す
    pr = N.new('ShaderNodeMapRange'); pr.inputs['From Min'].default_value = .55; pr.inputs['From Max'].default_value = .62; pr.inputs['To Max'].default_value = .55
    L.new(geo.outputs['Pointiness'], pr.inputs['Value'])
    wn = N.new('ShaderNodeTexNoise'); wn.inputs['Scale'].default_value = 25; L.new(geo.outputs['Position'], wn.inputs['Vector'])
    wm = N.new('ShaderNodeMath'); wm.operation = 'MULTIPLY'; wm.use_clamp = True; L.new(pr.outputs[0], wm.inputs[0]); L.new(wn.outputs['Fac'], wm.inputs[1])
    wear = N.new('ShaderNodeMix'); wear.data_type = 'RGBA'; wear.inputs['B'].default_value = (.12, .11, .1, 1)
    L.new(wm.outputs[0], wear.inputs['Factor']); L.new(base, wear.inputs['A']); base = wear.outputs['Result']
    # 雨だれの汚れ筋(縦に伸びたノイズ)
    sm = N.new('ShaderNodeMapping'); sm.inputs['Scale'].default_value = (6, 6, .5); L.new(geo.outputs['Position'], sm.inputs['Vector'])
    st = N.new('ShaderNodeTexNoise'); st.inputs['Scale'].default_value = 2.5; L.new(sm.outputs[0], st.inputs['Vector'])
    sr = N.new('ShaderNodeMapRange'); sr.inputs['From Min'].default_value = .55; sr.inputs['From Max'].default_value = .8; sr.inputs['To Min'].default_value = 1; sr.inputs['To Max'].default_value = .78
    L.new(st.outputs['Fac'], sr.inputs['Value'])
    ms = N.new('ShaderNodeVectorMath'); ms.operation = 'SCALE'; L.new(base, ms.inputs[0]); L.new(sr.outputs[0], ms.inputs['Scale']); base = ms.outputs[0]
    # AO(凹んだ所・部品の隙間を暗く)
    ao = N.new('ShaderNodeAmbientOcclusion'); ao.samples = 16; ao.inputs['Distance'].default_value = .6
    ar = N.new('ShaderNodeMapRange'); ar.inputs['To Min'].default_value = .35; L.new(ao.outputs['AO'], ar.inputs['Value'])
    ma = N.new('ShaderNodeVectorMath'); ma.operation = 'SCALE'; L.new(base, ma.inputs[0]); L.new(ar.outputs[0], ma.inputs['Scale']); base = ma.outputs[0]
    L.new(base, em.inputs['Color'])
    ti = N.new('ShaderNodeTexImage'); ti.image = img; nt.nodes.active = ti
    return m

# ---------------------------------------------------------------- 書き出し
def mesh_arrays(o, uvs=True):
    """評価済みメッシュ→角ごと(ループ)の位置・法線・UV と三角形インデックス。同一頂点はまとめる"""
    dg = bpy.context.evaluated_depsgraph_get(); oe = o.evaluated_get(dg); me = oe.to_mesh()
    me.calc_loop_triangles()
    nl = len(me.loops)
    co = np.zeros(len(me.vertices) * 3, np.float32); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
    vi = np.zeros(nl, np.int32); me.loops.foreach_get('vertex_index', vi)
    nr = np.zeros(nl * 3, np.float32); me.corner_normals.foreach_get('vector', nr); nr = nr.reshape(-1, 3)
    if uvs and me.uv_layers.active:
        uv = np.zeros(nl * 2, np.float32); me.uv_layers.active.data.foreach_get('uv', uv); uv = uv.reshape(-1, 2)
    else: uv = np.zeros((nl, 2), np.float32)
    tri = np.zeros(len(me.loop_triangles) * 3, np.int32); me.loop_triangles.foreach_get('loops', tri)
    M = np.array(o.matrix_world); pos = co[vi] @ M[:3, :3].T + M[:3, 3]
    nrm = nr @ np.array(o.matrix_world.to_3x3().inverted().transposed()).T
    nrm /= np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-8)
    oe.to_mesh_clear()
    # Blender(x,y,z) → ゲーム(x,z,y)
    pos = pos[:, [0, 2, 1]]; nrm = nrm[:, [0, 2, 1]]
    key = np.round(np.hstack([pos * 2000, nrm * 100, uv * 4000])).astype(np.int64)
    _, first, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    tri = inv.reshape(-1)[tri]
    # 面の向き: Blender(右手系・反時計回り)→ゲーム(左手系)は軸の入れ替えで向きも反転するので、頂点順はそのままでよい
    return pos[first], nrm[first], uv[first], tri

def pack_mesh(buf, pos, nrm, uv, tri, origin=(0, 0, 0)):
    pos = pos - np.array(origin, np.float32)
    lo = pos.min(0); hi = pos.max(0); sc = np.maximum(hi - lo, 1e-6)
    q = np.round((pos - lo) / sc * 65535).astype(np.uint16)
    n8 = np.round(np.clip(nrm, -1, 1) * 127).astype(np.int8)
    ulo = uv.min(0) if len(uv) else np.zeros(2); usc = np.maximum((uv.max(0) - ulo) if len(uv) else np.ones(2), 1e-6)
    uq = np.round((uv - ulo) / usc * 65535).astype(np.uint16)
    big = len(pos) > 65535
    idx = tri.astype(np.uint32 if big else np.uint16)
    info = dict(nv=int(len(pos)), ni=int(len(tri)), lo=lo.tolist(), sc=sc.tolist(), ulo=ulo.tolist(), usc=usc.tolist(), i32=bool(big))
    def put(a):
        while len(buf) % 4: buf.append(0)
        off = len(buf); buf.extend(a.tobytes()); return off
    info['p'] = put(q); info['n'] = put(n8); info['u'] = put(uq); info['i'] = put(idx)
    return info

def build(tid):
    for o in list(bpy.data.objects): bpy.data.objects.remove(o)
    for c in (bpy.data.meshes, bpy.data.materials, bpy.data.images, bpy.data.curves):
        for b in list(c): c.remove(b)
    fn, rd, scheme = TANKS[tid]
    k = Kit(); wheel_protos(k, rd); info = fn(k)
    # 砲塔・砲の部品はそれぞれの基準点からの座標で作ってあるので、組み上がった位置へ移す(AOの焼き込みを正しくするため)
    tv = Vector(info['tur']); gv = tv + Vector(info['gun'])
    for o, part, mat in k.objs:
        if part == 'turret': o.location = G(*tv)
        elif part == 'gun': o.location = G(*gv)
    bpy.context.view_layer.update()
    sc = bpy.context.scene; sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 24
    # 部品×素材ごとに結合(評価済みメッシュ=ベベル適用後を寄せ集める)
    groups = {}
    for o, part, mat in k.objs: groups.setdefault((part, mat), []).append(o)
    dg = bpy.context.evaluated_depsgraph_get(); joined = {}
    for (part, mat), objs in groups.items():
        bm = bmesh.new()
        for o in objs:
            me = o.evaluated_get(dg).to_mesh(); tmp = me.copy(); tmp.transform(o.matrix_world); bm.from_mesh(tmp); bpy.data.meshes.remove(tmp); o.evaluated_get(dg).to_mesh_clear()
        me = bpy.data.meshes.new(f'{part}_{mat}'); bm.to_mesh(me); bm.free()
        me.set_sharp_from_angle(angle=math.radians(35))
        jo = bpy.data.objects.new(f'{part}_{mat}', me); sc.collection.objects.link(jo); joined[(part, mat)] = jo
    for o, _, _ in k.objs: bpy.data.objects.remove(o)
    # 原型(転輪類)も同様に結合
    proto_objs = {}
    for name, lst in k.protos.items():
        per = {}
        for o, part, mat in lst: per.setdefault(mat, []).append(o)
        for mat, objs in per.items():
            bm = bmesh.new()
            for o in objs:
                me = o.evaluated_get(dg).to_mesh(); tmp = me.copy(); tmp.transform(o.matrix_world); bm.from_mesh(tmp); bpy.data.meshes.remove(tmp); o.evaluated_get(dg).to_mesh_clear()
            me = bpy.data.meshes.new(f'{name}_{mat}'); bm.to_mesh(me); bm.free(); me.set_sharp_from_angle(angle=math.radians(35))
            jo = bpy.data.objects.new(f'{name}_{mat}', me); sc.collection.objects.link(jo); proto_objs[(name, mat)] = jo
            for o in objs: bpy.data.objects.remove(o)
    # 塗装部品: UV自動展開(全部品で1枚のテクスチャを共有)→焼き込み
    paint_objs = [o for (part, mat), o in joined.items() if mat == 'paint']
    img = bpy.data.images.new(f'{tid}_paint', TEX, TEX); img.colorspace_settings.name = 'sRGB'
    pm = paint_material('paint', scheme, img)
    bpy.ops.object.select_all(action='DESELECT')
    for o in paint_objs: o.data.materials.append(pm); o.select_set(True)
    bpy.context.view_layer.objects.active = paint_objs[0]
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=.006, scale_to_bounds=False)
    bpy.ops.uv.pack_islands(margin=.004)
    bpy.ops.object.mode_set(mode='OBJECT')
    # 焼き込みは組み上がった姿勢で(砲塔・砲の位置に置いた状態の結合済みメッシュなので AO も正しく入る)
    sc.render.bake.margin = 6
    bpy.ops.object.bake(type='EMIT', margin=6)
    img.filepath_raw = os.path.join(OUT, f'{tid}_paint.png'); img.file_format = 'PNG'; img.save()  # JPEG化は pack_assets.py で行う
    # 書き出し
    buf = bytearray(); out = dict(parts=[], protos={}, wheels=[], tracks=[], tur=info['tur'], gun=info['gun'], len=info['len'])
    tur = np.array(info['tur'], np.float32); gun = tur + np.array(info['gun'], np.float32)
    for (part, mat), o in joined.items():
        pos, nrm, uv, tri = mesh_arrays(o, uvs=(mat == 'paint'))
        org = {'hull': (0, 0, 0), 'turret': tuple(tur), 'gun': tuple(gun)}[part]
        out['parts'].append(dict(part=part, mat=mat, **pack_mesh(buf, pos, nrm, uv, tri, org)))
    for (name, mat), o in proto_objs.items():
        pos, nrm, uv, tri = mesh_arrays(o, uvs=False)
        out['protos'].setdefault(name, []).append(dict(mat=mat, **pack_mesh(buf, pos, nrm, uv, tri)))
    for proto, side, p, r in k.wheels: out['wheels'].append(dict(proto=proto, side=side, pos=list(p), r=r))
    for o, side in k.tracks:
        pos, nrm, uv, tri = mesh_arrays(o, uvs=True)
        out['tracks'].append(dict(side=side, **pack_mesh(buf, pos, nrm, uv, tri)))
    open(os.path.join(OUT, f'{tid}.bin'), 'wb').write(bytes(buf))
    json.dump(out, open(os.path.join(OUT, f'{tid}.json'), 'w'))
    nv = sum(p['nv'] for p in out['parts']); print(tid, 'verts', nv, 'bin', len(buf))

if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    for tid in (ONLY or TANKS.keys()): build(tid)
