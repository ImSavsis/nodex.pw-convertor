const dropzone   = document.getElementById('dropzone');
const fileInput  = document.getElementById('fileInput');
const fileList   = document.getElementById('fileList');
const setupBtn   = document.getElementById('setupFfmpegBtn');

const TYPE_ICONS = {
    image:   '🖼️',
    video:   '🎬',
    audio:   '🎵',
    archive: '📦',
    unknown: '📄',
};

// drag & drop
dropzone.addEventListener('dragover', e => {
    e.preventDefault();
    dropzone.classList.add('drag-over');
});

dropzone.addEventListener('dragleave', e => {
    if (!dropzone.contains(e.relatedTarget)) {
        dropzone.classList.remove('drag-over');
    }
});

dropzone.addEventListener('drop', e => {
    e.preventDefault();
    dropzone.classList.remove('drag-over');
    handleFiles(Array.from(e.dataTransfer.files));
});

// клик на зону — открываем файловый диалог
dropzone.addEventListener('click', e => {
    if (e.target.tagName === 'LABEL' || e.target.closest('label')) return;
    fileInput.click();
});

fileInput.addEventListener('change', () => {
    handleFiles(Array.from(fileInput.files));
    fileInput.value = '';
});

// ctrl+v — вставка картинки из буфера (скриншоты и т.д.)
document.addEventListener('paste', e => {
    const items = Array.from(e.clipboardData?.items || []);
    const files = items
        .filter(i => i.kind === 'file')
        .map(i => i.getAsFile())
        .filter(Boolean);
    if (files.length > 0) handleFiles(files);
});

function handleFiles(files) {
    if (files.length === 0) return;
    fileList.classList.remove('hidden');
    files.forEach(f => uploadFile(f));
}

async function uploadFile(file) {
    const card = makeCard(file.name, 'unknown');
    fileList.prepend(card);

    const status = card.querySelector('.file-status');

    const fd = new FormData();
    fd.append('file', file);

    let data;
    try {
        const r = await fetch('/api/upload', { method: 'POST', body: fd });
        data = await r.json();
        if (!r.ok) throw new Error(data.error || r.statusText);
    } catch (err) {
        setStatus(status, 'ошибка: ' + err.message, 'error');
        return;
    }

    // обновляем иконку и мета-инфо
    const icon = card.querySelector('.file-icon');
    icon.textContent = TYPE_ICONS[data.type] || '📄';
    icon.className = `file-icon ${data.type}`;

    card.querySelector('.file-meta').textContent = data.type + ' · ' + fmtSize(file.size);

    if (data.targets.length === 0) {
        setStatus(status, 'формат не поддерживается', 'error');
        return;
    }

    // строим select + кнопку конвертации
    const actions = card.querySelector('.file-actions');
    actions.innerHTML = '';

    const sel = document.createElement('select');
    sel.className = 'format-select';
    data.targets.forEach(t => {
        const opt = document.createElement('option');
        opt.value = t;
        opt.textContent = t;
        sel.appendChild(opt);
    });

    const btn = document.createElement('button');
    btn.className = 'btn btn-primary';
    btn.textContent = 'конвертировать';
    btn.onclick = () => doConvert(data, sel.value, card);

    setStatus(status, 'готов');

    actions.appendChild(sel);
    actions.appendChild(btn);
}

async function doConvert(uploadData, target, card) {
    const btn    = card.querySelector('.btn-primary');
    const status = card.querySelector('.file-status');

    btn.disabled = true;
    status.innerHTML = '<span class="spinner"></span>конвертирую...';
    status.className = 'file-status';

    // берём актуальное значение select на момент нажатия
    const sel = card.querySelector('.format-select');
    const actualTarget = sel ? sel.value : target;

    let result;
    try {
        const r = await fetch('/api/convert', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                id:       uploadData.id,
                saved:    uploadData.saved,
                target:   actualTarget,
                filename: uploadData.filename,
            }),
        });
        result = await r.json();
        if (!r.ok) throw new Error(result.error || r.statusText);
    } catch (err) {
        const msg = err.message.slice(0, 220);
        setStatus(status, 'ошибка: ' + msg, 'error');
        btn.disabled = false;
        return;
    }

    setStatus(status, 'готово', 'success');
    btn.disabled = false;

    // кнопка скачать — заменяем если уже есть
    const actions = card.querySelector('.file-actions');
    actions.querySelector('.btn-download')?.remove();

    const dl = document.createElement('a');
    dl.href = '/api/download/' + encodeURIComponent(result.result);
    dl.download = result.filename;
    dl.className = 'btn btn-download';
    dl.textContent = 'скачать';
    actions.appendChild(dl);
}

function makeCard(filename, type) {
    const card = document.createElement('div');
    card.className = 'file-card';
    card.innerHTML = `
        <div class="file-icon ${type}">${TYPE_ICONS[type] || '📄'}</div>
        <div class="file-info">
            <div class="file-name" title="${escHtml(filename)}">${escHtml(filename)}</div>
            <div class="file-meta">загрузка...</div>
        </div>
        <div class="file-actions"></div>
        <div class="file-status">—</div>
    `;
    return card;
}

function setStatus(el, text, cls = '') {
    el.textContent = text;
    el.className = 'file-status' + (cls ? ' ' + cls : '');
}

function fmtSize(bytes) {
    if (bytes < 1024)            return bytes + ' B';
    if (bytes < 1024 * 1024)     return (bytes / 1024).toFixed(1) + ' KB';
    if (bytes < 1024 ** 3)       return (bytes / 1024 / 1024).toFixed(1) + ' MB';
    return (bytes / 1024 ** 3).toFixed(2) + ' GB';
}

function escHtml(s) {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

// кнопка setup ffmpeg (только на windows, показывается в шапке)
if (setupBtn) {
    setupBtn.addEventListener('click', async () => {
        setupBtn.textContent = 'качаю...';
        setupBtn.disabled = true;

        try {
            const r = await fetch('/api/setup-ffmpeg', { method: 'POST' });
            const d = await r.json();

            if (d.ffmpeg) {
                setupBtn.closest('.ffmpeg-warn').textContent = '✓ ffmpeg готов — перезагрузи страницу';
            } else {
                setupBtn.textContent = d.msg || 'ошибка';
                setupBtn.disabled = false;
            }
        } catch (e) {
            setupBtn.textContent = 'ошибка сети';
            setupBtn.disabled = false;
        }
    });
}
