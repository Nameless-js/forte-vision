"""Local deterministic video tools. No inference, network calls or retained uploads."""
import base64
import math
import re
import subprocess
from pathlib import Path

import imageio_ffmpeg

VARIANTS = {
    'original': 'null',
    'dark': 'eq=brightness=-0.16:contrast=0.85',
    'blur': 'gblur=sigma=2',
    'occlusion': 'drawbox=x=iw*0.35:y=ih*0.25:w=iw*0.3:h=ih*0.4:color=black:t=fill',
}


def run_ffmpeg(args, timeout=45):
    try:
        result = subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), '-nostdin', '-hide_banner',
            '-threads', '2', '-filter_threads', '1', *args], capture_output=True, timeout=timeout,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    except subprocess.TimeoutExpired as exc:
        raise ValueError('media_timeout') from exc
    return result


def probe(path: Path):
    # ffmpeg -i reports stream metadata without decoding a whole video.
    result = run_ffmpeg(['-protocol_whitelist', 'file,pipe', '-format_whitelist', 'mov,matroska,webm', '-i', str(path)], timeout=10)
    text = result.stderr.decode('utf-8', errors='replace')
    match = re.search(r'Duration: (\d+):(\d+):(\d+(?:\.\d+)?)', text)
    if not match or 'Video:' not in text:
        raise ValueError('invalid_video')
    duration = int(match[1])*3600 + int(match[2])*60 + float(match[3])
    if not math.isfinite(duration) or not 0 < duration <= 600:
        raise ValueError('media_duration')
    return duration


def context_frames(path: Path, timestamp: float, window: float):
    duration = probe(path)
    if timestamp >= duration:
        raise ValueError('invalid_timestamp')
    frames = []
    for role, requested in [('before', timestamp-window), ('moment', timestamp), ('after', timestamp+window)]:
        target = min(max(requested, 0), max(0, duration-.1))
        result = run_ffmpeg(['-loglevel', 'error', '-protocol_whitelist', 'file,pipe',
            '-format_whitelist', 'mov,matroska,webm', '-i', str(path), '-ss', str(target),
            '-frames:v', '1', '-vf', "scale='min(960,iw)':-2", '-q:v', '3',
            '-f', 'image2pipe', '-vcodec', 'mjpeg', '-'])
        if result.returncode or not result.stdout.startswith(b'\xff\xd8\xff'):
            raise ValueError('invalid_video')
        frames.append({'role': role, 'timestamp_sec': round(target, 3),
            'image_base64': base64.b64encode(result.stdout).decode()})
    return {'duration_sec': duration, 'frames': frames,
            'timestamp_note': 'requested_seek_time', 'source': 'local_video_decode'}


def render_video(path: Path, output: Path, kind='original', timestamp=None, window=3):
    duration = probe(path)
    if kind not in VARIANTS:
        raise ValueError('invalid_variant')
    args = ['-loglevel', 'error', '-y', '-protocol_whitelist', 'file,pipe',
            '-format_whitelist', 'mov,matroska,webm', '-i', str(path)]
    if timestamp is not None:
        if timestamp >= duration:
            raise ValueError('invalid_timestamp')
        start = max(0, timestamp-window)
        args += ['-ss', str(start), '-t', str(min(duration, timestamp+window)-start)]
    # Preserve timeline; no temporal cropping for benchmark variants.
    filters = "scale='trunc(min(1280,iw)/2)*2':-2," + VARIANTS[kind]
    args += ['-map', '0:v:0', '-an', '-vf', filters, '-c:v', 'libx264', '-threads', '2',
        '-preset', 'veryfast', '-crf', '24', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(output)]
    result = run_ffmpeg(args, timeout=90)
    if result.returncode or not output.exists() or output.stat().st_size == 0:
        raise ValueError('invalid_video')
    if output.stat().st_size > 100*1024*1024:
        raise ValueError('media_size')
    return output
