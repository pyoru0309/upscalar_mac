# はじめに

Upscalar の導入と起動方法を説明します。

## 動作環境

- macOS（Apple Silicon 推奨。Spandrel バックエンドは Metal / MPS を利用）/ Linux / Windows
- Python 3.9 以上
- デスクトップ版をビルドする場合は Rust ツールチェーン（`cargo`）と Node.js

## インストール

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Spandrel（MPS）バックエンドを使う場合は、PyTorch を環境に合わせて追加で導入します。

```bash
python -m pip install torch torchvision
```

モデルや実行ファイルの取得は [モデルのセットアップ](../setup/models.md) を参照してください。

## ブラウザ版の起動

```bash
python app.py
```

起動後、ブラウザで `http://127.0.0.1:7860` を開きます。7860 番が埋まっている場合は近い空きポートで起動します。

## デスクトップ版（Tauri）の起動

ブラウザを開かずネイティブウィンドウで使いたい場合は、Tauri 製の薄いラッパーを使います。Gradio サーバをサブプロセスとして起動し、ウィンドウに表示するだけの構成です（Python は同梱せず既存の `.venv` を使います）。

```bash
cd src-tauri
cargo run                              # 開発実行
npx --yes @tauri-apps/cli@^2 build     # .app / .dmg を生成
```

ビルドすると `src-tauri/target/release/bundle/` に配布物が生成されます。

- macOS: `bundle/macos/Upscalar.app`（Finder からダブルクリックで起動）
- macOS: `bundle/dmg/Upscalar_<ver>_aarch64.dmg`

ビルドした `.app` には開発時のプロジェクトの絶対パスが埋め込まれるため、同じマシン内であれば `.app` を任意の場所へ移動してもプロジェクト直下の `app.py` と `.venv` を見つけて起動します。

## 最初のアップスケール

1. `Single` タブで「ファイルを選択…」から画像を選ぶ（またはドラッグ＆ドロップ）。
2. `Engine` で使用するバックエンドを選ぶ（利用できないものは Backend status に理由が出ます）。
3. `Scale` で倍率を指定する。
4. `Upscale` を押す。出力は右側のプレビューと `Outputs` ギャラリーに表示されます。

各パラメータの詳細は [パラメータ設定](../reference/parameters.md) を参照してください。
