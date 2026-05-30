# モデルのセットアップ

各バックエンドが必要とする重み・実行ファイルの入手方法です。GitHub から配布されたソースには重み本体は含まれないため、下記のセットアップスクリプトで取得してください。

## 一括セットアップ（推奨）

`scripts/setup_models.py` から各バックエンドのアセットを取得できます。

```bash
# 既定: Spandrel(MPS) 用の推奨重み(RealESRGAN_x4plus.pth)を取得
python scripts/setup_models.py

# 個別に取得
python scripts/setup_models.py spandrel
python scripts/setup_models.py realesrgan
python scripts/setup_models.py aesrgan

# すべて取得
python scripts/setup_models.py all

# Spandrel の重みを指定して取得
python scripts/setup_models.py spandrel --model realesrgan-x4plus-anime
```

- ダウンロード済みのファイルがあるものはスキップします。
- 取得した重みは `models/spandrel/` などプロジェクト配下に保存され、GUI のドロップダウンに自動で表示されます。

## バックエンド別の詳細

### Spandrel (MPS)

`scripts/setup_models.py spandrel --model <名前>` で、`models/spandrel/` に重みをダウンロードします。spandrel が対応するアーキ（HAT / SwinIR / DAT / ESRGAN / RealESRGAN / OmniSR など40種以上）の `.pth` / `.safetensors` をそのまま読み込めます。

| `--model` 値 | ファイル | アーキ | 用途 |
| --- | --- | --- | --- |
| `realesrgan-x4plus` | `RealESRGAN_x4plus.pth` | ESRGAN | 写真・一般画像向け（既定・高速） |
| `realesrgan-x4plus-anime` | `RealESRGAN_x4plus_anime_6B.pth` | ESRGAN | アニメ・イラスト向け（高速） |
| `swinir-realsr-x4-large` | `..._SwinIR-L_x4_GAN.pth` | SwinIR | 写真の実写超解像・最高品質（重い） |
| `swinir-realsr-x4` | `..._SwinIR-M_x4_GAN.pth` | SwinIR | 写真の実写超解像・実用バランス |
| `swinir-classical-x4` | `001_classicalSR_..._x4.pth` | SwinIR | 劣化の少ない素材向け |

SwinIR は HAT / DAT と同系統の Transformer 系高品質モデルで、Apple Silicon の MPS で動きます（ESRGAN より高品質だが重め）。

```bash
python scripts/setup_models.py spandrel --model swinir-realsr-x4
```

### HAT / DAT を使う（手動配置）

HAT と DAT は spandrel 側では対応していますが、安定した直接ダウンロード URL が無いため自動取得には含めていません。配布元（HAT は Google Drive 等）から重みを入手し、`models/spandrel/` に置けば GUI の「Spandrel model」ドロップダウンに表示されます。

- HAT: <https://github.com/XPixelGroup/HAT>
- DAT: <https://github.com/zhengchen1999/DAT>

#### どの HAT モデルを選ぶ？

HAT は種類が多いですが、**入力画像の劣化の種類**で選びます。

| 入力画像 | おすすめ | 備考 |
| --- | --- | --- |
| 実写・写真・Web 画像・圧縮/ノイズあり | **`Real_HAT_GAN_SRx4.pth`** | 迷ったらこれ。実世界劣化で学習。Real-ESRGAN x4plus の上位互換的 |
| よりシャープにしたい | `Real_HAT_GAN_SRx4_sharper.pth` | 上のシャープ版 |
| クリーンな素材・忠実度最優先 | `HAT-L_SRx4.pth` | 最高品質だが重い |
| 標準的な忠実度重視 | `HAT_SRx4.pth` / `HAT_SRx4_ImageNet-pretrain.pth` | 標準サイズ |
| 軽さ優先 | `HAT-S_SRx4.pth` | 小型版 |

!!! warning "classical SR と real-world GAN の違い"
    `HAT_SRx4` / `HAT-L_SRx4` / `HAT-S` や DAT などの **classical SR 系**は、bicubic で縮小したクリーンな画像で学習しています。クリーン素材には最高ですが、**圧縮ノイズ等が乗った実写に使うとノイズごと鮮明化して逆に荒く見える**ことがあります。実写・実用には複雑な劣化で学習した **`Real_HAT_GAN_SRx4`** が向いています（モデルの「格」より、入力の劣化に合った学習かどうかが効きます）。

置いた後は、プリセット「高品質・Apple Silicon — Spandrel(HAT等)」を選ぶと、SwinIR / HAT / DAT の重みがあれば自動で選択されます。`HAT-L` など重いモデルで大きい画像を扱う場合は Tile を指定してください。探索先は `UPSCALAR_SPANDREL_MODEL_DIR` で変更できます。

### Real-ESRGAN ncnn-vulkan

`scripts/setup_models.py realesrgan`（内部で `scripts/setup_realesrgan_ncnn.py` を実行）で、OS に合った配布アーカイブを GitHub Releases から取得し、`external/realesrgan-ncnn-vulkan/` に展開します。

別の場所に実行ファイルがある場合は `UPSCALAR_REALESRGAN_BIN` で指定してください。モデルディレクトリは `UPSCALAR_REALESRGAN_MODEL_DIR` で変更できます。

### A-ESRGAN

`scripts/setup_models.py aesrgan`（内部で `scripts/setup_aesrgan.sh` を実行）で、`external/A-ESRGAN/` のクローン・`models/A_ESRGAN_Multi.pth` と `A_ESRGAN_Single.pth` の取得・現行 torchvision 向けの互換パッチ適用までを行います。

追加で次の依存が必要です。

```bash
python -m pip install torch torchvision basicsr facexlib gfpgan opencv-python tqdm
```

環境変数で配置を上書きできます。

```bash
export UPSCALAR_AESRGAN_REPO=/path/to/A-ESRGAN
export UPSCALAR_AESRGAN_MULTI_MODEL=/path/to/A_ESRGAN_Multi.pth
export UPSCALAR_AESRGAN_SINGLE_MODEL=/path/to/A_ESRGAN_Single.pth
```

## ライセンスについて

各モデル・実装にはそれぞれのライセンスがあります。Upscalar は非商用利用を前提とした実験用途です。配布元のライセンス条件を確認のうえ利用してください。
