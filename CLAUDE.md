# TANK 3D(tank_3d_babylon_v28_lite.html)の作業ルール

## 必ず守ること
- **戦車・障害物・建物・車・小物などのオブジェクトを新しく作る/作り直すときは、必ずウェブ検索で実物の資料(寸法・形・特徴的な部品・色)を調べてから作る。** 記憶だけで形を決めない。調べた要点はモデルのコメント(docstring)に残す。
- 実在のブランドや車種を模すときは、名前・ロゴは入れず形で表す。
- 返答は日本語。

## 構成
- ゲーム本体: `tank_3d_babylon_v28_lite.html`(Babylon.js を埋め込んだ1ファイル)。GitHub Pages で公開。
- 戦車モデル: `tools/tank_models.py`(Blender bpy)→ `tools/pack_assets.py` で `<script id="tk">` に埋め込み。
- 小物・名所・車: `tools/prop_models.py`, `tools/landmark_models.py` → `tools/pack_props.py`(`<script id="pr">`)。
- 建物の壁タイル: `tools/facade_tiles.py` → `tools/pack_tiles.py`(`<script id="fc">`)。
- コミット前に `python3 tools/check_comments.py tank_3d_babylon_v28_lite.html` を実行する(行の途中の // コメントが後ろのコードを飲み込む事故を防ぐ)。
- オブジェクトを置いたら当たり判定(K.solid / K.circ / 小物のメタ情報)を必ず付ける。
