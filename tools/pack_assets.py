# -*- coding: utf-8 -*-
"""
tank_models.py が出力した戦車データを1つにまとめ、ゲームのHTMLに埋め込む。

  python tools/pack_assets.py <tank_models.pyの出力ディレクトリ> <HTMLファイル>

形式: gzip( [u32 ヘッダ長][ヘッダJSON][4バイト境界][各車のbin][各車のJPEG] ) を base64 にして
<script type="text/plain" id="tk"> に入れる(既にあれば置き換える)。
"""
import sys, os, json, gzip, base64, io, re
from PIL import Image

src, html = sys.argv[1], sys.argv[2]
ids = ['leo', 'mk4', 't10', 'ab', 't90', 'cent', 'm4', 'k2', 't99']
head = {}; blobs = bytearray()
def put(b):
    while len(blobs) % 4: blobs.append(0)
    off = len(blobs); blobs.extend(b); return off
for t in ids:
    j = json.load(open(os.path.join(src, t + '.json')))
    j['bin'] = put(open(os.path.join(src, t + '.bin'), 'rb').read())
    im = Image.open(os.path.join(src, t + '_paint.png')).convert('RGB')
    bio = io.BytesIO(); im.save(bio, 'JPEG', quality=84, optimize=True, progressive=True)
    j['jpg'] = put(bio.getvalue()); j['jpgLen'] = len(bio.getvalue())
    head[t] = j
hb = json.dumps(head, separators=(',', ':')).encode()
data = bytearray(len(hb).to_bytes(4, 'little')) + hb
while len(data) % 4: data.append(32)
base = len(data); data += blobs
payload = base64.b64encode(gzip.compress(bytes(data), 9, mtime=0)).decode()
s = open(html, encoding='utf-8').read()
tag = '<script type="text/plain" id="tk">' + payload + '</script>'
if 'id="tk"' in s: s = re.sub(r'<script type="text/plain" id="tk">.*?</script>', lambda m: tag, s, count=1, flags=re.S)
else: s = s.replace('<script type="text/plain" id="bz">', tag + '\n<script type="text/plain" id="bz">', 1)
open(html, 'w', encoding='utf-8').write(s)
print('packed', len(data), 'bytes ->', len(payload), 'base64 chars; header base', base)
