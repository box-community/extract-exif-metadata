# Extract EXIF metadata with Box representations

A minimal, runnable reference script that fetches the on-demand
`[embedded_metadata]` representation for previewable images in a Box folder,
maps selected EXIF / XMP / ICC fields, and writes them onto a Box metadata
template so you can filter those images in a Box Apps dashboard.

This is the companion repository to the tutorial
**[Extract EXIF metadata with Box representations](https://developer.box.com/tutorials/extract-exif-metadata)**.
Clone it, add Client Credentials Grant (CCG) credentials, upload sample
photos, and run the folder processor.

## What it does

| Capability | How |
| --- | --- |
| List representations for a file | `GET /2.0/files/:id?fields=representations` |
| Request embedded technical metadata | Same endpoint with `x-rep-hints: [embedded_metadata]` |
| Generate an on-demand representation | Hit the representation info URL when state is `none`, then poll until `success` / `viewable` |
| Map EXIF, XMP, and ICC fields | `EMBEDDED_METADATA_FIELD_MAP` in `metadata.py` |
| Write values back to the file | `POST /2.0/files/:id/metadata/enterprise/:template` (create, or JSON-Patch `add` on 409) |

## Project layout

```
extract-exif-metadata/
├── box_client.py          # CCG Service Account auth
├── representations.py     # List and fetch representations (with polling)
├── metadata.py            # Field map + write metadata (409 upsert)
├── process.py             # Folder processor entrypoint
├── make_sample_photo.py   # Generates sample-photo.jpg for testing
├── sample-photo.jpg
├── requirements.txt
├── .env.example
├── .gitignore
└── LICENSE
```

## Prerequisites

- **Python 3.11 or higher**
- A free [Box developer account](https://account.box.com/signup/developer)
  (or an enterprise account with Developer Console access)
- A [Platform App](https://cloud.app.box.com/developers/console) using
  **Client Credentials Grant**, **authorized** in the Admin Console, with
  this scope:
  - **Read and write all files and folders stored in Box**
- An **Image Metadata** template in the Admin Console (see Setup below)
- A **Photos** folder in Box, with the app's **Service Account** invited as
  an **Editor** collaborator

## Setup

1. **Clone and enter the project**

   ```bash
   git clone https://github.com/box-community/extract-exif-metadata.git
   cd extract-exif-metadata
   ```

2. **Create a virtual environment and install dependencies**

   macOS / Linux:

   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

   Windows (Command Prompt):

   ```bat
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Create the Image Metadata template** (Admin Console → **Metadata** →
   **New**). Name it `Image Metadata` and add these fields:

   | Field name | Type | Template key |
   | --- | --- | --- |
   | Date/Time | Date | `datetime` |
   | Camera Make | Text | `cameraMake` |
   | Image Width | Number | `imageWidth` |
   | Image Height | Number | `imageHeight` |
   | ISO | Number | `iso` |
   | Color Profile | Text | `colorProfile` |
   | Rights | Text | `rights` |
   | Creator | Text | `creator` |

   Copy the **template key** shown under Template Name — you need it for `.env`.
   Box also generates a **field key** from each field name (for example,
   Camera Make becomes `cameraMake`). Those keys must match
   `EMBEDDED_METADATA_FIELD_MAP`.

4. **Create the Photos folder** in Box and note its folder ID from the URL
   (`https://app.box.com/folder/123456789` → `123456789`).

   **Critical:** invite the app's Service Account as an **Editor** on that
   folder. Find the Service Account email in Developer Console → your app →
   **General Settings** → **Service Account ID** (looks like
   `AutomationUser_xxxxx_xxxxxx@boxdevedition.com`). Without this
   collaboration, API calls return `404 Not Found`.

5. **Configure credentials**

   ```bash
   cp .env.example .env
   ```

   Edit `.env` and fill in:

   - `BOX_CLIENT_ID`, `BOX_CLIENT_SECRET`, `BOX_ENTERPRISE_ID` from the Developer Console
   - `BOX_METADATA_TEMPLATE_KEY` from step 3
   - `BOX_FOLDER_ID` from step 4

   Never commit `.env`. It is listed in `.gitignore`.

## Run

Upload one or more previewable images to the Photos folder. You can use
`sample-photo.jpg` from this repo (regenerate any time with
`python make_sample_photo.py`). Then:

```bash
python process.py
```

A successful run looks like:

```text
Processing [1]: sample-photo.jpg (id: 123456789)
state: success  |  url_template: https://dl.boxcloud.com/api/2.0/internal_files/...
Extracted 7 of 8 fields:
  datetime: '2024-06-15T14:30:00Z' (str)
  cameraMake: 'Apple' (str)
  imageWidth: 8 (int)
  imageHeight: 8 (int)
  iso: 200 (int)
  rights: 'Copyright 2026 Sample' (str)
  creator: 'Jane Photographer' (str)
Metadata created: imageMetadata on file 123456789
```

Open a file in Box → **Metadata** tab to verify the values. Not every file
includes every EXIF, XMP, or ICC field — missing fields are skipped.

## How it works

1. `process.py` lists image files in `BOX_FOLDER_ID` (`.jpg`, `.jpeg`,
   `.png`, `.tiff`, `.tif`, `.heic`, `.gif`, `.webp`).
2. `representations.py` requests `[embedded_metadata]`. If the state is
   `none`, it triggers generation through the representation info URL, then
   polls until `success` or `viewable`.
3. `metadata.py` maps template keys to JSON paths, coerces types (EXIF dates
   become RFC 3339), and writes an enterprise metadata instance. On `409
   Conflict` it JSON-Patch updates with op `add`.
4. Add a Box Apps dashboard on that template to filter by camera make, ISO,
   or capture date. See the [tutorial](https://developer.box.com/tutorials/extract-exif-metadata)
   for dashboard screenshots.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `ModuleNotFoundError` | Activate the venv: `source .venv/bin/activate`. Install with `pip install -r requirements.txt` (uses `boxsdk~=10` only — do not also install `box-sdk-gen`). |
| `invalid_client` | Check `BOX_CLIENT_ID` / `BOX_CLIENT_SECRET` / `BOX_ENTERPRISE_ID` in `.env`. Confirm the app type is Client Credentials Grant. |
| `unauthorized_client` | Authorize the app in the Admin Console (Developer Console → Authorization → Review and Submit). Re-authorize after changing scopes. |
| `404 Not Found` | Invite the Service Account as **Editor** on the Photos folder. |
| Timed out after 30s waiting for representation | `embedded_metadata` is generated on demand. Wait a few seconds and re-run. Confirm the file type is one Box can [preview](https://developer.box.com/guides/representations/supported-file-types). |
| Extracted 0 of 8 fields | Not every file includes every EXIF, XMP, or ICC field. Check the downloaded JSON, then adjust `EMBEDDED_METADATA_FIELD_MAP` if you need different paths. |
| `409 Conflict on Metadata Instance` | The file already has the template. Current `metadata.py` upserts on 409. To retest from a clean slate, delete the instance from the file's **Metadata** tab. |

## Related

- Tutorial: [Extract EXIF metadata with Box representations](https://developer.box.com/tutorials/extract-exif-metadata)
- [Representations](https://developer.box.com/guides/representations)
- [Request a representation](https://developer.box.com/guides/representations/request-a-representation)
- [Client Credentials Grant](https://developer.box.com/guides/authentication/client-credentials/)
- [Customizing metadata templates](https://support.box.com/hc/en-us/articles/360044194033-Customizing-Metadata-Templates)

## License

[MIT](./LICENSE)
