import subprocess
import shutil
import tempfile
from pathlib import Path

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".tiff", ".tif", ".ico", ".avif", ".heic", ".heif"}
VIDEO_EXTS = {".mp4", ".avi", ".mov", ".mkv", ".webm", ".flv", ".wmv", ".m4v", ".3gp", ".ts", ".mts", ".mpeg", ".mpg"}
AUDIO_EXTS = {".mp3", ".wav", ".flac", ".ogg", ".m4a", ".opus", ".aac", ".wma", ".aiff", ".alac"}
ARCHIVE_EXTS = {".zip", ".tar", ".gz", ".bz2", ".7z", ".rar", ".xz"}

IMAGE_TARGETS = ["png", "jpg", "webp", "bmp", "gif", "tiff", "ico"]
VIDEO_TARGETS = ["mp4", "avi", "mov", "mkv", "webm", "gif"]
VIDEO_TO_AUDIO = ["mp3", "wav", "flac", "aac", "opus"]
AUDIO_TARGETS = ["mp3", "wav", "flac", "ogg", "m4a", "opus", "aac"]
ARCHIVE_TARGETS = ["zip", "tar.gz", "tar.bz2", "7z"]


def detect_type(path: Path) -> str:
    name = path.name.lower()

    # двойные суффиксы — tar.gz и т.д.
    if name.endswith((".tar.gz", ".tar.bz2", ".tar.xz", ".tgz", ".tbz2")):
        return "archive"

    suf = path.suffix.lower()
    if suf in IMAGE_EXTS:
        return "image"
    if suf in VIDEO_EXTS:
        return "video"
    if suf in AUDIO_EXTS:
        return "audio"
    if suf in ARCHIVE_EXTS:
        return "archive"

    return "unknown"


def get_targets(file_type: str) -> list:
    if file_type == "image":
        return IMAGE_TARGETS
    if file_type == "video":
        return VIDEO_TARGETS + VIDEO_TO_AUDIO
    if file_type == "audio":
        return AUDIO_TARGETS
    if file_type == "archive":
        return ARCHIVE_TARGETS
    return []


def _convert_image(src: Path, dst: Path) -> tuple[bool, str]:
    try:
        from PIL import Image

        img = Image.open(src)
        ext = dst.suffix.lower()

        # jpeg не понимает прозрачность — заливаем белым
        if ext in (".jpg", ".jpeg"):
            if img.mode in ("RGBA", "LA", "P"):
                bg = Image.new("RGB", img.size, (255, 255, 255))
                if img.mode == "P":
                    img = img.convert("RGBA")
                mask = img.split()[-1] if img.mode in ("RGBA", "LA") else None
                bg.paste(img, mask=mask)
                img = bg
            elif img.mode != "RGB":
                img = img.convert("RGB")

        if ext == ".ico":
            img.save(dst, sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128)])
            return True, ""

        kwargs = {}
        if ext in (".jpg", ".jpeg"):
            kwargs["quality"] = 95
        elif ext == ".webp":
            kwargs["quality"] = 90

        img.save(dst, **kwargs)
        return True, ""
    except Exception as e:
        return False, str(e)


def _convert_ffmpeg(src: Path, dst: Path, ffmpeg_bin: str) -> tuple[bool, str]:
    ext = dst.suffix.lower()

    # gif из видео нормальный — с палитрой
    if ext == ".gif":
        cmd = [
            ffmpeg_bin, "-i", str(src), "-y",
            "-vf", "fps=12,scale=640:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse",
            str(dst),
        ]
    else:
        cmd = [ffmpeg_bin, "-i", str(src), "-y"]

        if ext == ".mp3":
            cmd += ["-codec:a", "libmp3lame", "-qscale:a", "2", "-vn"]
        elif ext == ".flac":
            cmd += ["-codec:a", "flac", "-vn"]
        elif ext == ".ogg":
            cmd += ["-codec:a", "libvorbis", "-qscale:a", "6", "-vn"]
        elif ext == ".opus":
            cmd += ["-codec:a", "libopus", "-b:a", "192k", "-vn"]
        elif ext == ".aac":
            cmd += ["-codec:a", "aac", "-b:a", "256k", "-vn"]
        elif ext == ".wav":
            cmd += ["-codec:a", "pcm_s16le", "-vn"]
        elif ext == ".m4a":
            cmd += ["-codec:a", "aac", "-b:a", "256k", "-vn"]

        cmd.append(str(dst))

    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if r.returncode != 0:
            return False, r.stderr[-1000:]
        return True, ""
    except subprocess.TimeoutExpired:
        return False, "таймаут конвертации"
    except FileNotFoundError:
        return False, "ffmpeg не найден — запусти setup-ffmpeg или поставь через пакетный менеджер"
    except Exception as e:
        return False, str(e)


def _convert_archive(src: Path, dst: Path) -> tuple[bool, str]:
    import zipfile
    import tarfile

    tmp = Path(tempfile.mkdtemp())

    try:
        src_name = src.name.lower()

        # распаковываем что пришло
        if src_name.endswith(".zip"):
            with zipfile.ZipFile(src) as z:
                z.extractall(tmp)
        elif src_name.endswith((".tar.gz", ".tgz")):
            with tarfile.open(src, "r:gz") as t:
                t.extractall(tmp)
        elif src_name.endswith((".tar.bz2", ".tbz2")):
            with tarfile.open(src, "r:bz2") as t:
                t.extractall(tmp)
        elif src_name.endswith((".tar.xz", ".txz")):
            with tarfile.open(src, "r:xz") as t:
                t.extractall(tmp)
        elif src_name.endswith(".tar"):
            with tarfile.open(src, "r:") as t:
                t.extractall(tmp)
        elif src_name.endswith(".7z"):
            import py7zr
            with py7zr.SevenZipFile(src, mode="r") as z:
                z.extractall(tmp)
        elif src_name.endswith(".rar"):
            import rarfile
            with rarfile.RarFile(src) as r:
                r.extractall(tmp)
        else:
            return False, "неизвестный формат архива"

        # пакуем в нужное
        dst_name = dst.name.lower()
        if dst_name.endswith(".zip"):
            with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as z:
                for f in tmp.rglob("*"):
                    if f.is_file():
                        z.write(f, f.relative_to(tmp))
        elif dst_name.endswith(".tar.gz"):
            with tarfile.open(dst, "w:gz") as t:
                for f in tmp.rglob("*"):
                    if f.is_file():
                        t.add(f, arcname=str(f.relative_to(tmp)))
        elif dst_name.endswith(".tar.bz2"):
            with tarfile.open(dst, "w:bz2") as t:
                for f in tmp.rglob("*"):
                    if f.is_file():
                        t.add(f, arcname=str(f.relative_to(tmp)))
        elif dst_name.endswith(".7z"):
            import py7zr
            with py7zr.SevenZipFile(dst, "w") as z:
                for f in tmp.rglob("*"):
                    if f.is_file():
                        z.write(f, str(f.relative_to(tmp)))
        else:
            return False, "неизвестный целевой формат"

        return True, ""
    except Exception as e:
        return False, str(e)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def convert(src: Path, dst: Path, target: str, ffmpeg_bin: str = "ffmpeg") -> tuple[bool, str]:
    file_type = detect_type(src)

    if file_type == "image":
        return _convert_image(src, dst)

    if file_type in ("video", "audio"):
        return _convert_ffmpeg(src, dst, ffmpeg_bin)

    if file_type == "archive":
        return _convert_archive(src, dst)

    # хуй знает что за файл — пусть ffmpeg попробует
    return _convert_ffmpeg(src, dst, ffmpeg_bin)
