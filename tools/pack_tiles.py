# -*- coding: utf-8 -*-
"""
facade_tiles.py が焼いた壁タイル(色・法線)を JPEG にしてゲームのHTMLに埋め込む。

  python tools/pack_tiles.py <facade_tiles.pyの出力ディレクトリ> <HTMLファイル>

形式: [u32 ヘッダ長][ヘッダJSON][4バイト境界][JPEG...] を base64 にして <script type="text/plain" id="fc"> に入れる。
ヘッダ: {名前: {w, h, a:[位置,長さ], n:[位置,長さ]}}(w,h はタイルの大きさ[ゲームの単位])
"""
import sys, os, json, base64, io, re
import numpy as np
from PIL import Image

src, html = sys.argv[1], sys.argv[2]
meta = json.load(open(os.path.join(src, 'tiles.json')))
head = {}; blobs = bytearray()
def put(b):
    while len(blobs) % 4: blobs.append(0)
    off = len(blobs); blobs.extend(b); return [off, len(b)]
for name, m in sorted(meta.items()):
    e = dict(w=m['w'], h=m['h'])
    for k, q in (('a', 86), ('n', 92)):
        bio = io.BytesIO(); Image.fromarray(np.load(os.path.join(src, name + '_' + k + '.npy'))).save(bio, 'JPEG', quality=q, optimize=True)
        e[k] = put(bio.getvalue())
    head[name] = e
hb = json.dumps(head, separators=(',', ':')).encode()
data = bytearray(len(hb).to_bytes(4, 'little')) + hb
while len(data) % 4: data.append(32)
data += blobs
payload = base64.b64encode(bytes(data)).decode()
s = open(html, encoding='utf-8').read()
tag = '<script type="text/plain" id="fc">' + payload + '</script>'
if 'id="fc"' in s: s = re.sub(r'<script type="text/plain" id="fc">.*?</script>', lambda m: tag, s, count=1, flags=re.S)
else: s = s.replace('<script type="text/plain" id="bz">', tag + '\n<script type="text/plain" id="bz">', 1)
open(html, 'w', encoding='utf-8').write(s)
print(len(head), 'tiles', len(data), 'bytes ->', len(payload), 'base64 chars')
