# バックエンド一覧

Upscalar は 5 種類のバックエンドを切り替えて使えます。どれを使うか迷ったら、まず下の早見表を参考にしてください。

## 早見表

| 目的 | おすすめ |
| --- | --- |
| 画質重視 / Apple Silicon で Transformer 系(HAT 等)を試す | Spandrel (MPS) |
| GAN 系の軽量高品質候補 | A-ESRGAN |
| 導入しやすい標準 | Real-ESRGAN ncnn-vulkan |
| 依存確認・フォールバック | Pillow Lanczos |
| 独自実装・実験 | External Command |

## Pillow Lanczos

依存確認用のフォールバックです。Pillow の Lanczos リサンプリングで拡大するだけで、AI アップスケールではありません。動作確認や比較の基準として使います。

## Real-ESRGAN ncnn-vulkan

Real-ESRGAN の軽量な標準バックエンドです。`realesrgan-ncnn-vulkan` 実行ファイルをサブプロセスとして呼び出します。

- 実行ファイルが `PATH` にあるか、`UPSCALAR_REALESRGAN_BIN` で指定します。
- 取得方法は [モデルのセットアップ](../setup/models.md) を参照してください。
- モデルは `realesrgan-x4plus` / `realesrgan-x4plus-anime` / `realesr-animevideov3` から選べます。

## Spandrel (Apple Silicon MPS)

Apple Silicon の Metal (MPS) を使うインプロセス PyTorch バックエンドです。[spandrel](https://github.com/chaiNNer-org/spandrel) が重みのアーキテクチャ（HAT / SwinIR / DAT / ESRGAN / Real-ESRGAN / OmniSR など）を自動判定して推論します。CUDA は不要です。

- 重みは `models/spandrel/` に置くと「Spandrel model」ドロップダウンに表示されます。
- **SwinIR の重みは `python scripts/setup_models.py spandrel --model swinir-realsr-x4` で取得できます**（HAT / DAT は手動配置。[モデルのセットアップ](../setup/models.md) 参照）。
- HAT / SwinIR / DAT など入力サイズに窓制約があるモデルも、内部で自動パディングして正しく処理します。
- 大きな画像でメモリが厳しい場合は Tile を指定してください。
- 半精度は対応モデルかつ MPS のときのみ使用し、非対応・失敗時は float32 で処理します。
- 既存の A-ESRGAN 重み（ESRGAN ベース）もこのバックエンドで読み込めます。

## A-ESRGAN

A-ESRGAN の公式リポジトリと重みを外部に置いて呼び出すバックエンドです。4x モデルが中心です。

- セットアップは [モデルのセットアップ](../setup/models.md) を参照してください。
- `multi` / `single` / `custom` を選べます。
- CUDA が無い環境では半精度指定を自動で外して CPU 実行します（遅い場合は Spandrel での読み込みも検討してください）。

!!! warning "A-ESRGAN の性質"
    A-ESRGAN（特に `multi`）はマルチスケール識別器によって**高周波を強調する**ため、出力が知覚的に**荒め・ノイジー**に見えやすく、ネットワークも重いため**遅い**傾向があります。これは設定の問題ではなくモデルの特性です。クリーンな仕上がりを求める場合は **Real-ESRGAN の anime モデル**や、**Spandrel 経由の HAT / DAT 系モデル**の方が向いています。

## External Command

CLI で呼べる任意の実装を接続するための枠です。コマンドテンプレートに `{input}` / `{output}` / `{scale}` / `{tile}` のプレースホルダを書いて使います。詳しくは [パラメータ設定](parameters.md#external-command-templateコマンド) を参照してください。

## 参考リンク

- Real-ESRGAN: <https://github.com/xinntao/Real-ESRGAN>
- A-ESRGAN: <https://github.com/stroking-fishes-ml-corp/A-ESRGAN>
- spandrel: <https://github.com/chaiNNer-org/spandrel>
- HAT: <https://github.com/XPixelGroup/HAT>
