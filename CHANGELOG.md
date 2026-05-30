# Changelog

このプロジェクトの主な変更点を記録します。
書式は [Keep a Changelog](https://keepachangelog.com/ja/1.1.0/) に、
バージョニングは [Semantic Versioning](https://semver.org/lang/ja/) に準じます。

## [Unreleased]

## [0.1.0] - 2026-05-30

### Added

- 初回リリース（Apple Silicon macOS 向け）。
- 5 つのバックエンド: Pillow Lanczos / Real-ESRGAN ncnn-vulkan / Spandrel (Apple Silicon MPS) / A-ESRGAN / External Command。
- 単体・バッチ・ディレクトリ入力のアップスケール、出力ギャラリー、入力/出力の比較画像。
- 実行履歴 (`outputs/history.jsonl`)、出力ごとのマニフェスト (`*.png.json`)、バッチレポート (`batch_report_*.md`)。
- バックエンド検出・診断表示、実行中の Stop によるキャンセル。
- CLI 実行 (`python -m upscaler.cli`)。
- Tauri 製デスクトップアプリ (.app / .dmg)。Gradio サーバを薄くラップして起動・表示・終了時クリーンアップを行う。
- OS ネイティブのファイル / フォルダ選択ダイアログ、macOS パスの NFC 正規化。
- 用途別プリセット、選択中エンジンに応じたオプションの有効/無効化、Seed のサイコロボタン。
- 設定の永続化 (`user_prefs.json`)。
- MPS メモリ解放ボタン。
- モデルダウンローダ `scripts/setup_models.py`（Real-ESRGAN / SwinIR / A-ESRGAN。HAT / DAT は手動配置を案内）。
- 同梱ユーザーガイド（[zensical](https://pypi.org/project/zensical/) で `user_guide/` → `docs/` を生成、アプリの `/guide` で配信、ヘルプボタンから起動）。

[Unreleased]: https://github.com/pyoru0309/upscaler_mac/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/pyoru0309/upscaler_mac/releases/tag/v0.1.0
