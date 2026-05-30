# パラメータ設定

画面左側の各パラメータの意味と、設定のコツをまとめます。設定内容は実行のたびに `user_prefs.json` に保存され、次回起動時の既定値として復元されます。

## まずはプリセットから

迷ったら画面上部の **プリセット**（用途別おすすめ設定）を選んでください。エンジンと主要パラメータがまとめて設定されるので、まずは試してから細部を調整するのが近道です。

| プリセット | 用途 | 設定内容 |
| --- | --- | --- |
| 写真・実写 — Real-ESRGAN x4plus | 写真・実写の拡大 | Real-ESRGAN / `x4plus` / Scale 4 |
| アニメ・イラスト — Real-ESRGAN anime | アニメ・イラストをクリーンに拡大 | Real-ESRGAN / `x4plus-anime` / Scale 4 |
| 高品質・Apple Silicon — Spandrel(HAT等) | M1/M2 等で最高品質を狙う | Spandrel(MPS) / Scale 4 / Tile 512 / 半精度 OFF |
| 高速プレビュー — Pillow Lanczos | 構図確認・動作確認 | Pillow Lanczos / Scale 2 |

## 用途別のおすすめ

### アニメ・イラスト

- **クリーンに仕上げたい**ならまず **Real-ESRGAN の `realesrgan-x4plus-anime`**。線がきれいで破綻が少なく、高速です。
- さらに高品質を狙うなら、**Spandrel で HAT / DAT 等のアニメ向け学習済みモデル**を `models/spandrel/` に置いて使います（Apple Silicon の MPS 推奨）。
- **A-ESRGAN は高周波を強調する性質**があり、アニメではノイジー・荒めに見えることがあります。クリーン志向には不向きです。

### 写真・実写

- まず **Real-ESRGAN の `realesrgan-x4plus`**。汎用的でバランスが良いです。
- ディテール重視なら **Spandrel で HAT / SwinIR 等の写真向けモデル**を試してください。

### 速度・確認用

- 構図やパイプラインの確認には **Pillow Lanczos**（AI 拡大ではありません）。

!!! note "A-ESRGAN が「遅い・荒い」と感じたら"
    これは設定ミスではなく**モデルの性質**です。A-ESRGAN（特に `multi`）はマルチスケール識別器で高周波を強調するため、知覚的に荒く見えやすく、ネットワークも重いため Real-ESRGAN ncnn より遅くなります。クリーンさを求める場合は Real-ESRGAN の anime モデルや、Spandrel 経由の HAT 系モデルをおすすめします。

## 基本パラメータ

### Engine（エンジン）

アップスケールに使うバックエンドを選びます。各バックエンドの特徴は [バックエンド一覧](engines.md) を参照してください。

- 利用できないバックエンドは、画面下部の **Backend status** に理由（未インストール・重み未配置など）が表示されます。
- 起動時の既定は「利用可能なものの中で品質重視の順（Spandrel → A-ESRGAN → Real-ESRGAN → Pillow → External）」で自動選択されます。前回使ったエンジンが利用可能ならそれが優先されます。

### Scale（スケール）

出力の拡大倍率です（範囲 1〜8、既定 4）。

- バックエンドによっては**モデル固有の倍率**（例: 多くのモデルは 4x）で動作します。指定した Scale がモデル倍率と異なる場合、最終的に Lanczos で要求倍率へ調整されます（Spandrel など）。
- 大きい倍率ほど出力解像度・処理時間・メモリ使用量が増えます。

### Tile（タイル）

大きな画像をタイル分割して処理する一辺のピクセル数です（範囲 0〜1024、64 刻み、既定 0）。

- **0 は一括処理**（分割しない）。メモリに余裕があれば最速・最も継ぎ目が出ません。
- 0 以外を指定すると、その大きさのタイルに分割し、**16px のオーバーラップ**を取りながら推論します。高解像度画像で「メモリ不足（OOM）」になる場合に有効です。
- 値を小さくするほど省メモリですが、タイル数が増えて遅くなり、稀に境界が見えることがあります。まずは 512 や 256 から試すのがおすすめです。
- インプロセス系（Spandrel）に効きます。サブプロセス系（Real-ESRGAN ncnn / A-ESRGAN / External）は各実装側のタイル処理に依存します。

### Half precision（半精度）

半精度（fp16）で推論するかどうかです（既定 ON）。

- 対応環境（Apple Silicon の MPS など）では高速・省メモリになります。
- MPS で半精度がうまく動かない場合は**自動的に float32 へフォールバック**します。
- 色がおかしい・NaN が出るなど不安定なときは OFF にして再試行してください。

### Seed（シード）

乱数シードです（既定 1234）。

- 確率的な要素を持つバックエンド（プロンプト対応の拡散系など）で、結果の再現性に影響します。
- 決定論的なバックエンド（Pillow / 一般的な ESRGAN 系）では出力に影響しません。

### Output directory（出力ディレクトリ）

出力先のフォルダです。空欄の場合はプロジェクトの `outputs/` に保存されます。

- デスクトップ版では右の「参照…」から OS のフォルダ選択ダイアログで指定できます。
- 出力ファイル名はジョブ ID 付きになり、既存ファイルを上書きしません。
- macOS で選んだパスは NFC へ正規化して扱います（日本語の濁点・半濁点を含むパス対策）。

## Backend options（バックエンド別オプション）

「Backend options」アコーディオン内のオプションは、選択中のエンジンに対応するものだけが使われます。

### Real-ESRGAN model

Real-ESRGAN ncnn-vulkan で使うモデルを選びます。

| モデル | 用途 |
| --- | --- |
| `realesrgan-x4plus` | 写真・一般画像向けの標準モデル |
| `realesrgan-x4plus-anime` | アニメ・イラスト向け |
| `realesr-animevideov3` | アニメ動画フレーム向け（軽量） |

### A-ESRGAN model

A-ESRGAN で使うモデルを選びます。基本は 4x です。

| 値 | 内容 |
| --- | --- |
| `multi` | マルチスケール識別器版（`A_ESRGAN_Multi.pth`） |
| `single` | シングル識別器版（`A_ESRGAN_Single.pth`） |
| `custom` | 後方互換用。`UPSCALER_AESRGAN_MODEL` で指定した重み |

### Spandrel model (models/spandrel)

`models/spandrel/` に置いた重みファイル（`.pth` / `.safetensors` など）から選びます。spandrel がアーキテクチャ（HAT / SwinIR / DAT / ESRGAN / Real-ESRGAN / OmniSR など）を自動判定し、`torch.device("mps")` で推論します。

- 重みの入手は [モデルのセットアップ](../setup/models.md) を参照してください。
- 出力倍率はモデル固有のスケールを使い、Scale と異なる場合は Lanczos で調整します。

### Positive prompt / Negative prompt（プロンプト）

プロンプトを受け付けるバックエンド（拡散系や、プロンプトを利用する External Command）向けの入力です。プロンプト非対応のバックエンドでは無視されます。

### External command template（外部コマンドテンプレート）

CLI で呼べる任意の実装を「External Command」エンジンとして接続するためのテンプレートです。

```bash
python inference.py --input "{input}" --output "{output}" --scale {scale} --tile {tile}
```

使えるプレースホルダは `{input}` / `{output}` / `{scale}` / `{tile}` です。MSA-ESRGAN や独自モデルなど、標準で組み込まれていない実装を試すための枠です。

## バッチ実行のパラメータ

`Batch` タブでは、複数画像をまとめて処理できます。

| 項目 | 説明 |
| --- | --- |
| Input files | 複数の画像ファイルを選択（ドラッグ＆ドロップ可） |
| Input directory | 入力フォルダを指定（デスクトップ版は「参照…」で選択可） |
| Recursive | サブフォルダも再帰的に探索するか |

実行中は 1 枚ごとに進捗・ギャラリー・履歴が更新され、完了後にバッチレポート（`batch_report_*.md`）が出力されます。`Stop` で途中キャンセルできます。
