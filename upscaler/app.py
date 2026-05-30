from __future__ import annotations

import os
import random
import socket
import unicodedata
from pathlib import Path
from typing import Dict, Iterator, List, Sequence, Tuple

from upscaler import cancellation, settings
from upscaler.diagnostics import diagnostics_markdown, release_memory
from upscaler.history import latest_records, records_markdown
from upscaler.images import collect_image_paths
from upscaler.jobs import run_many_iter, run_recorded, successful_comparisons, successful_outputs
from upscaler.reports import write_batch_report
from upscaler.registry import build_registry


REALESRGAN_MODELS = [
    "realesrgan-x4plus",
    "realesrgan-x4plus-anime",
    "realesr-animevideov3",
]

AESRGAN_MODELS = ["multi", "single", "custom"]

# 各エンジンが実際に参照するオプション。ここに無い項目はそのエンジンでは無効(灰色)にする。
# Scale は全エンジン共通なので常に有効。seed/prompt はビルトインでは未使用のため外部コマンド枠のみ。
ENGINE_OPTIONS = {
    "pillow_lanczos": set(),
    "realesrgan_ncnn": {"tile", "realesrgan_model"},
    "aesrgan": {"tile", "half", "aesrgan_model"},
    "spandrel_mps": {"tile", "half", "spandrel_model"},
    "external_command": {"tile", "seed", "prompt", "negative_prompt", "custom_command"},
}

PRESET_NONE = "（プリセット: 手動設定）"
# 用途別のおすすめ初期設定。選ぶと関連パラメータをまとめて適用する。
PRESETS = {
    "写真・実写 — Real-ESRGAN x4plus": {
        "engine_id": "realesrgan_ncnn", "scale": 4, "tile": 0, "half": True,
        "realesrgan_model": "realesrgan-x4plus",
    },
    "アニメ・イラスト — Real-ESRGAN anime": {
        "engine_id": "realesrgan_ncnn", "scale": 4, "tile": 0, "half": True,
        "realesrgan_model": "realesrgan-x4plus-anime",
    },
    "高品質・Apple Silicon — Spandrel(HAT等)": {
        "engine_id": "spandrel_mps", "scale": 4, "tile": 512, "half": False,
        # 該当する重みが既に置かれていれば Spandrel モデルとして自動選択する。
        "spandrel_prefer": ["swinir", "hat", "dat"],
    },
    "高速プレビュー — Pillow Lanczos": {
        "engine_id": "pillow_lanczos", "scale": 2, "tile": 0, "half": True,
    },
}


def _spandrel_model_choices() -> list[str]:
    return [path.name for path in settings.spandrel_model_files()]


def engine_status_markdown() -> str:
    rows = ["| Engine | Status | Notes |", "| --- | --- | --- |"]
    for engine in build_registry().values():
        status = engine.availability_message()
        limited = "non-commercial only" if engine.spec.non_commercial_only else ""
        rows.append(f"| {engine.spec.name} | {status} | {limited} |")
    return "\n".join(rows)


def _engine_choices(registry: Dict[str, object]) -> list[str]:
    return [f"{engine.spec.name} ({engine.spec.id})" for engine in registry.values()]


def _engine_id_from_choice(choice: str) -> str:
    if "(" not in choice or ")" not in choice:
        return choice
    return choice.rsplit("(", 1)[-1].rstrip(")")


def _nfc(text: str) -> str:
    # macOS のダイアログ/ファイルシステムは濁点等を NFD(分解形)で返すため NFC へ正規化する。
    # APFS のルックアップは正規化非依存なので、NFC パスでも NFD の実ファイルを開ける。
    return unicodedata.normalize("NFC", text) if text else text


def _coerce_choice(value, allowed, default):
    # 永続化された選択肢が現在の候補に存在しない場合は既定へフォールバックする。
    return value if value in allowed else default


def _persist_prefs(
    engine_choice: str,
    scale,
    tile,
    half,
    seed,
    realesrgan_model: str,
    aesrgan_model: str,
    spandrel_model: str,
    output_dir: str,
    recursive=None,
    input_directory=None,
) -> None:
    prefs = settings.load_prefs()
    prefs.update(
        {
            "engine_id": _engine_id_from_choice(engine_choice),
            "scale": int(scale),
            "tile": int(tile),
            "half": bool(half),
            "seed": int(seed),
            "realesrgan_model": realesrgan_model,
            "aesrgan_model": aesrgan_model,
            "spandrel_model": spandrel_model,
            "output_dir": (output_dir or "").strip(),
        }
    )
    if recursive is not None:
        prefs["recursive"] = bool(recursive)
    if input_directory is not None:
        prefs["input_directory"] = (input_directory or "").strip()
    settings.save_prefs(prefs)


def _set_input_image(path: str):
    # ネイティブのファイルダイアログ(フロントエンド)で得たパスをバックエンド経由で
    # Image コンポーネントへ渡し、Gradio に表示用として配信させる。
    # キャンセル時(空文字)は現在の画像を維持する。
    import gradio as gr

    return _nfc(path) if path else gr.update()


def history_markdown() -> str:
    return records_markdown(latest_records(limit=20))


def history_outputs() -> List[str]:
    return successful_outputs(latest_records(limit=20))


def history_comparisons() -> List[str]:
    return successful_comparisons(latest_records(limit=20))


def refresh_history_view() -> Tuple[str, List[str], List[str]]:
    return history_markdown(), history_outputs(), history_comparisons()


def _engine_options(
    scale: int,
    tile: int,
    half: bool,
    seed: int,
    realesrgan_model: str,
    aesrgan_model: str,
    spandrel_model: str,
    prompt: str,
    negative_prompt: str,
    custom_command: str,
    output_dir: str,
) -> Dict[str, object]:
    options = {
        "scale": int(scale),
        "tile": int(tile),
        "half": bool(half),
        "seed": int(seed),
        "realesrgan_model": realesrgan_model,
        "aesrgan_model": aesrgan_model,
        "spandrel_model": spandrel_model,
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "custom_command": custom_command,
    }
    if output_dir.strip():
        options["output_dir"] = output_dir.strip()
    return options


def _paths_from_files(files: Sequence[object] | None) -> List[Path]:
    paths: List[Path] = []
    for file in files or []:
        if isinstance(file, str):
            paths.append(Path(file))
        elif isinstance(file, dict) and file.get("path"):
            paths.append(Path(str(file["path"])))
        elif hasattr(file, "name"):
            paths.append(Path(str(file.name)))
        elif hasattr(file, "path"):
            paths.append(Path(str(file.path)))
    return paths


def run_upscale(
    input_image: str,
    engine_choice: str,
    scale: int,
    tile: int,
    half: bool,
    seed: int,
    realesrgan_model: str,
    aesrgan_model: str,
    spandrel_model: str,
    prompt: str,
    negative_prompt: str,
    custom_command: str,
    output_dir: str,
) -> Tuple[str | None, List[str], List[str], str, str]:
    if not input_image:
        return None, [], [], "画像を選択してください。", history_markdown()
    input_image = _nfc(input_image)
    output_dir = _nfc(output_dir)
    _persist_prefs(
        engine_choice, scale, tile, half, seed,
        realesrgan_model, aesrgan_model, spandrel_model, output_dir,
    )
    engine_id = _engine_id_from_choice(engine_choice)
    options = _engine_options(
        scale,
        tile,
        half,
        seed,
        realesrgan_model,
        aesrgan_model,
        spandrel_model,
        prompt,
        negative_prompt,
        custom_command,
        output_dir,
    )
    token = cancellation.start_token()
    try:
        record = run_recorded(Path(input_image), engine_id, options, cancel_token=token)
    finally:
        cancellation.clear_current(token)
    outputs = successful_outputs([record])
    comparisons = successful_comparisons([record])
    image = outputs[0] if outputs else None
    log = _records_log([record])
    return image, outputs, comparisons, log, history_markdown()


def run_batch_upscale(
    input_files: Sequence[object],
    input_directory: str,
    recursive: bool,
    engine_choice: str,
    scale: int,
    tile: int,
    half: bool,
    seed: int,
    realesrgan_model: str,
    aesrgan_model: str,
    spandrel_model: str,
    prompt: str,
    negative_prompt: str,
    custom_command: str,
    output_dir: str,
) -> Iterator[Tuple[List[str], List[str], str, str]]:
    input_directory = _nfc(input_directory)
    output_dir = _nfc(output_dir)
    paths = _paths_from_files(input_files)
    if input_directory.strip():
        paths.extend(collect_image_paths([Path(input_directory.strip()).expanduser()], recursive=recursive))
    paths = list(dict.fromkeys(paths))
    if not paths:
        yield [], [], "画像ファイルまたは入力ディレクトリを選択してください。", history_markdown()
        return
    _persist_prefs(
        engine_choice, scale, tile, half, seed,
        realesrgan_model, aesrgan_model, spandrel_model, output_dir,
        recursive=recursive, input_directory=input_directory,
    )
    engine_id = _engine_id_from_choice(engine_choice)
    options = _engine_options(
        scale,
        tile,
        half,
        seed,
        realesrgan_model,
        aesrgan_model,
        spandrel_model,
        prompt,
        negative_prompt,
        custom_command,
        output_dir,
    )
    token = cancellation.start_token()
    records = []
    try:
        for idx, total, record in run_many_iter(paths, engine_id, options, cancel_token=token):
            records.append(record)
            done = sum(1 for r in records if r.status == "ok")
            failed = sum(1 for r in records if r.status not in ("ok", "cancelled"))
            cancelled = sum(1 for r in records if r.status == "cancelled")
            header = f"進捗: {idx}/{total} (完了 {done} / 失敗 {failed} / キャンセル {cancelled})"
            log = header + "\n\n" + _records_log(records)
            yield successful_outputs(records), successful_comparisons(records), log, history_markdown()
    finally:
        cancellation.clear_current(token)
    report_path = write_batch_report(records, options)
    log = _records_log(records) + f"\n\nreport: {report_path}"
    yield successful_outputs(records), successful_comparisons(records), log, history_markdown()


def _records_log(records) -> str:
    ok_count = sum(1 for record in records if record.status == "ok")
    error_count = len(records) - ok_count
    lines = [f"完了: {ok_count} / 失敗: {error_count}"]
    for record in records:
        output = f" -> {record.output_path}" if record.output_path else ""
        elapsed = f"{record.elapsed_seconds:.2f}s"
        size = ""
        if record.input_width and record.input_height and record.output_width and record.output_height:
            size = f" ({record.input_width}x{record.input_height} -> {record.output_width}x{record.output_height})"
        lines.append(f"- {record.status}: {Path(record.input_path).name}{output}{size} [{elapsed}]")
        if record.manifest_path:
            lines.append(f"  manifest: {record.manifest_path}")
        if record.status != "ok":
            lines.append("")
            lines.append("```text")
            lines.append(record.message)
            lines.append("```")
    return "\n".join(lines)


def build_app():
    import gradio as gr

    settings.ensure_workspace_dirs()
    registry = build_registry()
    choices = _engine_choices(registry)
    prefs = settings.load_prefs()
    preferred_order = ["spandrel_mps", "aesrgan", "realesrgan_ncnn", "pillow_lanczos", "external_command"]
    pref_engine_id = prefs.get("engine_id")
    if pref_engine_id in registry and registry[pref_engine_id].is_available():
        default_engine_id = pref_engine_id
    else:
        default_engine_id = next(
            (engine_id for engine_id in preferred_order if registry[engine_id].is_available()),
            "pillow_lanczos",
        )
    default_engine = next(choice for choice in choices if choice.endswith(f"({default_engine_id})"))

    css = """
    .upscaler-shell { max-width: 1180px; margin: 0 auto; }
    .status-box textarea { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; }
    /* 横長テーブル(特にHistory)がはみ出さないよう、コンテナ内で横スクロールさせる */
    .table-scroll { overflow-x: auto; max-width: 100%; }
    .table-scroll table { width: max-content; min-width: 100%; border-collapse: collapse; }
    .table-scroll th, .table-scroll td { white-space: nowrap; padding: 6px 12px; }
    """

    # ドロップゾーン外に画像を落とした際、ブラウザ/Webview が画像ファイルへ遷移して
    # 戻れなくなるのを防ぐ。Gradio のドロップゾーンは dataTransfer 経由で処理するため影響しない。
    head = """
    <script>
      window.addEventListener('dragover', function (e) { e.preventDefault(); });
      window.addEventListener('drop', function (e) { e.preventDefault(); });
    </script>
    """

    with gr.Blocks(title="Upscaler", css=css, head=head) as demo:
        with gr.Row():
            gr.Markdown("# Upscaler")
            help_button = gr.Button("ヘルプ / ユーザーガイド", scale=0, min_width=200)

        with gr.Row():
            with gr.Column(scale=5):
                preset = gr.Dropdown(
                    choices=[PRESET_NONE, *PRESETS.keys()],
                    value=PRESET_NONE,
                    label="プリセット（用途別おすすめ設定）",
                )
                engine_choice = gr.Dropdown(
                    choices=choices,
                    value=default_engine,
                    label="Engine",
                )
                with gr.Row():
                    scale = gr.Slider(1, 8, value=int(prefs.get("scale", 4)), step=1, label="Scale")
                    tile = gr.Slider(0, 1024, value=int(prefs.get("tile", 0)), step=64, label="Tile")
                with gr.Row():
                    half = gr.Checkbox(value=bool(prefs.get("half", True)), label="Half precision")
                    seed = gr.Number(value=int(prefs.get("seed", 1234)), precision=0, label="Seed", scale=3)
                    seed_dice = gr.Button("🎲", scale=0, min_width=48)
                with gr.Row():
                    output_dir = gr.Textbox(
                        label="Output directory",
                        value=prefs.get("output_dir", ""),
                        placeholder=str(settings.OUTPUTS_DIR),
                        scale=5,
                    )
                    browse_output_dir = gr.Button("参照…", scale=1, min_width=80)

                with gr.Accordion("Backend options", open=False):
                    realesrgan_model = gr.Dropdown(
                        choices=REALESRGAN_MODELS,
                        value=_coerce_choice(prefs.get("realesrgan_model"), REALESRGAN_MODELS, REALESRGAN_MODELS[0]),
                        label="Real-ESRGAN model",
                    )
                    aesrgan_model = gr.Dropdown(
                        choices=AESRGAN_MODELS,
                        value=_coerce_choice(prefs.get("aesrgan_model"), AESRGAN_MODELS, AESRGAN_MODELS[0]),
                        label="A-ESRGAN model",
                    )
                    spandrel_choices = _spandrel_model_choices()
                    spandrel_default = _coerce_choice(
                        prefs.get("spandrel_model"),
                        spandrel_choices,
                        spandrel_choices[0] if spandrel_choices else None,
                    )
                    spandrel_model = gr.Dropdown(
                        choices=spandrel_choices,
                        value=spandrel_default,
                        label="Spandrel model (models/spandrel)",
                    )
                    prompt = gr.Textbox(label="Positive prompt", lines=2)
                    negative_prompt = gr.Textbox(label="Negative prompt", lines=2)
                    custom_command = gr.Textbox(
                        label="External command template",
                        placeholder='python inference.py --input "{input}" --output "{output}" --scale {scale} --tile {tile}',
                        lines=2,
                    )

                with gr.Tabs():
                    with gr.Tab("Single"):
                        input_image = gr.Image(label="Input", type="filepath")
                        # ファイルダイアログで得たパス文字列を確実に Python 側へ渡す中継。
                        picked_file = gr.Textbox(visible=False)
                        browse_input_file = gr.Button("ファイルを選択…")
                        with gr.Row():
                            run_button = gr.Button("Upscale", variant="primary")
                            stop_button = gr.Button("Stop", variant="stop")
                    with gr.Tab("Batch"):
                        input_files = gr.File(
                            label="Input files",
                            file_count="multiple",
                            file_types=["image"],
                            type="filepath",
                        )
                        with gr.Row():
                            input_directory = gr.Textbox(
                                label="Input directory",
                                value=prefs.get("input_directory", ""),
                                placeholder=str(settings.INPUTS_DIR),
                                scale=5,
                            )
                            browse_input_dir = gr.Button("参照…", scale=1, min_width=80)
                        recursive = gr.Checkbox(value=bool(prefs.get("recursive", False)), label="Recursive")
                        with gr.Row():
                            run_batch_button = gr.Button("Upscale batch", variant="primary")
                            stop_batch_button = gr.Button("Stop", variant="stop")

            with gr.Column(scale=5):
                output_image = gr.Image(label="Output", type="filepath")
                output_gallery = gr.Gallery(label="Outputs", columns=3, object_fit="contain", height=320)
                comparison_gallery = gr.Gallery(label="Comparisons", columns=2, object_fit="contain", height=320)
                log_output = gr.Markdown()

        with gr.Accordion("Backend status", open=True):
            status = gr.Markdown(engine_status_markdown(), elem_classes=["table-scroll"])
            refresh = gr.Button("Refresh status")
            refresh.click(fn=engine_status_markdown, outputs=status)

        with gr.Accordion("History", open=False):
            history = gr.Markdown(history_markdown(), elem_classes=["table-scroll"])
            history_gallery = gr.Gallery(label="Recent outputs", columns=4, object_fit="contain", height=260, value=history_outputs())
            history_comparison_gallery = gr.Gallery(
                label="Recent comparisons",
                columns=2,
                object_fit="contain",
                height=260,
                value=history_comparisons(),
            )
            refresh_history = gr.Button("Refresh history")
            refresh_history.click(fn=refresh_history_view, outputs=[history, history_gallery, history_comparison_gallery])

        with gr.Accordion("Diagnostics", open=False):
            diagnostics = gr.Markdown(diagnostics_markdown())
            with gr.Row():
                refresh_diagnostics = gr.Button("Refresh diagnostics")
                release_memory_button = gr.Button("メモリを解放", variant="secondary")
            memory_status = gr.Markdown()
            refresh_diagnostics.click(fn=diagnostics_markdown, outputs=diagnostics)

            def _release_and_refresh():
                return release_memory(), diagnostics_markdown()

            # 解放後に診断表(メモリ表示)も更新する。
            release_memory_button.click(
                fn=_release_and_refresh,
                outputs=[memory_status, diagnostics],
            )

        run_event = run_button.click(
            fn=run_upscale,
            inputs=[
                input_image,
                engine_choice,
                scale,
                tile,
                half,
                seed,
                realesrgan_model,
                aesrgan_model,
                spandrel_model,
                prompt,
                negative_prompt,
                custom_command,
                output_dir,
            ],
            outputs=[output_image, output_gallery, comparison_gallery, log_output, history],
        )
        run_batch_event = run_batch_button.click(
            fn=run_batch_upscale,
            inputs=[
                input_files,
                input_directory,
                recursive,
                engine_choice,
                scale,
                tile,
                half,
                seed,
                realesrgan_model,
                aesrgan_model,
                spandrel_model,
                prompt,
                negative_prompt,
                custom_command,
                output_dir,
            ],
            outputs=[output_gallery, comparison_gallery, log_output, history],
        )
        stop_button.click(fn=cancellation.cancel_current, inputs=None, outputs=None, cancels=[run_event])
        stop_batch_button.click(
            fn=cancellation.cancel_current,
            inputs=None,
            outputs=None,
            cancels=[run_batch_event],
        )

        # Seed のサイコロ: ランダムなシード値をセットする。
        seed_dice.click(fn=lambda: random.randint(0, 2 ** 31 - 1), outputs=seed)

        # エンジンに合わせて無関係なオプションを無効化(灰色)する。Scale は全エンジン共通。
        _option_components = [
            tile, half, seed, seed_dice,
            realesrgan_model, aesrgan_model, spandrel_model,
            prompt, negative_prompt, custom_command,
        ]

        def update_option_states(engine_choice_value):
            rel = ENGINE_OPTIONS.get(_engine_id_from_choice(engine_choice_value), set())
            keys = [
                "tile", "half", "seed", "seed",  # seed_dice は seed と同じ可否
                "realesrgan_model", "aesrgan_model", "spandrel_model",
                "prompt", "negative_prompt", "custom_command",
            ]
            return tuple(gr.update(interactive=(k in rel)) for k in keys)

        engine_choice.change(fn=update_option_states, inputs=engine_choice, outputs=_option_components)
        # 起動時の初期状態(既定エンジン)にも反映する。
        demo.load(fn=update_option_states, inputs=engine_choice, outputs=_option_components)

        # Tauri 連携: dialog プラグインの open コマンドを直接呼ぶ。自作コマンドはリモート
        # (http://127.0.0.1)コンテキストの ACL で拒否されるため、capabilities で許可済みの
        # plugin:dialog|open を使う。Tauri 外(純ブラウザ)では何もしないで現在値を保持する。
        _IMAGE_EXTS = "['png','jpg','jpeg','webp','bmp','tif','tiff','gif']"
        _pick_dir_js = """
        async (current) => {
          try {
            if (window.__TAURI__ && window.__TAURI__.core) {
              const p = await window.__TAURI__.core.invoke('plugin:dialog|open', { options: { directory: true, multiple: false } });
              const v = (p && typeof p === 'object') ? (p.path || '') : p;
              if (v) return v.normalize('NFC');
            }
          } catch (e) { console.error('pick dir failed', e); }
          return current;
        }
        """
        _pick_file_js = (
            """
        async (current) => {
          try {
            if (window.__TAURI__ && window.__TAURI__.core) {
              const p = await window.__TAURI__.core.invoke('plugin:dialog|open', { options: { directory: false, multiple: false, filters: [{ name: 'Images', extensions: __EXTS__ }] } });
              const v = (p && typeof p === 'object') ? (p.path || '') : p;
              if (v) return v.normalize('NFC');
            }
          } catch (e) { console.error('pick file failed', e); }
          return current;
        }
        """.replace("__EXTS__", _IMAGE_EXTS)
        )
        def apply_preset(name: str):
            cfg = PRESETS.get(name)
            if not cfg:
                return tuple(gr.update() for _ in range(6))
            label = next((c for c in choices if c.endswith(f"({cfg['engine_id']})")), None)
            realesrgan = cfg.get("realesrgan_model")
            # 高品質プリセット等: 推奨アーキの重みが既にあれば Spandrel モデルを自動選択。
            spandrel_update = gr.update()
            prefer = cfg.get("spandrel_prefer")
            if prefer:
                match = next(
                    (c for c in spandrel_choices if any(k in c.lower() for k in prefer)),
                    None,
                )
                if match:
                    spandrel_update = gr.update(value=match)
            return (
                gr.update(value=label) if label else gr.update(),
                gr.update(value=cfg["scale"]),
                gr.update(value=cfg["tile"]),
                gr.update(value=cfg["half"]),
                gr.update(value=realesrgan) if realesrgan else gr.update(),
                spandrel_update,
            )

        preset.change(
            fn=apply_preset,
            inputs=preset,
            outputs=[engine_choice, scale, tile, half, realesrgan_model, spandrel_model],
        )

        # ヘルプ: 同一オリジンで配信しているユーザーガイド(/guide/)を別画面で開く。
        # Tauri では opener プラグインで OS のブラウザを起動し、純ブラウザでは新規タブで開く。
        _help_js = """
        async () => {
          const url = location.origin + '/guide/';
          try {
            if (window.__TAURI__ && window.__TAURI__.core) {
              await window.__TAURI__.core.invoke('plugin:opener|open_url', { url });
              return;
            }
          } catch (e) { console.error('open guide failed', e); }
          window.open(url, '_blank');
        }
        """
        help_button.click(fn=None, inputs=None, outputs=None, js=_help_js)
        browse_output_dir.click(fn=None, inputs=output_dir, outputs=output_dir, js=_pick_dir_js)
        browse_input_dir.click(fn=None, inputs=input_directory, outputs=input_directory, js=_pick_dir_js)
        # 中継テキストボックス経由でパス文字列を受け取り、バックエンドで Image へ反映する。
        browse_input_file.click(
            fn=_set_input_image,
            inputs=picked_file,
            outputs=input_image,
            js=_pick_file_js,
        )

    return demo


def _watch_parent(parent_pid: int) -> None:
    # Tauri などのラッパーから起動された場合、親プロセスが消えたら自分も終了する。
    # グレースフル終了に頼らず、SIGKILL やクラッシュ時もサーバを残さないための保険。
    import threading
    import time

    def _poll() -> None:
        while True:
            try:
                os.kill(parent_pid, 0)
            except OSError:
                os._exit(0)
            time.sleep(1.0)

    thread = threading.Thread(target=_poll, name="upscaler-parent-watch", daemon=True)
    thread.start()


def main() -> None:
    parent_pid = os.getenv("UPSCALER_PARENT_PID")
    if parent_pid and parent_pid.isdigit():
        _watch_parent(int(parent_pid))
    demo = build_app()
    demo.queue()
    host = os.getenv("UPSCALER_HOST", "127.0.0.1")
    start_port = int(os.getenv("UPSCALER_PORT", "7860"))
    port = _find_free_port(host, start_port)
    # Tauri など外部ラッパーが起動URLを確実に取得できるよう、安定したマーカーを出力する。
    print(f"UPSCALER_URL=http://{host}:{port}", flush=True)
    _serve(demo, host, port)


def _serve(demo, host: str, port: int) -> None:
    # ユーザーガイド(docs/)を /guide で同梱配信しつつ、Gradio を / にマウントして起動する。
    import gradio as gr
    import uvicorn
    from fastapi import FastAPI

    app = FastAPI()
    if settings.DOCS_DIR.exists():
        # /guide を Gradio(/) より先に登録して、こちらが優先的にマッチするようにする。
        from fastapi.staticfiles import StaticFiles

        app.mount("/guide", StaticFiles(directory=str(settings.DOCS_DIR), html=True), name="guide")
    # ネイティブのファイルダイアログで選んだ任意パスの画像を表示できるよう全ルートを許可する。
    # 127.0.0.1 限定のローカル単一ユーザー用途を前提とする。
    app = gr.mount_gradio_app(app, demo, path="/", allowed_paths=["/"])
    uvicorn.run(app, host=host, port=port, log_level="warning")


def _find_free_port(host: str, start_port: int, attempts: int = 50) -> int:
    for port in range(start_port, start_port + attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind((host, port))
                return port
            except OSError:
                continue
    raise OSError(f"No free port found in range {start_port}-{start_port + attempts - 1}")
