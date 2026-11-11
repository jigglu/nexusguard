#!/usr/bin/env python3
"""
NexusGuard — Web3 Product Launch Video Post-Production Engine
Upgrades raw screen recording `nexusguard_demo.mp4` into:
1. `nexusguard_launch_promo.mp4` (Full Voiceover + Glassmorphic Lower-Thirds, Zero-Overlap)
2. `nexusguard_launch_muted.mp4` (Lower-Thirds Only, Silent Mode)
"""

import os
import sys
import asyncio
import subprocess
import shutil
from pathlib import Path

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont
import edge_tts

ROOT_DIR = Path(__file__).parent.resolve()
SRC_VIDEO = ROOT_DIR / "nexusguard_demo.mp4"
PROMO_OUTPUT = ROOT_DIR / "nexusguard_launch_promo.mp4"
MUTED_OUTPUT = ROOT_DIR / "nexusguard_launch_muted.mp4"
ASSETS_DIR = ROOT_DIR / ".build_assets"

# Frame-accurate trim offset to remove Chromium blank white boot flash
TRIM_START_SEC = 1.233

# 6 Frame-Accurate Scenes with Zero-Overlap Guard Windows
SCENES = [
    {
        "id": 1,
        "banner_start": 0.0,
        "banner_end": 12.0,
        "emoji": "🛡️",
        "title": "NEXUSGUARD ON NEAR",
        "subtitle": "Give AI Agents a Corporate Budget — Never the Raw Keys",
        "accent_rgb": (0, 236, 151),  # NEAR Emerald / Cyan
        "vo_text": "Giving AI agents raw wallet keys is a security nightmare. Meet NexusGuard on NEAR—the autonomous general contractor with hard cryptographic safety.",
        "vo_rate": "+8%",
        "target_start": 0.0,
        "target_end": 12.0,
    },
    {
        "id": 2,
        "banner_start": 12.0,
        "banner_end": 22.8,
        "emoji": "🔐",
        "title": "SCOPED FUNCTION-CALL KEYS",
        "subtitle": "Hard $25 Budget Cap & Human-Approval Gates",
        "accent_rgb": (0, 236, 151),
        "vo_text": "Inside Mission Control, our agent operates strictly on a scoped NEAR Function-Call Access Key. Watch it decompose a full smart contract build and audit within a twenty-five dollar cap.",
        "vo_rate": "+10%",
        "target_start": 12.2,
        "target_end": 22.8,
    },
    {
        "id": 3,
        "banner_start": 22.8,
        "banner_end": 32.0,
        "emoji": "🤝",
        "title": "1-ROUND AI NEGOTIATION",
        "subtitle": "Walks Away From Overpriced Vendors • Settles via NEAR Intents 1Click",
        "accent_rgb": (0, 236, 151),
        "vo_text": "It builds core code for zero dollars, walks away from an overpriced eleven-dollar quote, counters a fallback down to six forty-five, and settles cross-chain on Base via NEAR Intents One-Click.",
        "vo_rate": "+16%",
        "target_start": 23.0,
        "target_end": 32.0,
    },
    {
        "id": 4,
        "banner_start": 32.0,
        "banner_end": 37.3,
        "emoji": "📦",
        "title": "VERIFIED DELIVERABLES",
        "subtitle": "49% Under Budget ($13.80 Saved) • SHA-256 Audited Artifacts",
        "accent_rgb": (0, 236, 151),
        "vo_text": "Every deliverable is hash-verified by QA—finishing forty-nine percent under budget.",
        "vo_rate": "+18%",
        "target_start": 32.2,
        "target_end": 37.3,
    },
    {
        "id": 5,
        "banner_start": 37.3,
        "banner_end": 52.2,
        "emoji": "🚨",
        "title": "LIVE PROMPT-INJECTION DEFENSE",
        "subtitle": "$50 Rogue Drain Halted in <50ms • 8/8 Threat Signals Blocked",
        "accent_rgb": (239, 68, 68),  # Crimson Red Alert
        "vo_text": "Now watch what happens when a rogue auditor hides a prompt injection trying to drain fifty dollars. Our Security Swarm flags eight critical threat signals, blocks the drain cold, and mints a SHA-256 incident receipt.",
        "vo_rate": "+8%",
        "target_start": 37.5,
        "target_end": 52.0,
    },
    {
        "id": 6,
        "banner_start": 52.2,
        "banner_end": 62.5,
        "emoji": "⚡",
        "title": "READY FOR ENTERPRISE & DAOS",
        "subtitle": "Accountant CSV Ledger • Built for #NEARHackathon",
        "accent_rgb": (0, 236, 151),
        "vo_text": "Privileged actions like adding keys or deleting accounts are mathematically impossible. NexusGuard: autonomous agent commerce, secured by NEAR.",
        "vo_rate": "+8%",
        "target_start": 52.5,
        "target_end": 62.4,
    },
]


def get_ffmpeg_exe() -> str:
    return imageio_ffmpeg.get_ffmpeg_exe()


def get_audio_duration(file_path: Path) -> float:
    ffmpeg = get_ffmpeg_exe()
    proc = subprocess.run([ffmpeg, "-i", str(file_path)], capture_output=True, text=True)
    for line in proc.stderr.splitlines():
        if "Duration:" in line:
            t_str = line.split("Duration:")[1].split(",")[0].strip()
            h, m, s = t_str.split(":")
            return float(h) * 3600 + float(m) * 60 + float(s)
    return 0.0


def find_system_fonts():
    """Finds available typography and Apple Color Emoji font."""
    emoji_font_path = "/System/Library/Fonts/Apple Color Emoji.ttc"
    if not os.path.exists(emoji_font_path):
        emoji_font_path = None

    text_font_candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Helvetica.ttc",
        "/System/Library/Fonts/SFProText-Bold.otf",
        "/System/Library/Fonts/Menlo.ttc",
    ]
    text_font_path = None
    for p in text_font_candidates:
        if os.path.exists(p):
            text_font_path = p
            break

    return emoji_font_path, text_font_path


def render_lower_third_banners():
    """Renders high-DPI glassmorphic lower-third banners as transparent 1920x1080 PNGs."""
    print("🎨 [1/4] Rendering Glassmorphic Lower-Third Banners...")
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    emoji_path, text_path = find_system_fonts()

    emoji_font = (
        ImageFont.truetype(emoji_path, 32)
        if emoji_path
        else ImageFont.load_default()
    )
    title_font = (
        ImageFont.truetype(text_path, 20)
        if text_path
        else ImageFont.load_default()
    )
    sub_font = (
        ImageFont.truetype(text_path, 17)
        if text_path
        else ImageFont.load_default()
    )
    div_font = (
        ImageFont.truetype(text_path, 18)
        if text_path
        else ImageFont.load_default()
    )

    for sc in SCENES:
        img = Image.new("RGBA", (1920, 1080), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Measure text width
        t_box = draw.textbbox((0, 0), sc["title"], font=title_font)
        t_w = t_box[2] - t_box[0]
        s_box = draw.textbbox((0, 0), sc["subtitle"], font=sub_font)
        s_w = s_box[2] - s_box[0]

        content_w = 40 + t_w + 18 + 10 + 18 + s_w
        pill_w = max(1160, content_w + 90)
        pill_h = 70
        x1 = (1920 - pill_w) // 2
        y1 = 964
        x2 = x1 + pill_w
        y2 = y1 + pill_h

        # Translucent glassmorphic slate background
        pill_bg = (7, 12, 22, 240)
        color = sc["accent_rgb"]
        border_color = (
            (color[0], color[1], color[2], 120)
            if color[0] == 239
            else (255, 255, 255, 42)
        )
        draw.rounded_rectangle(
            [x1, y1, x2, y2],
            radius=20,
            fill=pill_bg,
            outline=border_color,
            width=1,
        )

        # Glowing left accent capsule
        draw.rounded_rectangle(
            [x1 + 14, y1 + 15, x1 + 20, y2 - 15],
            radius=3,
            fill=color + (255,),
        )

        # Draw content
        cur_x = x1 + 34
        if emoji_path:
            draw.text(
                (cur_x, y1 + 18),
                sc["emoji"],
                font=emoji_font,
                embedded_color=True,
            )
        else:
            draw.text((cur_x, y1 + 23), "•", font=title_font, fill=color + (255,))
        cur_x += 44

        draw.text(
            (cur_x, y1 + 23), sc["title"], font=title_font, fill=color + (255,)
        )
        cur_x += t_w + 16

        draw.text(
            (cur_x, y1 + 23), "|", font=div_font, fill=(100, 116, 139, 200)
        )
        cur_x += 18

        draw.text(
            (cur_x, y1 + 25),
            sc["subtitle"],
            font=sub_font,
            fill=(241, 245, 249, 255),
        )

        out_banner = ASSETS_DIR / f"banner_{sc['id']}.png"
        img.save(out_banner)
        print(f"  ✓ Scene {sc['id']} Lower-Third: {sc['title']} ({pill_w}px)")


async def generate_voiceover_clips():
    """
    Generates 6 neural founder voiceover clips via edge-tts.
    Enforces collision-free timing: each clip is guaranteed to complete
    before the next segment starts, with positive silence gaps.
    """
    print("🎙️  [2/4] Synthesizing Neural Founder Voiceovers (Zero-Overlap Engine)...")
    ffmpeg = get_ffmpeg_exe()

    for sc in SCENES:
        raw_mp3 = ASSETS_DIR / f"vo_{sc['id']}_raw.mp3"
        final_wav = ASSETS_DIR / f"vo_{sc['id']}.wav"

        comm = edge_tts.Communicate(
            sc["vo_text"], "en-US-ChristopherNeural", rate=sc["vo_rate"]
        )
        await comm.save(str(raw_mp3))

        raw_dur = get_audio_duration(raw_mp3)
        max_allowed = sc["target_end"] - sc["target_start"] - 0.25  # 250ms guard buffer

        if raw_dur > max_allowed:
            speed_factor = raw_dur / max_allowed
            print(
                f"  ⚙️  Clip {sc['id']}: raw={raw_dur:.2f}s > max={max_allowed:.2f}s -> tuning tempo={speed_factor:.2f}"
            )
            subprocess.run(
                [
                    ffmpeg,
                    "-y",
                    "-i",
                    str(raw_mp3),
                    "-filter:a",
                    f"atempo={speed_factor:.3f}",
                    "-ar",
                    "44100",
                    "-ac",
                    "2",
                    str(final_wav),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
        else:
            print(f"  ✓ Clip {sc['id']}: raw={raw_dur:.2f}s fits window naturally")
            subprocess.run(
                [
                    ffmpeg,
                    "-y",
                    "-i",
                    str(raw_mp3),
                    "-ar",
                    "44100",
                    "-ac",
                    "2",
                    str(final_wav),
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )


def build_master_audio_track() -> Path:
    """Mixes all 6 voiceover clips into a single timed master audio track."""
    print("🎚️  [3/4] Aligning & Auditing Master Audio Timeline...")
    ffmpeg = get_ffmpeg_exe()
    master_wav = ASSETS_DIR / "master_voiceover.wav"

    # Audit each clip boundary
    print("\n  " + "-" * 60)
    print(f"  {'Clip':<5} | {'Start':<7} | {'End':<7} | {'Duration':<9} | {'Gap to Next'}")
    print("  " + "-" * 60)

    clip_stats = []
    for sc in SCENES:
        wav_path = ASSETS_DIR / f"vo_{sc['id']}.wav"
        dur = get_audio_duration(wav_path)
        start = sc["target_start"]
        end = start + dur
        clip_stats.append((sc["id"], start, end, dur))

    for i in range(len(clip_stats)):
        cid, start, end, dur = clip_stats[i]
        next_start = clip_stats[i + 1][1] if i + 1 < len(clip_stats) else 62.44
        gap = next_start - end
        if gap < 0:
            print(f"  ❌ ERROR: Clip {cid} overlaps by {-gap:.2f}s!")
            sys.exit(1)
        else:
            print(f"  {cid:<5} | {start:>6.2f}s | {end:>6.2f}s | {dur:>7.2f}s  | +{gap:.2f}s silence ✅")
    print("  " + "-" * 60 + "\n")

    cmd = [ffmpeg, "-y"]
    for sc in SCENES:
        cmd.extend(["-i", str(ASSETS_DIR / f"vo_{sc['id']}.wav")])

    filter_parts = []
    for i, sc in enumerate(SCENES):
        delay_ms = int(round(sc["target_start"] * 1000))
        filter_parts.append(f"[{i}:a]adelay={delay_ms}|{delay_ms}[a{i+1}]")

    mix_inputs = "".join(f"[a{i+1}]" for i in range(len(SCENES)))
    filter_parts.append(
        f"{mix_inputs}amix=inputs={len(SCENES)}:dropout_transition=0:normalize=0[aout]"
    )

    filter_str = ";".join(filter_parts)
    cmd.extend(
        [
            "-filter_complex",
            filter_str,
            "-map",
            "[aout]",
            "-t",
            "62.44",
            "-ar",
            "44100",
            "-ac",
            "2",
            str(master_wav),
        ]
    )

    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    print(f"  ✓ Master collision-free audio track compiled: {master_wav.name}")
    return master_wav


def composite_and_export_video(master_audio: Path):
    """Composites trimmed video, lower-third overlays, and master audio into promo & muted MP4s."""
    print("🎬 [4/4] Compositing Final Video Deliverables with FFmpeg...")
    ffmpeg = get_ffmpeg_exe()

    # Step A: Build Promo Video (Video + Lower-Thirds + Founder Voiceover)
    cmd_promo = [
        ffmpeg,
        "-y",
        "-ss",
        str(TRIM_START_SEC),
        "-i",
        str(SRC_VIDEO),
    ]

    for sc in SCENES:
        cmd_promo.extend(["-i", str(ASSETS_DIR / f"banner_{sc['id']}.png")])

    cmd_promo.extend(["-i", str(master_audio)])

    # Construct overlay filter chain using synchronized banner start/end
    overlay_filters = []
    prev_label = "0:v"
    for i, sc in enumerate(SCENES):
        next_label = f"v{i+1}" if i < len(SCENES) - 1 else "vfinal"
        input_idx = i + 1
        overlay_filters.append(
            f"[{prev_label}][{input_idx}:v]overlay=0:0:enable='between(t,{sc['banner_start']},{sc['banner_end']})'[{next_label}]"
        )
        prev_label = next_label

    filter_str = ";".join(overlay_filters)
    audio_idx = len(SCENES) + 1

    cmd_promo.extend(
        [
            "-filter_complex",
            filter_str,
            "-map",
            "[vfinal]",
            "-map",
            f"{audio_idx}:a",
            "-c:v",
            "libx264",
            "-crf",
            "18",
            "-preset",
            "medium",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            str(PROMO_OUTPUT),
        ]
    )

    print("  ⏳ Encoding nexusguard_launch_promo.mp4 (H.264 / AAC 1080p)...")
    res = subprocess.run(
        cmd_promo, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    if res.returncode != 0:
        print("FFmpeg Promo Encoding Error:\n", res.stderr)
        sys.exit(1)

    print(f"  ✓ Exported: {PROMO_OUTPUT.name}")

    # Step B: Export Muted Video (-an) via fast stream copy
    print("  ⏳ Exporting nexusguard_launch_muted.mp4 (Stream Copy, Silent)...")
    cmd_muted = [
        ffmpeg,
        "-y",
        "-i",
        str(PROMO_OUTPUT),
        "-c:v",
        "copy",
        "-an",
        "-movflags",
        "+faststart",
        str(MUTED_OUTPUT),
    ]
    res_muted = subprocess.run(
        cmd_muted, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    )
    if res_muted.returncode != 0:
        print("FFmpeg Muted Export Error:\n", res_muted.stderr)
        sys.exit(1)

    print(f"  ✓ Exported: {MUTED_OUTPUT.name}")


def verify_outputs():
    """Inspects and prints technical diagnostic verification for both output files."""
    ffmpeg = get_ffmpeg_exe()
    print("\n" + "=" * 65)
    print("🔍 VERIFICATION & TECHNICAL AUDIT REPORT")
    print("=" * 65)

    for p in [PROMO_OUTPUT, MUTED_OUTPUT]:
        if not p.exists():
            print(f"❌ ERROR: Missing output file {p.name}")
            continue

        size_mb = p.stat().st_size / (1024 * 1024)
        cmd = [ffmpeg, "-i", str(p)]
        proc = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )

        duration_str = "Unknown"
        video_stream = "None"
        audio_stream = "None"
        for line in proc.stderr.splitlines():
            line_str = line.strip()
            if "Duration:" in line_str:
                duration_str = line_str.split("Duration:")[1].split(",")[0].strip()
            elif "Stream #0:" in line_str and "Video:" in line_str:
                video_stream = line_str.split("Video:")[1].strip()
            elif "Stream #0:" in line_str and "Audio:" in line_str:
                audio_stream = line_str.split("Audio:")[1].strip()

        print(f"\n📦 File: {p.name}")
        print(f"   • Path:        {p}")
        print(f"   • File Size:   {size_mb:.2f} MB (< 50MB Target: {'PASS ✅' if size_mb < 50 else 'FAIL ❌'})")
        print(f"   • Duration:    {duration_str}")
        print(f"   • Video Track: {video_stream}")
        print(f"   • Audio Track: {audio_stream}")

    print("\n" + "=" * 65)
    print("🎉 ALL DELIVERABLES PRODUCED WITH ZERO-OVERLAP AUDIO GUARANTEE!")
    print("=" * 65 + "\n")


def cleanup():
    """Removes temporary build assets directory."""
    if ASSETS_DIR.exists():
        shutil.rmtree(ASSETS_DIR, ignore_errors=True)


def main():
    if not SRC_VIDEO.exists():
        print(f"❌ Source video {SRC_VIDEO} does not exist!")
        sys.exit(1)

    print("🚀 Initializing NexusGuard Zero-Overlap Post-Production Suite...")
    try:
        render_lower_third_banners()
        asyncio.run(generate_voiceover_clips())
        master_audio = build_master_audio_track()
        composite_and_export_video(master_audio)
        verify_outputs()
    finally:
        cleanup()


if __name__ == "__main__":
    main()
