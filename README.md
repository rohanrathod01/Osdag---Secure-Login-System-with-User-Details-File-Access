# Osdag Secure Login System with User Details & File Access

This project implements the same secure login and file-access workflow with two separated backends:

- `custom-backend/`: FastAPI, SQLite, bcrypt, and JWT bearer authentication.
- `appwrite-backend/`: Appwrite Web SDK integration for Auth, Database, and Storage.

The provided `index.html` is the browser test client required for this task. No npm build step or framework is required.

## Features

- User registration, login, and logout.
- Protected current-user profile endpoint.
- User-specific file listing, metadata lookup, and download.
- Three seeded accounts with separate files.
- Password hashing and generic failed-login responses.
- Basic lockout after repeated failed login attempts.
- Ownership checks that prevent cross-user file access.

## Project Layout

```text
index.html                         Browser test client
mock-api.js                        Optional in-browser mock only
seed-data.json                     Mock data only
custom-backend/                    FastAPI implementation
	app/main.py                      API routes and JWT authentication
	app/database.py                  SQLite schema, hashing, and seed data
	seed_demo.py                     Idempotent seed command
	verify_app.py                    Automated API verification
	.env.example                     Custom backend configuration template
appwrite-backend/                  Appwrite implementation
	appwrite-client.js               Appwrite browser adapter
	README.md                        Appwrite Console setup details
```

## Setup and Execution

### Option A: Custom FastAPI backend

Open PowerShell in the cloned repository root, then run:

```powershell
cd .\custom-backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Open `.env` and replace `SECRET_KEY` with a long random value. For example, generate one with:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Then start the API:

```powershell
python -m app.main
```

The API runs at `http://localhost:8000`. The database is created at `custom-backend/data/app.db` and local files are stored below `custom-backend/storage/`.

### Start the browser client

Keep the API terminal running and open a second PowerShell terminal:

```powershell
# Run this command from the cloned repository root.
python -m http.server 5500
```

Open [http://localhost:5500](http://localhost:5500). Select **Custom REST backend** and keep the Base URL set to `http://localhost:8000`.

Do not open `index.html` directly with `file://`; serving it over HTTP is required for the browser scripts and Appwrite requests.

### Verify the custom backend

Run this from `custom-backend`, with the virtual environment active:

```powershell
cd .\custom-backend
python verify_app.py
```

The check covers registration conflict handling, login, profile access, file listing, download, cross-user `403` protection, and invalid-login handling.

## Seeded Test Users and Files

The custom backend creates these users automatically on startup when the SQLite database is empty:

| User | Email | Password |
| --- | --- | --- |
| Alice Nakamura | `alice@example.com` | `Password123!` |
| Bob Alvarez | `bob@example.com` | `Password123!` |
| Carol Whitfield | `carol@example.com` | `Password123!` |

Each account has its own seeded files. The additional notes are:

- Alice: `alice_notes.txt`
- Bob: `bob_notes.txt`
- Carol: `carol_notes.txt`

The seed operation is idempotent: it does not duplicate users or files that already exist. It can also be run explicitly:

```powershell
cd .\custom-backend
python seed_demo.py
```

To test isolation, log in as one user, click **GET /files**, and use one of the returned custom IDs such as `file_e634add29fe5`. A different user must receive `403 Forbidden` when requesting that file.

The Appwrite implementation uses the same three email/password test accounts only after they have been created in the Appwrite Console. Its file records must reference the corresponding Appwrite Storage file IDs. See [appwrite-backend/README.md](appwrite-backend/README.md).

## API Endpoints: Custom Backend

All protected endpoints require:

```http
Authorization: Bearer <jwt>
```

| Method | Endpoint | Purpose |
| --- | --- | --- |
| `GET` | `/health` | Health check |
| `POST` | `/api/register` | Create an account |
| `POST` | `/api/login` | Return a JWT |
| `POST` | `/api/logout` | Revoke the current JWT |
| `GET` | `/api/user` | Return the authenticated user |
| `GET` | `/api/files` | List only that user’s files |
| `GET` | `/api/files/{file_id}` | Read owned file metadata |
| `GET` | `/api/files/{file_id}/download` | Download an owned file |

The browser client automatically prefixes custom routes with `/api`.

## Authentication Decision: JWT vs. Sessions

The custom implementation uses signed JWT bearer tokens because the API is a small REST service and the browser test client can send the same `Authorization` header to every protected route. The token contains the user ID in `sub` and an expiration timestamp. The server validates the signature, algorithm, expiration, and user existence on every request.

This avoids requiring a server-side session database for the basic request flow and makes the API easy to test independently. The trade-off is that JWTs are difficult to revoke by themselves, so this project maintains an in-memory revoked-token set for logout. A production deployment would use a persistent revocation/session store or short-lived access tokens with refresh-token rotation.

Appwrite uses its own managed session system instead. The browser creates and deletes the current Appwrite session through the SDK.

## Logout Implementation

For the custom backend, logout requires the current valid bearer token and adds that token to `REVOKED_TOKENS`. Every protected request checks this set before decoding and accepting the token. Clearing the token in the browser alone is therefore not the security mechanism.

For Appwrite, `account.deleteSession('current')` destroys the current Appwrite session. Subsequent `account.get()` and database/storage operations fail until the user logs in again.

## User Data Isolation

The custom backend derives the user ID from the validated JWT, never from a user ID supplied by the browser. File listing queries SQLite with that authenticated user ID. Single-file metadata and download routes compare the record owner against the authenticated user and return `403` for another user’s existing file and `404` for a missing file.

The Appwrite adapter first calls `account.get()` and filters profile/file database queries by `userId == currentUser.$id`. File downloads are allowed only after an owned metadata record is found, and then use that record’s Storage `fileId`. Appwrite collection and bucket permissions must also be configured in the Console; client-side filtering is not a replacement for server-side permissions.

## Appwrite: Managed vs. Manual Configuration

### Appwrite handles automatically

- Password hashing and credential validation.
- Account creation and email/password authentication.
- Session creation, persistence, expiration, and deletion.
- Database and Storage API primitives.
- Storage file delivery after a valid authenticated request.

### Project configuration required manually

- Add the web platform/origin used to run the client, such as `http://localhost:5500`.
- Enable Email/Password authentication.
- Create database `6a89dc580022c8de2e51`.
- Create the `profiles` and `files` collections with the attributes, indexes, and permissions in [appwrite-backend/README.md](appwrite-backend/README.md).
- Use Storage bucket `6a8a8af20011e4c3163d` and configure its size/type limits.
- Apply authenticated-user and ownership-aware collection/bucket permissions.
- Create the three test accounts, profile documents, Storage files, and corresponding file metadata documents.

The browser adapter is configured for endpoint `https://sgp.cloud.appwrite.io/v1` and project `6a89db4c00229eba40ca`.

## Security Notes

- Custom passwords are hashed with bcrypt; plaintext passwords are not stored in SQLite.
- The custom JWT secret must be supplied through `.env` and must not be committed.
- Failed custom logins use the same generic error for unknown users and wrong passwords.
- Five failed attempts trigger a 60-second in-memory lockout for that email.
- `.gitignore` excludes virtual environments, local databases, and environment files.
- The mock API and `seed-data.json` are demonstrations only and are not production authentication.

## Future Improvements

Given more time, I would:

- Replace SQLite and in-memory revocation/lockout state with PostgreSQL and a shared Redis-backed session/security store.
- Use short-lived access tokens with refresh-token rotation, or secure HttpOnly cookies with CSRF protection.
- Restrict CORS to known frontend origins instead of `*`.
- Add upload, delete, profile-update, and password-reset workflows.
- Add automated tests for token expiry, logout reuse, rate limiting, malformed input, and path traversal.
- Add structured logging, production deployment configuration, migrations, and monitoring.
- Provide a server-side Appwrite provisioning script for repeatable users, metadata, files, and permissions.

## License

This project was created as an Osdag technical task demonstration.
