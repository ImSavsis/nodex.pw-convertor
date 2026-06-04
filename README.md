# nodex.pw converter

конвертирует всё что возможно — картинки, видео, аудио, архивы  
веб-интерфейс, drag & drop, ctrl+v, автоопределение форматов

---

## что нужно

- python 3.10+
- ffmpeg (для видео и аудио, см. ниже)

---

## установка

```
pip install -r requirements.txt
```

ffmpeg на **windows** — скачается сам при первом запуске (кнопка в шапке)  
или вручную:

```
python app.py setup-ffmpeg
```

на **linux/mac**:

```
sudo apt install ffmpeg
# или
brew install ffmpeg
```

---

## запуск

```
python app.py
```

открывай `http://localhost:5000`

порт можно поменять через `PORT=8080 python app.py`

---

## что конвертирует

**изображения**

| формат | → |
|--------|---|
| jpg, png, webp, bmp, gif, tiff, ico, avif, heic | любой из этих |

webp → png, heic → jpg, gif → webp — всё работает через pillow

**видео**

| формат | → |
|--------|---|
| mp4, avi, mov, mkv, webm, flv, wmv, m4v... | mp4, avi, mov, mkv, webm, gif |
| любое видео | mp3, wav, flac, aac, opus (вытащить аудио) |

**аудио**

| формат | → |
|--------|---|
| mp3, wav, flac, ogg, m4a, opus, aac, wma, aiff | любой из этих |

**архивы**

| формат | → |
|--------|---|
| zip, tar.gz, tar.bz2, tar.xz, 7z, rar | zip, tar.gz, tar.bz2, 7z |

для rar нужен системный `unrar` — `apt install unrar`  
7z работает без внешних зависимостей (py7zr)

---

## как использовать

1. открываешь браузер
2. кидаешь файл в зону или нажимаешь "выбери файлы"
3. ctrl+v — вставить картинку из буфера (скриншоты работают)
4. выбираешь целевой формат
5. жмёшь конвертировать, скачиваешь

---

## структура

```
app.py           — сервер flask, эндпоинты upload/convert/download
converter.py     — логика конвертации (pillow + ffmpeg + архивы)
templates/
  index.html     — фронт
static/
  style.css
  app.js
uploads/         — временные загрузки
outputs/         — результаты
ffmpeg/          — ffmpeg.exe / ffprobe.exe (windows)
requirements.txt
```

---

## зависимости

```
flask       — веб-сервер
pillow      — изображения
py7zr       — 7z архивы (чистый python)
rarfile     — rar архивы (нужен системный unrar)
```

ffmpeg ставится отдельно — через пакетный менеджер или кнопку в интерфейсе
