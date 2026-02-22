# Immich Faceless Album Sync

A small Python utility to keep an Immich album in sync with assets that contain no detected people ("faceless" assets). The script queries the Immich API for assets, finds those without people metadata, and ensures a configured album contains exactly those assets (adds missing ones and removes assets that now contain people).

I find this useful because I take a lot of techinical photos of projects for work/hobbies and WAY MORE pictures of my kids.  When I need to find a technical picture the search tool isn't always useful. Having a quick way seeing only assets that are not my kids (or other people) is very helpful.

A second use is to have an easy way to see whcih photos the machine learning missed when tagging people.

This repository contains:
- `faceless_album_sync.py` — the sync script you run on a schedule (cron / Task Scheduler).
- `.env` (example provided) — runtime configuration (API key, URL, logging, email).
- Optional email notifications for unhandled exceptions.

Key behaviors implemented by the script:
- Pages through Immich search results to collect assets with no people.
- Creates the target album if it does not exist.
- Adds new faceless assets and removes assets that are no longer faceless.
- Rotating file logging and optional email alerts on exception.

Requirements
- Python 3.8+
- Packages: `requests`, `python-dotenv`

Install dependencies
```immich_faceless_album/README.md#L1-4
pip install requests python-dotenv
```

Quick start
1. Copy or create a `.env` file in the project root with the values described below.
2. Run the script:
```immich_faceless_album/README.md#L5-7
python faceless_album_sync.py
```

Configuration (environment variables)
Set these environment variables in a `.env` file or in your environment. Example:
```immich_faceless_album/.env.example#L1-20
# Immich API and behavior
IMMICH_URL=https://your-immich-server.example
API_KEY=your_immich_api_key_here

# Album name to keep in sync (created if missing)
ALBUM_NAME=Faceless

# Logging
LOG_FILE_PATH=./faceless_sync.log

# Email notifications (optional)
ENABLE_EMAIL_ON_ERROR=false
EMAIL_SMTP_SERVER=smtp.example.com
EMAIL_SMTP_PORT=465
EMAIL_USERNAME=your-smtp-user
EMAIL_PASSWORD=your-smtp-password
EMAIL_FROM=from@example.com
EMAIL_TO=you@example.com
```

Notes about config:
- `IMMICH_URL` should be the base URL of your Immich instance (no trailing slash required; script appends endpoints).
- `API_KEY` is required and is sent with `x-api-key` header for API calls.
- `ALBUM_NAME` is the album that will be kept in sync.
- `ENABLE_EMAIL_ON_ERROR` toggles sending an error email on unhandled exceptions.
- `LOG_FILE_PATH` is used by a rotating file handler; ensure the directory is writable.

Security and TLS
- The script currently disables TLS verification for the search request (`verify=False`) when posting to `/api/search/metadata`. This was present in the original script; for production you should enable proper certificate verification. If you must use a self-signed certificate, prefer configuring your environment to trust it rather than disabling verification.
- Keep your `API_KEY` and SMTP credentials out of version control (use `.env` and add it to `.gitignore`).

Running on a schedule
- Unix / Linux (cron):
```immich_faceless_album/README.md#L30-33
# Run every hour
0 * * * * cd /path/to/immich_faceless_album && /usr/bin/python3 faceless_album_sync.py >> /var/log/faceless_sync_cron.log 2>&1
```
- Windows Task Scheduler:
  - Create a task that runs `python C:\path\to\immich_faceless_album\faceless_album_sync.py`.
  - Configure triggers (e.g., hourly) and ensure the account has file/network permissions.

Logging and rotation
- The script writes logs to the file pointed by `LOG_FILE_PATH` and also streams logs to stdout.
- Log rotation is configured with a 5 MB max file size and 3 backups. Adjust as needed by modifying the script.

Email notifications
- If `ENABLE_EMAIL_ON_ERROR` is `true`, the script attempts to email a traceback when it encounters an unhandled exception.
- It uses SMTP over SSL (`smtplib.SMTP_SSL`) with `EMAIL_SMTP_SERVER` and `EMAIL_SMTP_PORT` and logs failures to send emails.
- Ensure SMTP credentials are correct and allowed to send from the configured `EMAIL_FROM`.

Troubleshooting
- Authentication errors: double-check `API_KEY` and that the Immich instance allows API access.
- Network / connectivity: make sure the server running the script can reach `IMMICH_URL`.
- Permission errors writing logs: verify `LOG_FILE_PATH` directory exists and is writable.
- Unexpected results from API: enable debug/INFO logging and inspect the HTTP responses. The script uses `response.raise_for_status()` to surface non-2xx responses as exceptions.

Extending or customizing
- You can alter the search request (currently requests `/api/search/metadata` with `withPeople: True`) to change what counts as "faceless".
- If you prefer to only add assets (no removals) or vice versa, modify the `main()` logic around `ids_to_add` / `ids_to_remove`.

Implementation notes (for maintainers)
- Main entrypoint: `main()` in `faceless_album_sync.py`.
- HTTP headers use `x-api-key` and `Accept: application/json`.
- The script pages through results using `page` and `size` until fewer results than page size are returned.
- Assets are compared by their `id` to determine set differences.

Contributing
- Contributions are welcome. Open an issue or PR with clear explanations of changes and any test steps.

License
- See the `LICENSE` file in this repository for licensing details.
