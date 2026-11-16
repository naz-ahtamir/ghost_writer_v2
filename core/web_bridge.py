"""Local Browser Bridge server for keyless xAI Grok Web (grok.com / x.com/i/grok) automation."""

import json
import socket
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urlparse

import config


USERSCRIPT_PATH = Path(__file__).resolve().parent.parent / "scripts" / "grok_web_bridge.user.js"


def _build_dashboard_html(port: int) -> str:
    """Render an interactive dark-mode bridge control panel & manual fallback UI."""
    return f"""<!DOCTYPE html>
<html lang="id">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>GhostWriter AI — Grok Web Bridge (:{port})</title>
<style>
  :root {{
    --bg: #0f172a;
    --card: #1e293b;
    --border: #334155;
    --accent: #38bdf8;
    --green: #22c55e;
    --amber: #f59e0b;
    --text: #f1f5f9;
    --muted: #94a3b8;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    margin: 0; padding: 20px;
    background: var(--bg); color: var(--text);
    font-family: system-ui, -apple-system, sans-serif;
    line-height: 1.5;
  }}
  .container {{ max-width: 820px; margin: 0 auto; }}
  .card {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 18px 20px;
    margin-bottom: 16px;
    box-shadow: 0 8px 24px rgba(0,0,0,0.25);
  }}
  h1 {{ margin: 0 0 6px 0; font-size: 20px; color: var(--accent); }}
  h2 {{ margin: 0 0 10px 0; font-size: 16px; color: #e2e8f0; }}
  p {{ margin: 6px 0; color: var(--muted); font-size: 14px; }}
  .badge {{
    display: inline-flex; align-items: center; gap: 8px;
    padding: 6px 12px; border-radius: 999px;
    font-size: 13px; font-weight: 600;
    background: rgba(245, 158, 11, 0.15); color: var(--amber);
    border: 1px solid var(--amber);
  }}
  .badge.connected {{
    background: rgba(34, 197, 94, 0.15); color: var(--green);
    border-color: var(--green);
  }}
  .btn-row {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 12px; }}
  .btn {{
    display: inline-flex; align-items: center; gap: 6px;
    padding: 9px 15px; border-radius: 9px;
    font-size: 13px; font-weight: 600;
    text-decoration: none; cursor: pointer;
    border: 1px solid transparent;
    transition: opacity 0.15s;
  }}
  .btn:hover {{ opacity: 0.9; }}
  .btn-primary {{ background: var(--accent); color: #0f172a; }}
  .btn-success {{ background: var(--green); color: #052e16; }}
  .btn-outline {{ background: transparent; color: var(--text); border-color: var(--border); }}
  textarea {{
    width: 100%; min-height: 130px;
    background: #0b1120; color: var(--text);
    border: 1px solid var(--border); border-radius: 10px;
    padding: 12px; font-family: ui-monospace, monospace; font-size: 13px;
    resize: vertical; margin-top: 8px;
  }}
  .step-list {{ margin: 8px 0 0 18px; padding: 0; color: var(--muted); font-size: 13.5px; }}
  .step-list li {{ margin-bottom: 6px; }}
  code {{ background: #0b1120; padding: 2px 6px; border-radius: 5px; color: var(--accent); }}
</style>
</head>
<body>
<div class="container">
  <div class="card">
    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;">
      <div>
        <h1>👻 GhostWriter AI — Jembatan Web Grok (Gratis / Tanpa API Key)</h1>
        <p>Server Lokal Aktif di <code>http://127.0.0.1:{port}</code></p>
      </div>
      <div id="conn-badge" class="badge">⏳ Menunggu Tab grok.com...</div>
    </div>
  </div>

  <div class="card">
    <h2>🚀 Cara 1: Mode 100% Otomatis (Direkomendasikan)</h2>
    <ol class="step-list">
      <li>Pasang ekstensi <b>Tampermonkey</b> atau <b>Violentmonkey</b> di browser Anda (PC: Chrome/Edge/Brave/Firefox, Android: Firefox Mobile / Kiwi Browser / Lemur Browser).</li>
      <li>Klik tombol <b>Pasang Userscript Otomatis</b> di bawah ini, lalu tekan <b>Install</b> di tab yang muncul.</li>
      <li>Buka <a href="https://grok.com" target="_blank" style="color:var(--accent)">https://grok.com</a> (atau <a href="https://x.com/i/grok" target="_blank" style="color:var(--accent)">x.com/i/grok</a>) dan pastikan Anda sudah login. Widget <code>👻 GhostWriter Bridge</code> akan muncul di pojok kanan bawah halaman Grok!</li>
    </ol>
    <div class="btn-row">
      <a class="btn btn-primary" href="/grok_web_bridge.user.js" target="_blank">⚡ Pasang Userscript Otomatis (.user.js)</a>
      <a class="btn btn-outline" href="https://grok.com" target="_blank">🌐 Buka grok.com</a>
      <a class="btn btn-outline" href="https://x.com/i/grok" target="_blank">🐦 Buka x.com/i/grok</a>
    </div>
  </div>

  <div class="card">
    <h2>📋 Cara 2: Mode Semi-Otomatis / Relay Cepat (Tanpa Ekstensi Browser)</h2>
    <p>Jika browser Anda belum memasang Tampermonkey, Anda bisa langsung menyalin prompt aktif di bawah ini ke tab <b>grok.com</b> dan menempelkan balasannya di sini:</p>

    <div id="no-task-box" style="padding:14px;background:#0b1120;border-radius:10px;margin-top:10px;color:var(--muted);font-size:13.5px;">
      ✨ Saat ini belum ada antrean prompt dari GhostWriter. Silakan jalankan pembuatan Novel / Bab di terminal GhostWriter.
    </div>

    <div id="active-task-box" style="display:none;margin-top:12px;">
      <div style="display:flex;justify-content:space-between;align-items:center;">
        <strong style="color:var(--amber);font-size:14px;" id="task-title">🔔 Prompt Aktif Menunggu Respons Grok:</strong>
        <span style="font-size:12px;color:var(--muted);" id="task-meta"></span>
      </div>
      <textarea id="prompt-text" readonly></textarea>
      <div class="btn-row">
        <button class="btn btn-primary" onclick="copyPrompt()">📋 1. Salin Prompt</button>
        <a class="btn btn-outline" href="https://grok.com" target="_blank">🌐 2. Buka grok.com</a>
      </div>

      <div style="margin-top:16px;">
        <strong style="color:var(--green);font-size:14px;">📥 3. Tempel Balasan dari Grok di Bawah Ini:</strong>
        <textarea id="response-text" placeholder="Tempel (Paste) hasil balasan dari Grok Web di sini, lalu klik Kirim Balasan..."></textarea>
        <div class="btn-row">
          <button class="btn btn-success" onclick="submitResponse()">✅ Kirim Balasan ke GhostWriter</button>
        </div>
      </div>
    </div>
  </div>
</div>

<script>
let activeTaskId = null;

async function refreshStatus() {{
  try {{
    const r = await fetch('/status');
    const data = await r.json();
    const badge = document.getElementById('conn-badge');
    if (data.userscript_connected) {{
      badge.className = 'badge connected';
      badge.textContent = '🟢 Userscript grok.com Terhubung (Auto Mode)';
    }} else {{
      badge.className = 'badge';
      badge.textContent = '🟡 Menunggu Tab grok.com / Mode Manual Siap';
    }}

    const noTask = document.getElementById('no-task-box');
    const taskBox = document.getElementById('active-task-box');
    if (data.pending_task) {{
      noTask.style.display = 'none';
      taskBox.style.display = 'block';
      if (activeTaskId !== data.pending_task.id) {{
        activeTaskId = data.pending_task.id;
        document.getElementById('prompt-text').value = data.pending_task.prompt;
        document.getElementById('task-meta').textContent = 'ID: ' + activeTaskId.slice(0, 8) + ' | Model: ' + (data.pending_task.model || 'grok-3-web');
      }}
    }} else {{
      activeTaskId = null;
      noTask.style.display = 'block';
      taskBox.style.display = 'none';
    }}
  }} catch (e) {{}}
}}

function copyPrompt() {{
  const el = document.getElementById('prompt-text');
  el.select();
  navigator.clipboard.writeText(el.value);
  alert('Prompt berhasil disalin! Silakan Paste di tab grok.com.');
}}

async function submitResponse() {{
  if (!activeTaskId) return;
  const content = document.getElementById('response-text').value.trim();
  if (!content) {{
    alert('Silakan tempel balasan teks dari Grok terlebih dahulu.');
    return;
  }}
  await fetch('/result', {{
    method: 'POST',
    headers: {{ 'Content-Type': 'application/json' }},
    body: JSON.stringify({{ id: activeTaskId, content: content }})
  }});
  document.getElementById('response-text').value = '';
  activeTaskId = null;
  refreshStatus();
}}

setInterval(refreshStatus, 1200);
refreshStatus();
</script>
</body>
</html>"""


class _BridgeTask:
    """Represents a single pending prompt waiting for a Grok Web response."""

    def __init__(
        self,
        prompt: str,
        model: str = "grok-3-web",
        is_json: bool = False,
    ):
        self.id: str = uuid.uuid4().hex
        self.prompt: str = prompt
        self.model: str = model
        self.is_json: bool = is_json
        self.created_at: float = time.time()
        self.dispatched_at: Optional[float] = None
        self.event: threading.Event = threading.Event()
        self.result_content: Optional[str] = None
        self.error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "prompt": self.prompt,
            "model": self.model,
            "is_json": self.is_json,
            "created_at": self.created_at,
        }


class WebBridgeManager:
    """Thread-safe local HTTP bridge coordinating GhostWriter LLM requests with a grok.com browser tab."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._tasks: List[_BridgeTask] = []
        self._tasks_by_id: Dict[str, _BridgeTask] = {}
        self._server: Optional[ThreadingHTTPServer] = None
        self._port: int = config.WEB_BRIDGE_PORT
        self._last_userscript_poll: float = 0.0

    @property
    def port(self) -> int:
        return self._port

    def get_bridge_url(self) -> str:
        self.ensure_server()
        return f"http://127.0.0.1:{self._port}"

    def is_userscript_connected(self) -> bool:
        """Return True if a browser Userscript polled within the last 10 seconds."""
        return (time.time() - self._last_userscript_poll) < 10.0

    def record_userscript_poll(self) -> None:
        with self._lock:
            self._last_userscript_poll = time.time()

    def enqueue_task(self, prompt: str, model: str = "grok-3-web", is_json: bool = False) -> _BridgeTask:
        task = _BridgeTask(prompt=prompt, model=model, is_json=is_json)
        with self._lock:
            self._tasks.append(task)
            self._tasks_by_id[task.id] = task
        return task

    def claim_next_task_for_userscript(self) -> Optional[Dict[str, Any]]:
        """Return next undispatched task (or re-dispatch if timed out > 90s without result)."""
        self.record_userscript_poll()
        now = time.time()
        with self._lock:
            for task in self._tasks:
                if not task.event.is_set():
                    if task.dispatched_at is None or (now - task.dispatched_at) > 120.0:
                        task.dispatched_at = now
                        return task.to_dict()
        return None

    def peek_active_task(self) -> Optional[Dict[str, Any]]:
        """Peek at the earliest unfinished task without marking it dispatched (used by Dashboard UI)."""
        with self._lock:
            for task in self._tasks:
                if not task.event.is_set():
                    return task.to_dict()
        return None

    def complete_task(self, task_id: str, content: Optional[str] = None, error: Optional[str] = None) -> bool:
        """Store response text or error from browser and wake waiting thread."""
        with self._lock:
            task = self._tasks_by_id.get(task_id)
            if not task:
                # Fallback: if there is only one active task, resolve it
                for candidate in self._tasks:
                    if not candidate.event.is_set():
                        task = candidate
                        break
            if not task:
                return False

            task.result_content = content
            task.error_message = error
            task.event.set()
            if task in self._tasks:
                self._tasks.remove(task)
            return True

    def cancel_task(self, task_id: str) -> None:
        with self._lock:
            task = self._tasks_by_id.pop(task_id, None)
            if task and task in self._tasks:
                self._tasks.remove(task)

    def ensure_server(self) -> int:
        """Start the background HTTP bridge server if not already running."""
        with self._lock:
            if self._server is not None:
                return self._port

            manager = self

            class BridgeRequestHandler(BaseHTTPRequestHandler):
                def _send_cors_headers(self) -> None:
                    self.send_header("Access-Control-Allow-Origin", "*")
                    self.send_header("Access-Control-Allow-Private-Network", "true")
                    self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
                    self.send_header("Access-Control-Allow-Headers", "Content-Type")
                    self.send_header("Cache-Control", "no-store")

                def do_OPTIONS(self) -> None:
                    self.send_response(204)
                    self._send_cors_headers()
                    self.end_headers()

                def do_GET(self) -> None:
                    parsed = urlparse(self.path)
                    path = parsed.path

                    if path == "/poll":
                        task_dict = manager.claim_next_task_for_userscript()
                        payload = json.dumps({"task": task_dict}).encode("utf-8")
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json; charset=utf-8")
                        self._send_cors_headers()
                        self.end_headers()
                        self.wfile.write(payload)
                        return

                    if path == "/status":
                        status_data = {
                            "ok": True,
                            "port": manager.port,
                            "userscript_connected": manager.is_userscript_connected(),
                            "pending_task": manager.peek_active_task(),
                        }
                        payload = json.dumps(status_data).encode("utf-8")
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json; charset=utf-8")
                        self._send_cors_headers()
                        self.end_headers()
                        self.wfile.write(payload)
                        return

                    if path.endswith(".user.js"):
                        if USERSCRIPT_PATH.exists():
                            script_bytes = USERSCRIPT_PATH.read_bytes()
                        else:
                            script_bytes = b"// Userscript file not found"
                        self.send_response(200)
                        self.send_header("Content-Type", "application/javascript; charset=utf-8")
                        self._send_cors_headers()
                        self.end_headers()
                        self.wfile.write(script_bytes)
                        return

                    # Default: Serve interactive dashboard HTML
                    html_bytes = _build_dashboard_html(manager.port).encode("utf-8")
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self._send_cors_headers()
                    self.end_headers()
                    self.wfile.write(html_bytes)

                def do_POST(self) -> None:
                    parsed = urlparse(self.path)
                    if parsed.path == "/result":
                        length = int(self.headers.get("Content-Length", "0") or "0")
                        raw = self.rfile.read(length).decode("utf-8", errors="replace") if length > 0 else "{}"
                        try:
                            data = json.loads(raw)
                        except Exception:
                            data = {}
                        task_id = str(data.get("id", "")).strip()
                        content = data.get("content")
                        error = data.get("error")
                        ok = manager.complete_task(task_id, content=content, error=error)
                        resp_bytes = json.dumps({"ok": ok}).encode("utf-8")
                        self.send_response(200)
                        self.send_header("Content-Type", "application/json; charset=utf-8")
                        self._send_cors_headers()
                        self.end_headers()
                        self.wfile.write(resp_bytes)
                        return

                    self.send_response(404)
                    self._send_cors_headers()
                    self.end_headers()

                def log_message(self, format: str, *args: Any) -> None:
                    # Silence noisy HTTP access logs in CLI
                    return

            preferred_port = config.WEB_BRIDGE_PORT
            for candidate_port in range(preferred_port, preferred_port + 25):
                try:
                    srv = ThreadingHTTPServer(("127.0.0.1", candidate_port), BridgeRequestHandler)
                    srv.daemon_threads = True
                    t = threading.Thread(target=srv.serve_forever, daemon=True)
                    t.start()
                    self._server = srv
                    self._port = candidate_port
                    return candidate_port
                except OSError:
                    continue

            # Fallback to OS-assigned ephemeral port
            srv = ThreadingHTTPServer(("127.0.0.1", 0), BridgeRequestHandler)
            srv.daemon_threads = True
            t = threading.Thread(target=srv.serve_forever, daemon=True)
            t.start()
            self._server = srv
            self._port = int(srv.server_address[1])
            return self._port


# Singleton bridge instance
bridge_manager = WebBridgeManager()


def format_web_prompt(
    prompt: str,
    system_instruction: Optional[str] = None,
    is_json: bool = False,
    messages: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Combine system instruction, multi-turn history, and user prompt into a single clean Web AI message."""
    sections: List[str] = []

    if system_instruction and system_instruction.strip():
        sections.append(f"[INSTRUKSI SISTEM / PERAN AI]\n{system_instruction.strip()}")

    if messages:
        history_lines: List[str] = []
        for msg in messages:
            role = str(msg.get("role", "user")).upper()
            content = str(msg.get("content", "")).strip()
            if not content:
                continue
            if role == "SYSTEM" and system_instruction:
                continue
            history_lines.append(f"[{role}]\n{content}")
        if history_lines:
            sections.append("\n\n".join(history_lines))
    else:
        sections.append(prompt.strip())

    if is_json:
        sections.append(
            "[ATURAN FORMAT OUTPUT WAJIB]\n"
            "Keluarkan HANYA JSON murni yang valid (dimulai dengan '{' atau '[' dan diakhiri dengan '}' atau ']'). "
            "Jangan tambahkan kalimat pengantar, penjelasan, atau komentar di luar JSON."
        )

    return "\n\n" + ("\n\n" + ("=" * 40) + "\n\n").join(sections)


def execute_web_grok_request(
    prompt: str,
    system_instruction: Optional[str] = None,
    model_name: str = "grok-3-web",
    is_json: bool = False,
    messages: Optional[List[Dict[str, Any]]] = None,
    timeout: int = 600,
    log_fn: Optional[Any] = None,
) -> str:
    """Send a prompt to the Grok Web Bridge and wait for the browser response."""
    port = bridge_manager.ensure_server()
    bridge_url = f"http://127.0.0.1:{port}"
    combined_prompt = format_web_prompt(
        prompt=prompt,
        system_instruction=system_instruction,
        is_json=is_json,
        messages=messages,
    )

    task = bridge_manager.enqueue_task(
        prompt=combined_prompt,
        model=model_name,
        is_json=is_json,
    )

    if log_fn:
        if bridge_manager.is_userscript_connected():
            log_fn(
                f"[Grok Web Bridge] 🟢 Terhubung ke tab grok.com! Mengirim prompt #{task.id[:6]} ({len(combined_prompt):,} karakter)..."
            )
        else:
            log_fn(
                f"[Grok Web Bridge] 🌐 Menunggu respons Grok Web di {bridge_url} "
                f"(Buka {bridge_url} untuk pasang Userscript otomatis atau Copy-Paste manual)..."
            )

    try:
        completed = task.event.wait(timeout=timeout)
        if not completed:
            raise TimeoutError(
                f"Waktu tunggu Grok Web Bridge habis ({timeout}s). "
                f"Pastikan tab grok.com terbuka dengan Userscript aktif atau kirim balasan melalui {bridge_url}."
            )
        if task.error_message:
            raise RuntimeError(f"Grok Web Bridge melaporkan kendala: {task.error_message}")
        if not task.result_content or not task.result_content.strip():
            raise RuntimeError("Balasan dari Grok Web kosong.")
        return task.result_content.strip()
    finally:
        bridge_manager.cancel_task(task.id)
