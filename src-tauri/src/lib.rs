use std::io::{BufRead, BufReader};
use std::net::TcpStream;
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::mpsc;
use std::sync::Mutex;
use std::thread;
use std::time::{Duration, Instant};

use tauri::{Manager, RunEvent, WebviewWindow};

/// 起動した Gradio (Python) プロセスを保持し、アプリ終了時に確実に停止させる。
#[derive(Default)]
struct PythonServer(Mutex<Option<Child>>);

/// プロジェクトルート（src-tauri の親ディレクトリ）を解決する。
/// 開発時は CARGO_MANIFEST_DIR、配布時は実行ファイルからの相対で探索する。
fn project_root() -> Option<PathBuf> {
    if let Some(manifest) = option_env!("CARGO_MANIFEST_DIR") {
        let root = Path::new(manifest).parent()?.to_path_buf();
        if root.join("app.py").exists() {
            return Some(root);
        }
    }
    // 配布バイナリ向けフォールバック: 実行ファイルの近傍を上方向に探索する。
    let exe = std::env::current_exe().ok()?;
    let mut dir = exe.parent()?.to_path_buf();
    for _ in 0..6 {
        if dir.join("app.py").exists() {
            return Some(dir);
        }
        dir = dir.parent()?.to_path_buf();
    }
    None
}

/// プロジェクト内の venv の Python を優先し、無ければ環境変数や PATH の python3 を使う。
fn resolve_python(root: &Path) -> PathBuf {
    if let Ok(custom) = std::env::var("UPSCALER_PYTHON") {
        if !custom.is_empty() {
            return PathBuf::from(custom);
        }
    }
    let venv = if cfg!(windows) {
        root.join(".venv").join("Scripts").join("python.exe")
    } else {
        root.join(".venv").join("bin").join("python")
    };
    if venv.exists() {
        return venv;
    }
    PathBuf::from(if cfg!(windows) { "python" } else { "python3" })
}

/// Gradio サーバへ TCP 接続できるまで待機する。
fn wait_for_server(host: &str, port: u16, timeout: Duration) -> bool {
    let addr = format!("{host}:{port}");
    let deadline = Instant::now() + timeout;
    while Instant::now() < deadline {
        if TcpStream::connect_timeout(
            &addr.parse().expect("valid socket address"),
            Duration::from_millis(500),
        )
        .is_ok()
        {
            return true;
        }
        thread::sleep(Duration::from_millis(200));
    }
    false
}

/// Python (Gradio) を起動し、標準出力に出る `UPSCALER_URL=...` マーカーから URL を取得する。
fn spawn_server(root: &Path) -> std::io::Result<(Child, String)> {
    let python = resolve_python(root);
    let mut child = Command::new(&python)
        .arg("app.py")
        .current_dir(root)
        .env("UPSCALER_HOST", "127.0.0.1")
        .env("PYTHONUNBUFFERED", "1")
        // 親(本プロセス)が消えたら Python 側も自発終了するよう PID を渡す。
        .env("UPSCALER_PARENT_PID", std::process::id().to_string())
        .stdout(Stdio::piped())
        .stderr(Stdio::inherit())
        .spawn()?;

    let stdout = child
        .stdout
        .take()
        .ok_or_else(|| std::io::Error::other("failed to capture python stdout"))?;

    let (tx, rx) = mpsc::channel::<String>();
    // 子プロセスの stdout を読み続け、URL マーカーを拾ってメインスレッドへ渡す。
    thread::spawn(move || {
        let reader = BufReader::new(stdout);
        for line in reader.lines().map_while(Result::ok) {
            if let Some(url) = line.strip_prefix("UPSCALER_URL=") {
                let _ = tx.send(url.trim().to_string());
            }
            println!("[upscaler] {line}");
        }
    });

    match rx.recv_timeout(Duration::from_secs(60)) {
        Ok(url) => Ok((child, url)),
        Err(_) => {
            let _ = child.kill();
            Err(std::io::Error::other(
                "timed out waiting for UPSCALER_URL marker from python",
            ))
        }
    }
}

/// 起動失敗時に splash 画面へエラーを表示する。
fn show_error(window: &WebviewWindow, message: &str) {
    let escaped = message.replace('\\', "\\\\").replace('`', "\\`");
    let script = format!(
        "if (window.upscalerError) {{ window.upscalerError(`{escaped}`); }} else {{ document.body.innerText = `{escaped}`; }}"
    );
    let _ = window.eval(&script);
}

fn start_backend(window: WebviewWindow, state_handle: tauri::AppHandle) {
    thread::spawn(move || {
        let root = match project_root() {
            Some(root) => root,
            None => {
                show_error(
                    &window,
                    "プロジェクトルート (app.py) が見つかりませんでした。",
                );
                return;
            }
        };

        let (child, url) = match spawn_server(&root) {
            Ok(result) => result,
            Err(err) => {
                show_error(&window, &format!("Python の起動に失敗しました:\n{err}"));
                return;
            }
        };

        // 子プロセスを state に保存し、終了時の kill 対象にする。
        if let Some(server) = state_handle.try_state::<PythonServer>() {
            *server.0.lock().unwrap() = Some(child);
        }

        // URL から host:port を取り出して TCP 接続可能になるまで待つ。
        let (host, port) = parse_host_port(&url).unwrap_or(("127.0.0.1".to_string(), 7860));
        if !wait_for_server(&host, port, Duration::from_secs(90)) {
            show_error(&window, "Gradio サーバへの接続待機がタイムアウトしました。");
            return;
        }

        if let Ok(parsed) = url.parse() {
            let _ = window.navigate(parsed);
        } else {
            show_error(&window, &format!("不正なURLです: {url}"));
        }
    });
}

fn parse_host_port(url: &str) -> Option<(String, u16)> {
    let rest = url.strip_prefix("http://").or_else(|| url.strip_prefix("https://"))?;
    let authority = rest.split('/').next()?;
    let (host, port) = authority.rsplit_once(':')?;
    Some((host.to_string(), port.parse().ok()?))
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    // フロントエンド(Gradio ページ)からは plugin:dialog|open を直接呼ぶため、
    // 自作コマンドは持たない。dialog プラグインだけ登録する。
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_opener::init())
        .manage(PythonServer::default())
        .setup(|app| {
            let window = app
                .get_webview_window("main")
                .expect("main window should exist");
            start_backend(window, app.handle().clone());
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        .run(|app_handle, event| {
            // アプリ終了時に Python プロセスを確実に停止する。
            if let RunEvent::ExitRequested { .. } | RunEvent::Exit = event {
                if let Some(server) = app_handle.try_state::<PythonServer>() {
                    if let Some(mut child) = server.0.lock().unwrap().take() {
                        let _ = child.kill();
                        let _ = child.wait();
                    }
                }
            }
        });
}
