import os
import sys
import uuid
import zipfile
import platform
import urllib.request
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file
import converter

FFMPEG_ZIP_URL = "https://www.gyan.dev/ffmpeg/builds/packages/ffmpeg-8.0.1-essentials_build.zip"
FFMPEG_EXES = {"ffmpeg.exe", "ffprobe.exe"}

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 2 * 1024 * 1024 * 1024

UPLOAD_DIR = Path("uploads")
OUTPUT_DIR = Path("outputs")
FFMPEG_DIR = Path("ffmpeg")

UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)


def get_ffmpeg():
    # на windows ищем локальный бинарь
    if platform.system() == "Windows":
        local = FFMPEG_DIR / "ffmpeg.exe"
        if local.exists():
            return str(local)
    return "ffmpeg"


def ffmpeg_ok():
    import subprocess
    try:
        subprocess.run([get_ffmpeg(), "-version"], capture_output=True, check=True, timeout=5)
        return True
    except Exception:
        return False


def do_setup_ffmpeg():
    if platform.system() != "Windows":
        return False, "поставь через apt install ffmpeg или brew install ffmpeg"

    FFMPEG_DIR.mkdir(exist_ok=True)
    zip_path = FFMPEG_DIR / "ffmpeg_dl.zip"

    print("качаю ffmpeg...", flush=True)
    urllib.request.urlretrieve(FFMPEG_ZIP_URL, zip_path)

    print("распаковываю...", flush=True)
    with zipfile.ZipFile(zip_path, "r") as z:
        for name in z.namelist():
            fname = Path(name).name
            if fname in FFMPEG_EXES:
                (FFMPEG_DIR / fname).write_bytes(z.read(name))

    zip_path.unlink()
    return True, "готово"


@app.route("/")
def index():
    return render_template("index.html", ffmpeg_ready=ffmpeg_ok())


@app.route("/api/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return jsonify({"error": "нет файла"}), 400

    f = request.files["file"]
    if not f.filename:
        return jsonify({"error": "имя файла пустое"}), 400

    uid = str(uuid.uuid4())[:8]
    ext = Path(f.filename).suffix
    save_name = uid + ext
    save_path = UPLOAD_DIR / save_name
    f.save(save_path)

    detected = converter.detect_type(save_path)
    targets = converter.get_targets(detected)

    return jsonify({
        "id": uid,
        "filename": f.filename,
        "saved": save_name,
        "type": detected,
        "size": save_path.stat().st_size,
        "targets": targets,
    })


# тут все доступные форматы для валидации
ALL_TARGETS = set(
    converter.IMAGE_TARGETS
    + converter.VIDEO_TARGETS
    + converter.VIDEO_TO_AUDIO
    + converter.AUDIO_TARGETS
    + converter.ARCHIVE_TARGETS
)


@app.route("/api/convert", methods=["POST"])
def convert_file():
    data = request.json or {}
    uid = data.get("id", "")
    saved = data.get("saved", "")
    target = data.get("target", "")
    original = data.get("filename", "file")

    if not all([uid, saved, target]):
        return jsonify({"error": "плохие параметры"}), 400

    if target not in ALL_TARGETS:
        return jsonify({"error": "недопустимый формат"}), 400

    src = UPLOAD_DIR / Path(saved).name
    if not src.exists():
        return jsonify({"error": "файл не найден"}), 404

    out_name = f"{uid}_out.{target}"
    out_path = OUTPUT_DIR / out_name

    ok, err = converter.convert(src, out_path, target, get_ffmpeg())
    if not ok:
        return jsonify({"error": err}), 500

    # чистое имя для скачивания — убираем все суффиксы кроме последнего
    base = Path(Path(original).stem).stem
    result_filename = f"{base}.{target}"

    return jsonify({"result": out_name, "filename": result_filename})


@app.route("/api/download/<path:filename>")
def download(filename):
    # только имя файла, без traversal
    safe = Path(filename).name
    path = OUTPUT_DIR / safe
    if not path.exists():
        return "не найдено", 404
    return send_file(path, as_attachment=True)


@app.route("/api/setup-ffmpeg", methods=["POST"])
def setup_ffmpeg_route():
    ok, msg = do_setup_ffmpeg()
    return jsonify({"ok": ok, "msg": msg, "ffmpeg": ffmpeg_ok()})


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "setup-ffmpeg":
        ok, msg = do_setup_ffmpeg()
        print(msg)
        sys.exit(0 if ok else 1)

    port = int(os.environ.get("PORT", 5000))
    print(f"http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
