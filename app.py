import os
import uuid
from functools import wraps

import psycopg2
import psycopg2.extras
from flask import (Flask, abort, flash, g, make_response, redirect,
                   render_template, request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

# PostgreSQL connection string from Neon
DATABASE_URL = os.environ.get(
    'DATABASE_URL',
    'postgresql://neondb_owner:npg_TadgY6mjw3cG@ep-damp-brook-adaj2kn8-pooler.c-2.us-east-1.aws.neon.tech/neondb?sslmode=require'
)

IMAGE_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp'}
PDF_EXTENSIONS = {'pdf'}

CONTENT_TYPES = {
    'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
    'png': 'image/png', 'gif': 'image/gif',
    'webp': 'image/webp', 'pdf': 'application/pdf',
}

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'change-this-secret-key-in-production')
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50 MB

ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME', 'admin')
ADMIN_PASSWORD_HASH = generate_password_hash(os.environ.get('ADMIN_PASSWORD', 'admin123'))


# ---------------------------------------------------------------- database

def get_db():
    """Get a PostgreSQL connection for the current request."""
    if 'db' not in g:
        g.db = psycopg2.connect(DATABASE_URL)
    return g.db


def get_cursor():
    """Return a dict-like cursor from the current connection."""
    db = get_db()
    return db.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


@app.teardown_appcontext
def close_db(exc):
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    """Create tables if they don't exist."""
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS editions (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            publish_date TEXT NOT NULL,
            pdf_file TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS pages (
            id SERIAL PRIMARY KEY,
            edition_id INTEGER NOT NULL REFERENCES editions (id) ON DELETE CASCADE,
            page_number INTEGER NOT NULL,
            filename TEXT NOT NULL
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS files (
            id SERIAL PRIMARY KEY,
            filename TEXT NOT NULL UNIQUE,
            content_type TEXT NOT NULL,
            data BYTEA NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    cur.close()
    conn.close()


def get_edition_with_pages(edition_id):
    cur = get_cursor()
    cur.execute('SELECT * FROM editions WHERE id = %s', (edition_id,))
    edition = cur.fetchone()
    if edition is None:
        cur.close()
        return None, []
    cur.execute(
        'SELECT * FROM pages WHERE edition_id = %s ORDER BY page_number',
        (edition_id,))
    pages = cur.fetchall()
    cur.close()
    return edition, pages


# ---------------------------------------------------------------- helpers

def allowed_file(filename, extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in extensions


def save_upload(file_storage):
    """Save an uploaded file into PostgreSQL and return the stored filename."""
    original = secure_filename(file_storage.filename)
    ext = original.rsplit('.', 1)[1].lower()
    stored_name = f"{uuid.uuid4().hex}.{ext}"
    content_type = CONTENT_TYPES.get(ext, 'application/octet-stream')
    data = file_storage.read()

    db = get_db()
    cur = get_cursor()
    cur.execute(
        'INSERT INTO files (filename, content_type, data) VALUES (%s, %s, %s)',
        (stored_name, content_type, psycopg2.Binary(data)))
    db.commit()
    cur.close()
    return stored_name


def delete_stored_file(filename):
    """Delete a file from PostgreSQL storage."""
    if not filename:
        return
    db = get_db()
    cur = get_cursor()
    cur.execute('DELETE FROM files WHERE filename = %s', (filename,))
    db.commit()
    cur.close()


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get('admin_logged_in'):
            return redirect(url_for('admin_login', next=request.path))
        return view(*args, **kwargs)
    return wrapped


# ---------------------------------------------------------------- public site

@app.route('/')
def index():
    cur = get_cursor()
    cur.execute('SELECT * FROM editions ORDER BY publish_date DESC, id DESC LIMIT 1')
    latest = cur.fetchone()
    cur.close()
    if latest is None:
        return render_template('index.html', edition=None, pages=[])
    return redirect(url_for('view_edition', edition_id=latest['id']))


@app.route('/edition/<int:edition_id>')
def view_edition(edition_id):
    edition, pages = get_edition_with_pages(edition_id)
    if edition is None:
        abort(404)
    return render_template('index.html', edition=edition, pages=pages)


@app.route('/archive')
def archive():
    cur = get_cursor()
    cur.execute(
        '''SELECT e.*, COUNT(p.id) AS page_count,
                  (SELECT filename FROM pages WHERE edition_id = e.id
                   ORDER BY page_number LIMIT 1) AS cover
           FROM editions e LEFT JOIN pages p ON p.edition_id = e.id
           GROUP BY e.id
           ORDER BY e.publish_date DESC, e.id DESC''')
    editions = cur.fetchall()
    cur.close()
    return render_template('archive.html', editions=editions)


@app.route('/uploads/<path:filename>')
def uploaded_file(filename):
    """Serve uploaded files from PostgreSQL storage."""
    cur = get_cursor()
    cur.execute('SELECT content_type, data FROM files WHERE filename = %s', (filename,))
    row = cur.fetchone()
    cur.close()
    if row is None:
        abort(404)
    response = make_response(bytes(row['data']))
    response.headers['Content-Type'] = row['content_type']
    response.headers['Cache-Control'] = 'public, max-age=31536000, immutable'
    return response


# ---------------------------------------------------------------- admin auth

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username', '')
        password = request.form.get('password', '')
        if username == ADMIN_USERNAME and check_password_hash(ADMIN_PASSWORD_HASH, password):
            session['admin_logged_in'] = True
            flash('Welcome back!', 'success')
            return redirect(request.args.get('next') or url_for('admin_dashboard'))
        flash('Invalid username or password.', 'error')
    return render_template('admin/login.html')


@app.route('/admin/logout')
def admin_logout():
    session.pop('admin_logged_in', None)
    flash('Logged out.', 'success')
    return redirect(url_for('admin_login'))


# ---------------------------------------------------------------- admin portal

@app.route('/admin')
@login_required
def admin_dashboard():
    cur = get_cursor()
    cur.execute(
        '''SELECT e.*, COUNT(p.id) AS page_count
           FROM editions e LEFT JOIN pages p ON p.edition_id = e.id
           GROUP BY e.id
           ORDER BY e.publish_date DESC, e.id DESC''')
    editions = cur.fetchall()
    cur.close()
    return render_template('admin/dashboard.html', editions=editions)


@app.route('/admin/upload', methods=['GET', 'POST'])
@login_required
def admin_upload():
    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        publish_date = request.form.get('publish_date', '').strip()
        page_files = [f for f in request.files.getlist('pages') if f and f.filename]
        pdf_file = request.files.get('pdf')

        if not title or not publish_date:
            flash('Title and publish date are required.', 'error')
            return render_template('admin/upload.html')
        if not page_files and not (pdf_file and pdf_file.filename):
            flash('Upload at least one page image or a PDF.', 'error')
            return render_template('admin/upload.html')

        for f in page_files:
            if not allowed_file(f.filename, IMAGE_EXTENSIONS):
                flash(f'"{f.filename}" is not a supported image (jpg, png, gif, webp).', 'error')
                return render_template('admin/upload.html')
        if pdf_file and pdf_file.filename and not allowed_file(pdf_file.filename, PDF_EXTENSIONS):
            flash('The PDF upload must be a .pdf file.', 'error')
            return render_template('admin/upload.html')

        pdf_name = save_upload(pdf_file) if pdf_file and pdf_file.filename else None

        db = get_db()
        cur = get_cursor()
        cur.execute(
            'INSERT INTO editions (title, publish_date, pdf_file) VALUES (%s, %s, %s) RETURNING id',
            (title, publish_date, pdf_name))
        edition_id = cur.fetchone()['id']
        for number, f in enumerate(page_files, start=1):
            cur.execute(
                'INSERT INTO pages (edition_id, page_number, filename) VALUES (%s, %s, %s)',
                (edition_id, number, save_upload(f)))
        db.commit()
        cur.close()
        flash('Edition uploaded successfully.', 'success')
        return redirect(url_for('admin_dashboard'))

    return render_template('admin/upload.html')


@app.route('/admin/edition/<int:edition_id>/edit', methods=['GET', 'POST'])
@login_required
def admin_edit(edition_id):
    edition, pages = get_edition_with_pages(edition_id)
    if edition is None:
        abort(404)
    db = get_db()

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        publish_date = request.form.get('publish_date', '').strip()
        if not title or not publish_date:
            flash('Title and publish date are required.', 'error')
            return redirect(url_for('admin_edit', edition_id=edition_id))

        cur = get_cursor()
        cur.execute('UPDATE editions SET title = %s, publish_date = %s WHERE id = %s',
                    (title, publish_date, edition_id))

        # Optional PDF replacement
        pdf_file = request.files.get('pdf')
        if pdf_file and pdf_file.filename:
            if not allowed_file(pdf_file.filename, PDF_EXTENSIONS):
                flash('The PDF upload must be a .pdf file.', 'error')
                cur.close()
                return redirect(url_for('admin_edit', edition_id=edition_id))
            delete_stored_file(edition['pdf_file'])
            cur.execute('UPDATE editions SET pdf_file = %s WHERE id = %s',
                        (save_upload(pdf_file), edition_id))

        # Optional extra pages appended at the end
        new_pages = [f for f in request.files.getlist('pages') if f and f.filename]
        if new_pages:
            cur.execute(
                'SELECT COALESCE(MAX(page_number), 0) AS n FROM pages WHERE edition_id = %s',
                (edition_id,))
            last = cur.fetchone()['n']
            for offset, f in enumerate(new_pages, start=1):
                if not allowed_file(f.filename, IMAGE_EXTENSIONS):
                    flash(f'"{f.filename}" is not a supported image.', 'error')
                    cur.close()
                    return redirect(url_for('admin_edit', edition_id=edition_id))
                cur.execute(
                    'INSERT INTO pages (edition_id, page_number, filename) VALUES (%s, %s, %s)',
                    (edition_id, last + offset, save_upload(f)))

        db.commit()
        cur.close()
        flash('Edition updated.', 'success')
        return redirect(url_for('admin_edit', edition_id=edition_id))

    return render_template('admin/edit.html', edition=edition, pages=pages)


@app.route('/admin/page/<int:page_id>/delete', methods=['POST'])
@login_required
def admin_delete_page(page_id):
    db = get_db()
    cur = get_cursor()
    cur.execute('SELECT * FROM pages WHERE id = %s', (page_id,))
    page = cur.fetchone()
    if page is None:
        cur.close()
        abort(404)
    delete_stored_file(page['filename'])
    cur.execute('DELETE FROM pages WHERE id = %s', (page_id,))
    # Re-number remaining pages
    cur.execute(
        'SELECT id FROM pages WHERE edition_id = %s ORDER BY page_number',
        (page['edition_id'],))
    remaining = cur.fetchall()
    for number, row in enumerate(remaining, start=1):
        cur.execute('UPDATE pages SET page_number = %s WHERE id = %s', (number, row['id']))
    db.commit()
    cur.close()
    flash('Page deleted.', 'success')
    return redirect(url_for('admin_edit', edition_id=page['edition_id']))


@app.route('/admin/edition/<int:edition_id>/delete', methods=['POST'])
@login_required
def admin_delete_edition(edition_id):
    db = get_db()
    edition, pages = get_edition_with_pages(edition_id)
    if edition is None:
        abort(404)
    for page in pages:
        delete_stored_file(page['filename'])
    delete_stored_file(edition['pdf_file'])
    cur = get_cursor()
    cur.execute('DELETE FROM editions WHERE id = %s', (edition_id,))
    db.commit()
    cur.close()
    flash('Edition deleted.', 'success')
    return redirect(url_for('admin_dashboard'))


# ---------------------------------------------------------------- entry point

init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)
