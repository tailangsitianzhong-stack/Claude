# -*- coding: utf-8 -*-
"""
prop_models.py が出力した小物データ(<名前>.bin/.json)を1つにまとめ、ゲームのHTMLに埋め込む。

  python tools/pack_props.py <prop_models.pyの出力ディレクトリ> <HTMLファイル>

形式: gzip( [u32 ヘッダ長][ヘッダJSON][4バイト境界][全小物のbin] ) を base64 にして
<script type="text/plain" id="pr"> に入れる(既にあれば置き換える)。ヘッダには小物ごとの高さ hi も入れる。
"""
import sys, os, json, gzip, base64, re

src, html = sys.argv[1], sys.argv[2]
head = {}; blobs = bytearray()
for f in sorted(os.listdir(src)):
    if not f.endswith('.json'): continue
    name = f[:-5]; j = json.load(open(os.path.join(src, f)))
    while len(blobs) % 4: blobs.append(0)
    off = len(blobs); blobs.extend(open(os.path.join(src, name + '.bin'), 'rb').read())
    piv = j.get('pivots') or {}; hi = 0
    for p in j['parts']:
        for k in ('p', 'n', 'c', 'i'): p[k] += off
        hi = max(hi, (piv.get(p['part']) or [0, 0, 0])[1] + p['lo'][1] + p['sc'][1])
        p['lo'] = [round(v, 5) for v in p['lo']]; p['sc'] = [round(v, 5) for v in p['sc']]
    j['hi'] = round(hi, 3); head[name] = j
hb = json.dumps(head, separators=(',', ':')).encode()
data = bytearray(len(hb).to_bytes(4, 'little')) + hb
while len(data) % 4: data.append(32)
data += blobs
payload = base64.b64encode(gzip.compress(bytes(data), 9, mtime=0)).decode()
s = open(html, encoding='utf-8').read()
tag = '<script type="text/plain" id="pr">' + payload + '</script>'
if 'id="pr"' in s: s = re.sub(r'<script type="text/plain" id="pr">.*?</script>', lambda m: tag, s, count=1, flags=re.S)
else: s = s.replace('<script type="text/plain" id="bz">', tag + '\n<script type="text/plain" id="bz">', 1)
open(html, 'w', encoding='utf-8').write(s)
print(len(head), 'props', len(data), 'bytes ->', len(payload), 'base64 chars')
