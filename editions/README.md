# How to publish a weekly edition (admin guide)

Publishing is done right here in GitLab - no separate admin site needed.
Only project members can do this, so it is automatically login-protected.

## Upload a new edition

1. Open the repository in GitLab: **Code > Repository**, go into the `editions` folder
2. Click **+ > New directory** and name it with the publish date: `YYYY-MM-DD` (e.g. `2026-06-14`)
3. Open the new folder, click **+ > Upload file** and upload the page images
   - Name them in page order: `01.jpg`, `02.jpg`, `03.jpg`, ...
   - Supported formats: JPG, PNG, GIF, WEBP
   - Optionally also upload a full `edition.pdf`
4. Commit directly to `main`

The website rebuilds automatically (takes 1-2 minutes) and the new edition
appears as the latest edition on the homepage, with older ones in the Archive.

## Optional: custom title

By default the title is "Shree Classified - 14 June 2026" (from the folder name).
To override it, add a `title.txt` file in the edition folder containing the title.

## Edit an edition

- **Replace a page**: upload a file with the same name (it overwrites the old one)
- **Delete a page**: open the file in GitLab and choose **Delete**
- **Delete an edition**: delete all files in its folder

Every change to `main` republishes the site automatically.
