# -*- coding: utf-8 -*-
"""
行の途中に書いた「// コメント」が、同じ行の後ろのコードを飲み込んでいないか検査する。

  python tools/check_comments.py tank_3d_babylon_v28_lite.html

1行に複数の文を詰めて書いているので、文の途中にコメントを足すと後ろのコードまでコメントになる事故が起きやすい
(例: 地形に合わせた傾きのリセットが消えて、戦車が回転し続けた)。日本語のコメントの後ろに、
JS の文らしい並び(代入・関数呼び出し・アロー関数など)が続いている行を報告する。見つかったら終了コード 1。
"""
import re, sys

src = open(sys.argv[1], encoding='utf-8').read().split('\n')
JP = r'[぀-ヿ一-鿿]'
code_after = re.compile(JP + r'[^぀-ヿ一-鿿]*?(?:\w\)\s*;|=>|\)\{|\};|;\s*[A-Za-z_$][\w$.\[\]]*\s*=[^=])')
bad = 0
for i, line in enumerate(src, 1):
    if len(line) > 3000:  # 埋め込みデータの行は対象外
        continue
    m = re.search(r'(?<![:\'"/\\])//(?!/)', line)
    if m and code_after.search(line[m.end():]):
        print(f'{i}: {line[m.start():m.start() + 160]}')
        bad += 1
print('OK' if not bad else f'{bad} 行でコメントがコードを飲み込んでいる可能性があります')
sys.exit(1 if bad else 0)
