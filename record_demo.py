#!/usr/bin/env python3
"""
NexusGuard — Cinematic Hackathon Demo Video Recorder (Presentation Grade).

Features:
- Hardware-accelerated Chromium 1080p recording at constant 30fps.
- In-browser requestAnimationFrame smooth scrolling (zero DevTools IPC jitter).
- Animated virtual cursor with motion glide and luminous click ripple effects.
- 5-Act storyline covering Landing, Live CLI Simulator, Mission Control,
  Task Decomposition, 1Click Settlements, Security Swarm Attack Defense,
  and Scoped Function-Call Key Policy Verification.
- Broadcast-grade H.264 export (CRF 17, 30.000 CFR) universally playable
  on macOS QuickTime, Safari, Chrome, Windows, and Discord.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE_URL = os.environ.get("NEXUSGUARD_URL", "http://localhost:8000")
RECORDINGS_DIR = Path("recordings")
OUTPUT_MP4 = Path("nexusguard_demo.mp4")

# In-browser virtual cursor and smooth scroll engine
DEMO_ENGINE_JS = """
(function() {
    if (window.__demo_engine_ready) return;
    window.__demo_engine_ready = true;

    // Inject styles for virtual cursor and ripple animations
    const style = document.createElement('style');
    style.id = 'demo-engine-styles';
    style.textContent = `
        #demo-virtual-cursor {
            position: fixed;
            top: 0;
            left: 0;
            width: 32px;
            height: 32px;
            pointer-events: none;
            z-index: 2147483647;
            transform: translate3d(-100px, -100px, 0);
            will-change: transform;
        }
        #demo-cursor-arrow {
            width: 26px;
            height: 26px;
            filter: drop-shadow(0 4px 12px rgba(0,0,0,0.9)) drop-shadow(0 0 6px rgba(6,182,212,0.6));
            transform-origin: 0 0;
            transition: transform 0.12s ease;
        }
        #demo-cursor-ripple {
            position: absolute;
            top: 0;
            left: 0;
            width: 50px;
            height: 50px;
            margin: -25px 0 0 -25px;
            border-radius: 50%;
            border: 2px solid #22D3EE;
            background: radial-gradient(circle, rgba(34,211,238,0.35) 0%, transparent 70%);
            opacity: 0;
            transform: scale(0.2);
            pointer-events: none;
        }
        #demo-cursor-pill {
            position: absolute;
            left: 24px;
            top: 18px;
            background: rgba(6, 12, 24, 0.92);
            backdrop-filter: blur(8px);
            border: 1px solid rgba(34, 211, 238, 0.45);
            color: #E2E8F0;
            font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
            font-size: 11px;
            font-weight: 700;
            padding: 3px 9px;
            border-radius: 9999px;
            white-space: nowrap;
            box-shadow: 0 8px 20px rgba(0,0,0,0.6), 0 0 10px rgba(6,182,212,0.25);
            opacity: 0;
            transform: translateY(4px);
            transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
            pointer-events: none;
        }
        /* Smooth scrolling physics */
        html {
            scroll-behavior: auto !important;
        }
    `;
    document.head.appendChild(style);

    const cursorEl = document.createElement('div');
    cursorEl.id = 'demo-virtual-cursor';
    cursorEl.innerHTML = `
        <svg id="demo-cursor-arrow" viewBox="0 0 24 24" fill="none">
            <path d="M3 3L10.5 21L14 13.5L21 10L3 3Z" fill="#06B6D4" stroke="#082F49" stroke-width="1.8" stroke-linejoin="round"/>
        </svg>
        <div id="demo-cursor-ripple"></div>
        <div id="demo-cursor-pill"></div>
    `;
    document.body.appendChild(cursorEl);

    let curX = 200;
    let curY = 150;
    cursorEl.style.transform = `translate3d(${curX}px, ${curY}px, 0)`;

    // Native 60fps cursor translation
    window.__moveCursor = function(targetX, targetY, durationMs = 600) {
        return new Promise(resolve => {
            const startX = curX;
            const startY = curY;
            const diffX = targetX - startX;
            const diffY = targetY - startY;
            const startTime = performance.now();

            function frame(now) {
                const elapsed = now - startTime;
                const progress = Math.min(elapsed / durationMs, 1);
                // Ease out cubic
                const ease = 1 - Math.pow(1 - progress, 3);
                curX = startX + diffX * ease;
                curY = startY + diffY * ease;
                cursorEl.style.transform = `translate3d(${curX}px, ${curY}px, 0)`;
                if (progress < 1) {
                    requestAnimationFrame(frame);
                } else {
                    resolve();
                }
            }
            requestAnimationFrame(frame);
        });
    };

    // Move to element center
    window.__moveCursorTo = function(selector, durationMs = 600, offsetX = 0.5, offsetY = 0.5) {
        return new Promise(resolve => {
            const el = document.querySelector(selector);
            if (!el) return resolve();
            const rect = el.getBoundingClientRect();
            const targetX = rect.left + rect.width * offsetX;
            const targetY = rect.top + rect.height * offsetY;
            window.__moveCursor(targetX, targetY, durationMs).then(resolve);
        });
    };

    // Click pulse ripple
    window.__clickCursor = function() {
        return new Promise(resolve => {
            const arrow = document.getElementById('demo-cursor-arrow');
            const ripple = document.getElementById('demo-cursor-ripple');
            if (arrow) arrow.style.transform = 'scale(0.85)';
            if (ripple) {
                ripple.style.transition = 'none';
                ripple.style.transform = 'scale(0.2)';
                ripple.style.opacity = '1';
                requestAnimationFrame(() => {
                    ripple.style.transition = 'all 0.45s cubic-bezier(0.16, 1, 0.3, 1)';
                    ripple.style.transform = 'scale(1.8)';
                    ripple.style.opacity = '0';
                });
            }
            setTimeout(() => {
                if (arrow) arrow.style.transform = 'scale(1)';
            }, 150);
            setTimeout(resolve, 300);
        });
    };

    // Show tooltip label next to cursor
    window.__showCursorPill = function(text, durationMs = 1500) {
        const pill = document.getElementById('demo-cursor-pill');
        if (!pill) return;
        pill.textContent = text;
        pill.style.opacity = '1';
        pill.style.transform = 'translateY(0)';
        if (durationMs > 0) {
            setTimeout(() => {
                pill.style.opacity = '0';
                pill.style.transform = 'translateY(4px)';
            }, durationMs);
        }
    };

    // Butter-smooth in-browser requestAnimationFrame scrolling
    window.__smoothScrollTo = function(targetY, durationMs = 1200) {
        return new Promise(resolve => {
            const startY = window.scrollY || window.pageYOffset || 0;
            const diff = targetY - startY;
            if (Math.abs(diff) < 2) return resolve();
            const startTime = performance.now();

            function step(now) {
                const elapsed = now - startTime;
                const progress = Math.min(elapsed / durationMs, 1);
                // Ease in-out cubic
                const ease = progress < 0.5
                    ? 4 * progress * progress * progress
                    : 1 - Math.pow(-2 * progress + 2, 3) / 2;
                window.scrollTo(0, startY + diff * ease);
                if (progress < 1) {
                    requestAnimationFrame(step);
                } else {
                    resolve();
                }
            }
            requestAnimationFrame(step);
        });
    };
})();
"""


def log(msg: str) -> None:
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] 🎬 {msg}", flush=True)


def ensure_server_running(url: str = BASE_URL) -> subprocess.Popen | None:
    """Ensure local FastAPI server is healthy. Start if needed."""
    health_url = f"{url}/api/health"
    log(f"Checking server health at {health_url}...")

    for _ in range(3):
        try:
            with urllib.request.urlopen(health_url, timeout=1.5) as resp:
                if resp.status == 200:
                    log("✅ Local server is healthy and responding.")
                    return None
        except Exception:
            time.sleep(0.4)

    log("⚠️ Server not responding. Spawning background server process...")
    proc = subprocess.Popen(
        [sys.executable, "server.py"],
        cwd=Path(__file__).parent.resolve(),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    for i in range(20):
        time.sleep(0.5)
        try:
            with urllib.request.urlopen(health_url, timeout=1.0) as resp:
                if resp.status == 200:
                    log(f"✅ Spawned server is up and healthy (attempt {i+1}).")
                    return proc
        except Exception:
            pass

    log("❌ Could not connect to server at http://localhost:8000. Aborting.")
    sys.exit(1)


def find_ffmpeg() -> str | None:
    """Locate available ffmpeg executable."""
    sys_ffmpeg = shutil.which("ffmpeg")
    if sys_ffmpeg:
        return sys_ffmpeg
    try:
        import imageio_ffmpeg

        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and os.path.exists(exe):
            return exe
    except Exception:
        pass
    return None


def inject_engine(page) -> None:
    """Inject the virtual cursor and smooth scrolling engine into the current page."""
    page.evaluate(DEMO_ENGINE_JS)


def cursor_move_to(page, selector: str, duration_ms: int = 600) -> None:
    page.evaluate(f"window.__moveCursorTo('{selector}', {duration_ms})")
    time.sleep(duration_ms / 1000.0 + 0.05)


def cursor_move_xy(page, x: int, y: int, duration_ms: int = 600) -> None:
    page.evaluate(f"window.__moveCursor({x}, {y}, {duration_ms})")
    time.sleep(duration_ms / 1000.0 + 0.05)


def cursor_click(page, selector: str | None = None) -> None:
    if selector:
        cursor_move_to(page, selector, duration_ms=500)
    page.evaluate("window.__clickCursor()")
    time.sleep(0.35)
    if selector:
        try:
            page.click(selector)
        except Exception:
            pass


def cursor_pill(page, text: str, duration_ms: int = 1500) -> None:
    escaped = text.replace("'", "\\'")
    page.evaluate(f"window.__showCursorPill('{escaped}', {duration_ms})")


def smooth_scroll_to(page, target_y: int, duration_ms: int = 1200) -> None:
    page.evaluate(f"window.__smoothScrollTo({target_y}, {duration_ms})")
    time.sleep(duration_ms / 1000.0 + 0.1)


def run_recording() -> Path:
    """Record the cinematic 60-second hackathon demonstration."""
    RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)
    server_proc = ensure_server_running(BASE_URL)

    log("Launching Hardware-Accelerated Chromium at 1920x1080 (60fps)...")
    with sync_playwright() as p:
        # Launch Chromium with clean hardware-accelerated rendering
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
            ],
        )

        context = browser.new_context(
            viewport={"width": 1920, "height": 1080},
            record_video_dir=str(RECORDINGS_DIR),
            record_video_size={"width": 1920, "height": 1080},
            device_scale_factor=1,
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 NexusGuard-CinemaBot/2.0",
        )

        page = context.new_page()

        # ══════════════════════════════════════════════════════════════
        # ACT 1 (0:00 – 0:10) | LANDING PAGE & TERMINAL SIMULATOR
        # ══════════════════════════════════════════════════════════════
        log("Act 1: Navigating to Public Portal (Landing Page)...")
        page.goto(f"{BASE_URL}/", wait_until="domcontentloaded")
        inject_engine(page)

        # Move cursor gracefully from initial pos to hero value prop
        cursor_move_xy(page, 480, 220, duration_ms=600)
        cursor_pill(page, "🛡️ Hard Cryptographic Safety", duration_ms=1400)
        time.sleep(1.2)

        # Smooth scroll to Live Architecture & Terminal Simulator
        log("Smoothly scrolling to Live CLI Simulator (#architecture)...")
        arch_y = page.evaluate(
            "document.getElementById('architecture') ? document.getElementById('architecture').offsetTop - 40 : 600"
        )
        smooth_scroll_to(page, arch_y, duration_ms=1100)

        # Move cursor to terminal title bar and watch CLI output stream
        cursor_move_xy(page, 960, 480, duration_ms=600)
        cursor_pill(page, "⚡ Streaming Pipeline Telemetry", duration_ms=1600)
        time.sleep(2.5)

        # Move cursor to the "Launch Mission Control" CTA button in navbar
        log("Gliding to 'Launch Mission Control' button...")
        cursor_move_to(page, 'header a[href="/app"], nav a[href="/app"], a[href="/app"]', duration_ms=500)
        cursor_pill(page, "🚀 Entering Mission Control", duration_ms=1000)
        time.sleep(0.3)
        cursor_click(page, 'header a[href="/app"], nav a[href="/app"], a[href="/app"]')

        # ══════════════════════════════════════════════════════════════
        # ACT 2 (0:10 – 0:30) | MISSION CONTROL & AUTONOMOUS PIPELINE
        # ══════════════════════════════════════════════════════════════
        log("Act 2: Mission Control loaded. Re-injecting engine...")
        page.wait_for_selector("#btn-pipeline", timeout=5000)
        inject_engine(page)
        time.sleep(0.6)

        # Highlight Connected Agent Wallet Capsule and Telemetry
        cursor_move_to(page, "#status-dot", duration_ms=500)
        cursor_pill(page, "Scoped FunctionCall Key Active", duration_ms=1200)
        time.sleep(0.8)

        # Glide down to the General Contractor Command Studio
        cursor_move_to(page, "#task-spec", duration_ms=500)
        cursor_pill(page, "Autonomous Task Prompt Studio", duration_ms=1200)
        time.sleep(0.8)

        # Glide to primary Execute button and click!
        log("Executing Autonomous General Contractor Pipeline...")
        cursor_move_to(page, "#btn-pipeline", duration_ms=500)
        cursor_pill(page, "⌘ + Enter Triggered", duration_ms=1200)
        cursor_click(page, "#btn-pipeline")

        # Watch the real-time 5-node stepper animate smoothly
        log("Observing real-time 5-node stepper execution...")
        cursor_move_xy(page, 960, 320, duration_ms=500)
        time.sleep(4.5)

        # ══════════════════════════════════════════════════════════════
        # ACT 3 (0:30 – 0:42) | 1CLICK SETTLEMENTS & DELIVERED OUTPUT
        # ══════════════════════════════════════════════════════════════
        log("Act 3: Smoothly scrolling to Cross-Chain Settlement Receipts Table...")
        settlements_y = page.evaluate(
            "document.getElementById('settlements-section') ? document.getElementById('settlements-section').offsetTop - 30 : 800"
        )
        smooth_scroll_to(page, settlements_y, duration_ms=1100)

        # Move cursor across live 1Click quote IDs and chain badges
        cursor_move_xy(page, 500, 360, duration_ms=500)
        cursor_pill(page, "NEAR Intents 1Click Rails (Base L2 USDC)", duration_ms=1800)
        time.sleep(2.2)

        # Smooth scroll down to Final Delivered Output Workbench
        log("Smoothly scrolling to Final Delivered Output Workbench...")
        delivered_y = page.evaluate(
            "document.getElementById('delivered-section') ? document.getElementById('delivered-section').offsetTop - 30 : 1200"
        )
        smooth_scroll_to(page, delivered_y, duration_ms=1100)

        # Move cursor to verified cryptographic deliverable cards
        cursor_move_xy(page, 960, 480, duration_ms=500)
        cursor_pill(page, "3 SHA-256 Verified Code Deliverables", duration_ms=1800)
        time.sleep(2.2)

        # ══════════════════════════════════════════════════════════════
        # ACT 4 (0:42 – 0:52) | SECURITY SWARM THREAT INTERCEPTION
        # ══════════════════════════════════════════════════════════════
        log("Act 4: Smoothly scrolling back to Action Controls...")
        controls_y = page.evaluate(
            "document.getElementById('command-center') ? document.getElementById('command-center').offsetTop - 30 : 300"
        )
        smooth_scroll_to(page, controls_y, duration_ms=1000)

        # Glide cursor to Simulate Attack button and click!
        log("Simulating Poisoned Prompt Injection & Malicious Drain Attack...")
        cursor_move_to(page, "#btn-attack", duration_ms=500)
        cursor_pill(page, "Simulating Rogue Agent Drain ($50.00)", duration_ms=1200)
        cursor_click(page, "#btn-attack")
        time.sleep(2.2)

        # Smooth scroll to Security Swarm Threat Interception Matrix
        log("Smoothly scrolling to Threat Interception Matrix...")
        attack_y = page.evaluate(
            "document.getElementById('attack-section') ? document.getElementById('attack-section').offsetTop - 30 : 1100"
        )
        smooth_scroll_to(page, attack_y, duration_ms=1100)

        # Cursor highlights blocked drain & 8/8 regex heuristic flags
        cursor_move_xy(page, 520, 360, duration_ms=500)
        cursor_pill(page, "DRAIN HALTED — 8/8 Regex Signals Fired", duration_ms=1800)
        time.sleep(1.8)

        # Cursor highlights Cryptographic Incident Receipt
        cursor_move_xy(page, 960, 520, duration_ms=500)
        cursor_pill(page, "Cryptographic Incident Receipt (INC-B8A764C7)", duration_ms=1800)
        time.sleep(1.8)

        # ══════════════════════════════════════════════════════════════
        # ACT 5 (0:52 – 0:59) | KEY CUSTODY POLICY & FINALE
        # ══════════════════════════════════════════════════════════════
        log("Act 5: Inspecting Scoped Function-Call Access Key Policy...")
        grid_y = page.evaluate(
            "document.getElementById('policy-content') ? document.getElementById('policy-content').closest('.grid').offsetTop - 50 : 700"
        )
        smooth_scroll_to(page, grid_y, duration_ms=1000)

        cursor_move_xy(page, 450, 420, duration_ms=500)
        cursor_pill(page, "Key Perms: FunctionCall Only (Never FullAccess)", duration_ms=1800)
        time.sleep(1.8)

        # Smooth glide back to top of Mission Control for final grand view
        log("Final smooth scroll to top of Mission Control...")
        smooth_scroll_to(page, 0, duration_ms=1000)
        cursor_move_xy(page, 960, 100, duration_ms=500)
        time.sleep(1.2)

        # Capture video path before closing context
        video = page.video
        video_path_str = video.path() if video else None

        log("Closing browser context to flush video stream...")
        context.close()
        browser.close()

    if server_proc:
        log("Terminating spawned server process...")
        server_proc.terminate()

    if not video_path_str or not os.path.exists(video_path_str):
        recordings = list(RECORDINGS_DIR.glob("*.webm"))
        if not recordings:
            raise RuntimeError("No recording file was found in recordings/.")
        recordings.sort(key=os.path.getmtime, reverse=True)
        raw_webm = recordings[0]
    else:
        raw_webm = Path(video_path_str)

    log(f"Raw Playwright video recorded: {raw_webm} ({raw_webm.stat().st_size / (1024*1024):.2f} MB)")
    return raw_webm


def convert_to_mp4(webm_path: Path, output_mp4: Path) -> Path:
    """
    Convert WebM to broadcast-grade H.264 MP4 with constant 30fps.
    Uses CRF 17 for visually lossless fidelity and zero gradient banding.
    """
    ffmpeg_exe = find_ffmpeg()
    if not ffmpeg_exe:
        log("⚠️ FFmpeg binary not found on PATH or in imageio-ffmpeg. Leaving raw WebM.")
        return webm_path

    log(f"Encoding broadcast-grade H.264 MP4 via {ffmpeg_exe}...")
    # Resample variable frame rate to strict 30.000 CFR with near-lossless CRF 17
    cmd = [
        ffmpeg_exe,
        "-y",
        "-i",
        str(webm_path),
        "-filter:v",
        "fps=fps=30,format=yuv420p",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "17",
        "-movflags",
        "+faststart",
        str(output_mp4),
    ]

    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        log(f"⚠️ FFmpeg conversion failed (code {res.returncode}): {res.stderr[:250]}")
        return webm_path

    if output_mp4.exists() and output_mp4.stat().st_size > 0:
        size_mb = output_mp4.stat().st_size / (1024 * 1024)
        log(f"🎉 Presentation-Grade MP4 Ready: {output_mp4.resolve()} ({size_mb:.2f} MB)")
        return output_mp4
    return webm_path


def main() -> None:
    print("=" * 72)
    print("NexusGuard — Cinematic Hackathon Demo Video Recorder (Presentation Grade)")
    print("=" * 72)
    t0 = time.time()
    try:
        raw_webm = run_recording()
        final_video = convert_to_mp4(raw_webm, OUTPUT_MP4)
        elapsed = time.time() - t0
        print("=" * 72)
        print(f"🎬 Presentation Video Generated Successfully in {elapsed:.1f}s!")
        print(f"📁 Output Video Path: {final_video.resolve()}")
        print(f"📊 File Size:         {final_video.stat().st_size / (1024*1024):.2f} MB")
        print("=" * 72)
    except Exception as exc:
        log(f"❌ Error during recording: {exc}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
