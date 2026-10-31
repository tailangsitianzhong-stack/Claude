# -*- coding: utf-8 -*-
"""
小物(prop_models.py / landmark_models.py)の「つながり」検査。Blender(bpy)で各小物を組み立て、部品どうしが接しているかを調べる。

  python tools/check_props.py [小物名...]

- 部品(オブジェクト)どうしが「交差している」か「表面どうしが TOL 以内に近い」ならつながっているとみなす
- つながった部品のかたまりのうち、地面(y≈ground)に届いていないもの = 宙に浮いた部品 → エラー
  (例: 壁から離れた屋根、ハブに付いていない風車の羽根、橋脚が川底に届かない橋)
- 回る部品(pivots)も同じく、本体につながっていなければエラー
出力: 小物ごとに OK / FLOAT(浮いた部品のかたまりの数・位置)
"""
import os, sys, math
sys.argv = [sys.argv[0], '/tmp/_chk'] + sys.argv[1:]
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
import landmark_models  # noqa: F401  (名所の小物も P に登録される)
from prop_models import P, PK, s_cut

TOL = .03
NEAR = .15   # これより近いのにつながっていない部品は「すき間」として報告(脚と蹄など)
ONLY = sys.argv[2:]

def check(name):
    for o in list(bpy.data.objects): bpy.data.objects.remove(o)
    for b in list(bpy.data.meshes): bpy.data.meshes.remove(b)
    s_cut.clear()
    k = PK(); meta = P[name](k) or {}
    ground = meta.get('ground', 0)
    dg = bpy.context.evaluated_depsgraph_get()
    items = []
    for o, part, col in k.objs:
        me = bpy.data.meshes.new_from_object(o.evaluated_get(dg)); me.transform(o.matrix_world)
        if not len(me.vertices): continue
        vs = [v.co.copy() for v in me.vertices]; fs = [tuple(p.vertices) for p in me.polygons]
        lo = Vector(map(min, *vs)) if len(vs) > 1 else vs[0]; hi = Vector(map(max, *vs)) if len(vs) > 1 else vs[0]
        smp = vs + [p.center.copy() for p in me.polygons]           # 頂点だけでなく面の中心も調べる(重ねた箱の角が相手の面の外にある場合)
        items.append(dict(part=part, col=col, vs=vs, smp=smp, tree=BVHTree.FromPolygons(vs, fs, epsilon=TOL), lo=lo, hi=hi))
    n = len(items); par = list(range(n))
    def f(i):
        while par[i] != i: par[i] = par[par[i]]; i = par[i]
        return i
    def near(a, b):
        if any(a['lo'][i] > b['hi'][i] + TOL or b['lo'][i] > a['hi'][i] + TOL for i in range(3)): return False
        if a['tree'].overlap(b['tree']): return True
        for A, B in ((a, b), (b, a)):
            step = max(1, len(A['smp']) // 600)
            for v in A['smp'][::step]:
                r = B['tree'].find_nearest(v, TOL)
                if r[0] is not None: return True
        return False
    for i in range(n):
        for j in range(i + 1, n):
            if f(i) != f(j) and near(items[i], items[j]): par[f(i)] = f(j)
    comps = {}
    for i in range(n): comps.setdefault(f(i), []).append(i)
    bad = []
    cl = list(comps.values())
    for a in range(len(cl)):                                  # すき間: 別のかたまりどうしが NEAR 以内に近いのに接していない
        for b in range(a + 1, len(cl)):
            best = (1e9, None, None, None)
            for i in cl[a]:
                for v in items[i]['smp'][::max(1, len(items[i]['smp']) // 150)]:
                    for j in cl[b]:
                        r = items[j]['tree'].find_nearest(v, NEAR)
                        if r[0] is not None and r[3] < best[0]: best = (r[3], v, i, j)
            if best[0] < NEAR:
                d, v, i, j = best
                bad.append('GAP %s と %s 点(%.2f,%.2f,%.2f) すき間%.3f' % (items[i]['col'], items[j]['col'], v[0], v[2], v[1], d))
    if len(comps) == 1: return bad                           # 全体が一つのかたまり(水に浮く船など)は可
    for c in comps.values():
        low = min(items[i]['lo'][2] for i in c)              # Blender z = ゲーム y
        if low > ground + .15:
            it = items[c[0]]; ctr = (it['lo'] + it['hi']) / 2; gap = 1e9
            for i in c:                                       # ほかの部品までの最短距離(すき間の大きさ)
                for v in items[i]['vs'][::max(1, len(items[i]['vs']) // 200)]:
                    for j in range(n):
                        if j in c: continue
                        r = items[j]['tree'].find_nearest(v, 50)
                        if r[0] is not None: gap = min(gap, r[3])
            bad.append('%s/%s x%.1f y%.1f z%.1f (%d部品, 下端%.2f, すき間%.2f)' % (it['part'], it['col'], ctr[0], ctr[2], ctr[1], len(c), low, gap))
    for c in s_cut: bpy.data.objects.remove(c)
    return bad

if __name__ == '__main__':
    names = ONLY or list(P.keys()); nbad = 0
    for nm in names:
        b = check(nm)
        if b: nbad += 1; print('FLOAT', nm, len(b), '; '.join(b[:6]))
        else: print('OK', nm)
    print('done', len(names), 'props,', nbad, 'with floating parts')
