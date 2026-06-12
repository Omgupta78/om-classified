#!/usr/bin/env python3
"""Build the static Shree Classified e-paper site from the editions/ folder.

Each subfolder of editions/ is one weekly edition, named by publish date:

    editions/2026-06-12/01.jpg, 02.jpg, ...   page images (sorted by filename)
    editions/2026-06-12/edition.pdf            optional full-edition PDF
    editions/2026-06-12/title.txt              optional custom title

Output is written to public/ and served by GitLab Pages.
Uses only the Python standard library.
"""
import html
import json
import os
import shutil
from datetime import datetime
from string import Template

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EDITIONS_DIR = os.path.join(BASE_DIR, 'editions')
OUTPUT_DIR = os.path.join(BASE_DIR, 'public')
CSS_SOURCE = os.path.join(BASE_DIR, 'static', 'css', 'style.css')
IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}

LAYOUT = Template('''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>$title</title>
  <link rel="stylesheet" href="css/style.css">
</head>
<body>
  <header class="site-header">
    <div class="masthead">
      <a href="index.html" class="brand"><span class="brand-shree">Shree</span> <span class="brand-classified">Classified</span></a>
      <p class="tagline">Your Weekly Classified E-Paper</p>
    </div>
    <nav class="main-nav">
      <a href="index.html">Latest Edition</a>
      <a href="archive.html">Archive</a>
    </nav>
  </header>
  <main class="content">
$content
  </main>
  <footer class="site-footer">
    <p>&copy; Shree Classified &mdash; Published weekly. For advertisements contact: <strong>+91-XXXXXXXXXX</strong> | <strong>shreeclassified@example.com</strong></p>
  </footer>
$scripts
</body>
</html>
''')

VIEWER_JS = Template('''<script>
  const pageFiles = $page_files;
  let current = 0;
  let zoom = 1;
  const img = document.getElementById('page-image');
  const indicator = document.getElementById('page-indicator');
  const download = document.getElementById('download-link');
  const thumbs = document.querySelectorAll('.thumb');
  function show(index) {
    current = Math.max(0, Math.min(index, pageFiles.length - 1));
    img.src = pageFiles[current];
    download.href = pageFiles[current];
    indicator.textContent = 'Page ' + (current + 1) + ' / ' + pageFiles.length;
    thumbs.forEach((t, i) => t.classList.toggle('active', i === current));
  }
  function applyZoom() { img.style.width = (zoom * 100) + '%'; }
  document.getElementById('prev-btn').onclick = () => show(current - 1);
  document.getElementById('next-btn').onclick = () => show(current + 1);
  document.getElementById('zoom-in-btn').onclick = () => { zoom = Math.min(zoom + 0.25, 3); applyZoom(); };
  document.getElementById('zoom-out-btn').onclick = () => { zoom = Math.max(zoom - 0.25, 0.5); applyZoom(); };
  thumbs.forEach(t => t.onclick = () => show(parseInt(t.dataset.index, 10)));
  document.addEventListener('keydown', e => {
    if (e.key === 'ArrowLeft') show(current - 1);
    if (e.key === 'ArrowRight') show(current + 1);
  });
  applyZoom();
</script>''')


def load_editions():
    """Return editions sorted newest first."""
    editions = []
    if not os.path.isdir(EDITIONS_DIR):
        return editions
    for name in sorted(os.listdir(EDITIONS_DIR), reverse=True):
        folder = os.path.join(EDITIONS_DIR, name)
        if not os.path.isdir(folder):
            continue
        files = sorted(os.listdir(folder))
        pages = [f for f in files if os.path.splitext(f)[1].lower() in IMAGE_EXTS]
        pdfs = [f for f in files if f.lower().endswith('.pdf')]
        title_file = os.path.join(folder, 'title.txt')
        if os.path.isfile(title_file):
            with open(title_file, encoding='utf-8') as fh:
                title = fh.read().strip()
        else:
            try:
                parsed = datetime.strptime(name, '%Y-%m-%d')
                title = 'Shree Classified - ' + parsed.strftime('%d %B %Y')
            except ValueError:
                title = 'Shree Classified - ' + name
        if pages or pdfs:
            editions.append({
                'slug': name,
                'title': title,
                'date': name,
                'pages': pages,
                'pdf': pdfs[0] if pdfs else None,
            })
    return editions


def render_page(title, content, scripts=''):
    return LAYOUT.substitute(title=html.escape(title), content=content, scripts=scripts)


def edition_content(ed):
    """Return (content_html, scripts_html) for an edition viewer page."""
    parts = []
    parts.append(
        f'<div class="edition-header"><h1>{html.escape(ed["title"])}</h1>'
        f'<p class="edition-date">Published: {ed["date"]}</p></div>')
    if ed['pages']:
        first = f'img/{ed["slug"]}/{ed["pages"][0]}'
        thumbs = ''.join(
            f'<img class="thumb{" active" if i == 0 else ""}" data-index="{i}" '
            f'src="img/{ed["slug"]}/{p}" alt="Page {i + 1}">'
            for i, p in enumerate(ed['pages']))
        parts.append(
            '<div class="viewer">'
            '<div class="viewer-toolbar">'
            '<button id="prev-btn">&#9664; Prev</button>'
            f'<span id="page-indicator">Page 1 / {len(ed["pages"])}</span>'
            '<button id="next-btn">Next &#9654;</button>'
            '<span class="toolbar-sep"></span>'
            '<button id="zoom-out-btn">&minus;</button>'
            '<button id="zoom-in-btn">+</button>'
            f'<a id="download-link" href="{first}" download>Download page</a>'
            '</div>'
            f'<div class="viewer-stage"><img id="page-image" src="{first}" alt="Page 1"></div>'
            f'<div class="thumbnails">{thumbs}</div>'
            '</div>')
    if ed['pdf']:
        pdf_path = f'img/{ed["slug"]}/{ed["pdf"]}'
        block = '<div class="pdf-section">'
        if not ed['pages']:
            block += f'<iframe class="pdf-frame" src="{pdf_path}"></iframe>'
        block += (f'<p><a class="btn" href="{pdf_path}" target="_blank">'
                  'Open full edition PDF</a></p></div>')
        parts.append(block)
    scripts = ''
    if ed['pages']:
        page_files = json.dumps([f'img/{ed["slug"]}/{p}' for p in ed['pages']])
        scripts = VIEWER_JS.substitute(page_files=page_files)
    return '\n'.join(parts), scripts


def archive_content(editions):
    if not editions:
        return '<div class="empty-state"><p>No editions have been published yet.</p></div>'
    cards = []
    for ed in editions:
        if ed['pages']:
            cover = f'<img src="img/{ed["slug"]}/{ed["pages"][0]}" alt="">'
        else:
            cover = '<div class="cover-placeholder">PDF</div>'
        extra = ' + PDF' if ed['pdf'] else ''
        cards.append(
            f'<a class="archive-card" href="e-{ed["slug"]}.html">{cover}'
            f'<div class="archive-card-body"><h3>{html.escape(ed["title"])}</h3>'
            f'<p>{ed["date"]}</p>'
            f'<p class="muted">{len(ed["pages"])} page(s){extra}</p></div></a>')
    return '<h1>Edition Archive</h1><div class="archive-grid">' + ''.join(cards) + '</div>'


def write(path, content):
    with open(path, 'w', encoding='utf-8') as fh:
        fh.write(content)


def main():
    if os.path.isdir(OUTPUT_DIR):
        shutil.rmtree(OUTPUT_DIR)
    os.makedirs(os.path.join(OUTPUT_DIR, 'css'), exist_ok=True)
    shutil.copy(CSS_SOURCE, os.path.join(OUTPUT_DIR, 'css', 'style.css'))

    editions = load_editions()

    for ed in editions:
        dest = os.path.join(OUTPUT_DIR, 'img', ed['slug'])
        os.makedirs(dest, exist_ok=True)
        files = list(ed['pages'])
        if ed['pdf']:
            files.append(ed['pdf'])
        for fname in files:
            shutil.copy(os.path.join(EDITIONS_DIR, ed['slug'], fname),
                        os.path.join(dest, fname))
        content, scripts = edition_content(ed)
        write(os.path.join(OUTPUT_DIR, f'e-{ed["slug"]}.html'),
              render_page(ed['title'] + ' - Shree Classified', content, scripts))

    if editions:
        content, scripts = edition_content(editions[0])
        index_html = render_page(editions[0]['title'] + ' - Shree Classified', content, scripts)
    else:
        index_html = render_page(
            'Shree Classified',
            '<div class="empty-state"><h2>No editions published yet</h2>'
            '<p>The first weekly edition of <strong>Shree Classified</strong> '
            'will appear here soon.</p></div>')
    write(os.path.join(OUTPUT_DIR, 'index.html'), index_html)
    write(os.path.join(OUTPUT_DIR, 'archive.html'),
          render_page('Archive - Shree Classified', archive_content(editions)))

    print(f'Built {len(editions)} edition(s) into public/')


if __name__ == '__main__':
    main()
