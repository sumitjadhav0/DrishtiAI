"""stream.py - Smooth live video + HUD (corner overlays).
Video Streamlit madhun nahi, browser cha native MJPEG stream (/video) ne jato -> lag nahi.
HUD (FPS, latency, CPU, model, place, listening wave, caption) HTML/CSS ne video chya kone-kopryat.
Open:  http://localhost:8765   (Streamlit madhe pan embed hota)"""
import ipaddress
import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import cv2
import numpy as np
import psutil

import config

HUD_HTML = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Mitra</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%;background:#07090c;color:#fff;overflow:hidden;
  font-family:system-ui,-apple-system,"Segoe UI",Roboto,"Noto Sans","Noto Sans Devanagari",sans-serif}
#wrap{position:relative;width:100%;height:100%;background:#000}
#video{position:absolute;inset:0;width:100%;height:100%;object-fit:contain;background:#000}
.hud{position:absolute;display:flex;gap:8px;align-items:center;z-index:5;pointer-events:none}
.hud *{pointer-events:auto}
.tl{top:12px;left:12px}.tr{top:12px;right:12px;justify-content:flex-end;flex-wrap:wrap;max-width:60%}
.tc{top:12px;left:50%;transform:translateX(-50%)}
.bl{bottom:14px;left:14px}.br{bottom:14px;right:14px}
.bc{bottom:78px;left:50%;transform:translateX(-50%);width:min(86%,820px);justify-content:center}
.chip{background:rgba(10,12,16,.55);backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);
  border:1px solid rgba(255,255,255,.12);border-radius:12px;padding:7px 11px;font-size:13px;line-height:1.1;
  white-space:nowrap;box-shadow:0 2px 10px rgba(0,0,0,.35)}
.chip b{font-size:17px;font-weight:650;margin-right:3px;font-variant-numeric:tabular-nums}
.chip small{opacity:.65;font-size:11px;letter-spacing:.04em;text-transform:uppercase}
.good b{color:#4ade80}.warn b{color:#fbbf24}.bad b{color:#f87171}
#nav{background:rgba(37,99,235,.75);border-color:rgba(147,197,253,.5);font-size:14px;display:none}
#caption{background:rgba(10,12,16,.62);border-radius:14px;padding:10px 16px;font-size:16px;line-height:1.35;
  text-align:center;display:none;white-space:normal;max-width:100%}
#statebox{display:flex;align-items:center;gap:12px;padding:9px 15px 9px 12px}
#wave{display:flex;align-items:center;gap:3px;height:30px}
#wave i{display:block;width:4px;height:6px;border-radius:3px;background:var(--c,#9ca3af);transition:background .3s}
#state{font-size:14px;font-weight:600;color:var(--c,#9ca3af)}
#mic{font-size:11px;opacity:.6;display:block;margin-top:2px;max-width:170px;overflow:hidden;text-overflow:ellipsis;font-weight:400;color:#fff}
@keyframes bar{0%,100%{height:6px}50%{height:var(--h,22px)}}
#wave[data-s=listening] i{animation:bar 1.5s ease-in-out infinite}
#wave[data-s=thinking] i{animation:bar .9s ease-in-out infinite}
#wave[data-s=speaking] i{animation:bar .45s ease-in-out infinite;--h:28px}
#wave i:nth-child(1){animation-delay:0s;--h:14px}#wave i:nth-child(2){animation-delay:.12s}
#wave i:nth-child(3){animation-delay:.24s;--h:28px}#wave i:nth-child(4){animation-delay:.08s;--h:20px}
#wave i:nth-child(5){animation-delay:.2s;--h:26px}#wave i:nth-child(6){animation-delay:.04s}
#wave i:nth-child(7){animation-delay:.16s;--h:12px}
#btn{cursor:pointer;border:0;border-radius:12px;padding:11px 18px;font-size:14px;font-weight:650;color:#fff;
  background:#16a34a;box-shadow:0 2px 10px rgba(0,0,0,.4)}
#btn.stop{background:#dc2626}
#conn{position:absolute;inset:0;display:none;align-items:center;justify-content:center;background:rgba(0,0,0,.7);
  font-size:18px;z-index:9}
@media (max-width:640px){
  .chip{font-size:11px;padding:5px 8px}.chip b{font-size:14px}
  .tr{top:50px;left:12px;right:auto;max-width:calc(100% - 24px);justify-content:flex-start}
  .tc{top:88px;left:12px;transform:none}
  #caption{font-size:14px}}
</style></head>
<body><div id="wrap">
  <img id="video" src="/video" alt="live video">
  <div class="hud tl">
    <div class="chip" id="c_fps"><b id="fps">--</b><small>FPS</small></div>
    <div class="chip" id="c_lat"><b id="lat">--</b><small>ms latency</small></div>
    <div class="chip"><b id="cpu">--</b><small>% CPU</small></div>
  </div>
  <div class="hud tc"><div class="chip" id="nav"></div></div>
  <div class="hud tr">
    <div class="chip" id="place" style="display:none">📍 <span></span></div>
    <div class="chip" id="model"><small>MODEL</small> <span id="modelv">--</span></div>
    <div class="chip" id="lang">--</div>
  </div>
  <div class="hud bc"><div class="chip" id="caption"></div></div>
  <div class="hud bl"><div class="chip" id="statebox">
    <div id="wave" data-s="off"><i></i><i></i><i></i><i></i><i></i><i></i><i></i></div>
    <div><span id="state">Idle</span><span id="mic"></span></div></div></div>
  <div class="hud br"><div class="chip" id="guide" style="display:none">🔕 Quiet mode</div>
    <button id="btn">▶ Start</button></div>
  <div id="conn">Reconnecting to Mitra…</div>
</div>
<script>
const $ = id => document.getElementById(id);
const ST = {listening:["🎤 Listening","#4ade80"], thinking:["💭 Thinking","#fbbf24"],
            speaking:["🔊 Speaking","#60a5fa"], off:["⏸ Idle","#9ca3af"], error:["⚠ Mic problem","#f87171"]};
let running = false, fails = 0;
function level(el, v, goodMax, warnMax){ el.className = "chip " + (v <= goodMax ? "good" : v <= warnMax ? "warn" : "bad"); }
async function tick(){
  try{
    const r = await fetch("/stats", {cache:"no-store"}); const s = await r.json(); fails = 0;
    running = s.running;
      if (s.error){ $("conn").textContent = "Mitra error: " + s.error; $("conn").style.display = "flex"; }
      else { $("conn").textContent = "Reconnecting to Mitra."; $("conn").style.display = "none"; }
    $("fps").textContent = s.running ? s.fps.toFixed(1) : "--";
    $("lat").textContent = s.running ? Math.round(s.latency_ms) : "--";
    $("cpu").textContent = Math.round(s.cpu);
    if (s.running){ level($("c_lat"), s.latency_ms, 300, 700); level($("c_fps"), -s.fps, -5, -2); }
    $("modelv").textContent = s.model || "--";
    $("lang").textContent = ({en:"EN", hi:"हिं", mr:"मरा"})[s.lang] || s.lang;
    const pl = $("place"); pl.style.display = s.place ? "block" : "none"; pl.lastElementChild.textContent = s.place;
    const nv = $("nav"); nv.style.display = s.nav ? "block" : "none"; nv.textContent = s.nav ? "🧭 " + s.nav : "";
    const cap = $("caption"); cap.style.display = s.caption ? "block" : "none"; cap.textContent = s.caption;
    const st = ST[s.state] || ST.off; $("state").textContent = st[0];
    $("wave").dataset.s = s.state; $("statebox").style.setProperty("--c", st[1]);
    $("wave").style.setProperty("--c", st[1]); $("state").style.setProperty("--c", st[1]);
    $("mic").textContent = s.mic || "";
    $("guide").style.display = (s.running && !s.guide) ? "block" : "none";
    const b = $("btn"); b.textContent = s.running ? "⏹ Stop" : "▶ Start"; b.className = s.running ? "stop" : "";
  }catch(e){ if (++fails > 3) $("conn").style.display = "flex"; }
  setTimeout(tick, 350);
}
$("btn").onclick = async () => { $("btn").disabled = true;
  try{ await fetch(running ? "/api/stop" : "/api/start", {method:"POST"}); }catch(e){}
  setTimeout(() => $("btn").disabled = false, 800); };
$("video").onerror = () => setTimeout(() => $("video").src = "/video?" + Date.now(), 1000);
tick();
</script></body></html>
"""


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *a):
        pass

    def _send(self, code, ctype, body):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        app = self.server.app
        path = self.path.split("?")[0]
        if path in ("/", "/index.html"):
            self._send(200, "text/html; charset=utf-8", HUD_HTML.encode("utf-8"))
        elif path == "/stats":
            self._send(200, "application/json", json.dumps(app.stats(), ensure_ascii=False).encode("utf-8"))
        elif path == "/video":
            self._stream(app)
        else:
            self._send(404, "text/plain", b"not found")

    def _allow_control_request(self):
        origin = self.headers.get("Origin")
        if origin:
            return origin == f"http://{self.headers.get('Host', '')}"
        try:
            return ipaddress.ip_address(self.client_address[0]).is_loopback
        except ValueError:
            return False

    def do_POST(self):
        app = self.server.app
        if not self._allow_control_request():
            self._send(403, "text/plain", b"forbidden")
            return
        if self.headers.get("Transfer-Encoding") or self.headers.get("Content-Length", "0") not in ("", "0"):
            self._send(400, "text/plain", b"request body not supported")
            return
        if self.path == "/api/start":
            threading.Thread(target=app.safe_start, daemon=True).start()
            self._send(200, "application/json", b'{"ok":true}')
        elif self.path == "/api/stop":
            app.p.stop()
            self._send(200, "application/json", b'{"ok":true}')
        else:
            self._send(404, "text/plain", b"not found")

    def _stream(self, app):
        self.send_response(200)
        self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Connection", "close")
        self.end_headers()
        last_id, last_write = -1, 0.0
        try:
            while not app._stop:
                jpeg, jid = app.wait_frame(last_id, 1.0)
                if jid == last_id and time.time() - last_write < 1.0:
                    continue
                self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\nContent-Length: %d\r\n\r\n" % len(jpeg))
                self.wfile.write(jpeg)
                self.wfile.write(b"\r\n")
                last_id, last_write = jid, time.time()
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError, OSError):
            return


class StreamServer:
    def __init__(self, pipeline, host=None, port=None):
        self.p = pipeline
        self.host = host or ("0.0.0.0" if config.STREAM_LAN else "127.0.0.1")
        self.port = port or config.STREAM_PORT
        self.jpeg, self.jid = None, 0
        self.cond = threading.Condition()
        self.cpu = 0.0
        self.error = ""
        self._stop = False
        self.httpd = None
        self.idle = self._make_idle()

    # ---------------- helpers ----------------
    @staticmethod
    def _make_idle():
        img = np.full((480, 640, 3), 16, np.uint8)
        cv2.putText(img, "Mitra", (250, 220), cv2.FONT_HERSHEY_SIMPLEX, 1.6, (230, 230, 230), 3)
        cv2.putText(img, "Press Start", (225, 275), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (150, 150, 150), 2)
        return cv2.imencode(".jpg", img)[1].tobytes()

    def start(self):
        for port in range(self.port, self.port + 10):          # port busy asel tar pudhcha
            try:
                self.httpd = ThreadingHTTPServer((self.host, port), _Handler)
                self.port = port
                break
            except OSError:
                continue
        if self.httpd is None:
            raise RuntimeError("Stream port milala nahi")
        self.httpd.daemon_threads = True
        self.httpd.app = self
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()
        threading.Thread(target=self._encoder, daemon=True).start()
        return self

    def stop(self):
        self._stop = True
        if self.httpd:
            self.httpd.shutdown()

    def url(self):
        return "http://localhost:%d/" % self.port

    def safe_start(self):
        try:
            self.p.start()
            self.error = ""
        except Exception as e:
            self.error = str(e)

    def wait_frame(self, last_id, timeout):
        with self.cond:
            if self.jid == last_id:
                self.cond.wait(timeout)
            return (self.jpeg or self.idle), self.jid

    def _publish(self, jpeg):
        with self.cond:
            self.jpeg = jpeg
            self.jid += 1
            self.cond.notify_all()

    def _draw(self, img):
        p = self.p
        if not config.SHOW_BOXES or time.time() - p.last_dets_t > 1.0:
            return
        h, w = img.shape[:2]
        for d in p.last_dets:
            x1, y1, x2, y2 = d["box"]
            a, b = (int(x1 * w), int(y1 * h)), (int(x2 * w), int(y2 * h))
            cv2.rectangle(img, a, b, (80, 220, 120), 2)
            cv2.putText(img, d["label"], (a[0] + 2, max(a[1] - 6, 14)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (80, 220, 120), 1,
                        cv2.LINE_AA)

    # ---------------- encoder: camera fps var, inference chya swatantra ----------------
    def _encoder(self):
        last_id, was_running, t_cpu = -1, False, 0.0
        q = [cv2.IMWRITE_JPEG_QUALITY, config.JPEG_QUALITY]
        while not self._stop:
            t0 = time.time()
            p = self.p
            if t0 - t_cpu > 1.0:
                self.cpu, t_cpu = psutil.cpu_percent(interval=None), t0
            frame = p.live_frame if p.running else None
            if frame is not None and p.live_id != last_id:
                last_id = p.live_id
                img = frame.copy()
                self._draw(img)
                ok, buf = cv2.imencode(".jpg", img, q)
                if ok:
                    self._publish(buf.tobytes())
                    was_running = True
            elif not p.running and (was_running or self.jpeg is None):
                self._publish(self.idle)
                was_running = False
            time.sleep(max(0.002, 1.0 / config.STREAM_FPS - (time.time() - t0)))

    # ---------------- stats (HUD) ----------------
    def stats(self):
        p = self.p
        v = p.voice
        state = v.state if (v and p.running) else "off"
        segs = p.speaker.last_segments
        said = " ".join(t for t, _ in segs) if segs else ""
        nid = p.current_node()
        if nid and nid in p.navmap.nodes:
            place = p.navmap.nodes[nid]["name"]
        else:
            place = p.place.replace("_", " ") if p.place else ""
        nav = ""
        if p.navigator.active:
            nav = "%s  ·  %s" % (p.navmap.nodes[p.navigator.target]["name"], p.navigator.status())
        return {
            "running": bool(p.running), "fps": float(p.fps), "latency_ms": float(p.latency_ms), "cpu": float(self.cpu),
            "model": p.last_model if p.running else "", "place": place, "nav": nav,
            "caption": (said or ("" if p.last_sentence == "-" else p.last_sentence))[:160] if p.running else "",
            "state": state, "guide": bool(p.guide_enabled), "lang": p.lang,
            "mic": (v.device_name if v else ""), "error": self.error,
        }
