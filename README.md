# Shree Classified

A weekly classified e-paper website (similar to epaper.dehradunclassified.com) with a built-in admin portal to upload, edit and manage weekly editions.

## Features

### Public website
- Latest weekly edition shown on the homepage as a page-by-page e-paper viewer
- Page navigation (previous / next / thumbnails), zoom in / out, keyboard arrow support
- PDF editions open in an embedded viewer
- Archive page to browse all past weekly editions by date
- Mobile-responsive layout

### Admin portal (`/admin`)
- Login protected
- Upload a new weekly edition as **page images** (JPG/PNG/WEBP) and/or a **PDF**
- Edit edition title and publish date, add more pages, delete pages
- Delete whole editions
- Dashboard listing all editions

## Quick start

```bash
# 1. Create a virtual environment
python3 -m venv venv
source venv/bin/activate        # Windows: venv\\Scripts\\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
python app.py
```

Open http://localhost:5000 for the website and http://localhost:5000/admin for the admin portal.

## Default admin credentials

| Username | Password |
|----------|----------|
| `admin`  | `admin123` |

**Change these in production** by setting environment variables:

```bash
export ADMIN_USERNAME=youradmin
export ADMIN_PASSWORD=a-strong-password
export SECRET_KEY=a-long-random-string
```

## Free hosting on GitLab Pages (recommended)

This repo also contains a **static site generator** (`build.py`) that publishes the
e-paper to GitLab Pages for free, forever, with no server needed.

- **How it works**: weekly editions live in the `editions/` folder of this repo.
  On every push to `main`, CI runs `build.py` and publishes the site to GitLab Pages.
- **Admin portal**: managing editions is done through the GitLab web interface
  (upload/replace/delete files in `editions/`). It is protected by your GitLab login.
  See [`editions/README.md`](editions/README.md) for the step-by-step admin guide.
- **Your site URL**: find it under **Deploy > Pages** in the project sidebar
  (typically `https://om-group4133924.gitlab.io/om-project`).
- **Make it public**: since this project is private, go to
  **Settings > General > Visibility, project features, permissions > Pages**
  and set it to **Everyone**, so readers can view the e-paper without logging in.

The Flask app below remains available if you later move to a server with its own
upload-based admin portal.

## Storage

- Edition metadata is stored in an SQLite database (`shree_classified.db`, created automatically)
- Uploaded page images and PDFs are stored in the `uploads/` directory

## Project structure

```
app.py              # Flask application (public site + admin portal)
requirements.txt    # Python dependencies
templates/          # HTML templates
static/css/         # Stylesheet
uploads/            # Uploaded editions (created automatically)
```
