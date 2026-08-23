# Osdag Secure Auth Task

This workspace contains two backend implementations for the same authentication and file access flow:

- `custom-backend/`: FastAPI + SQLite + JWT-based auth
- `appwrite-backend/`: Appwrite Web SDK client setup and configuration notes

The browser UI stays in the provided `index.html` and is intentionally not redesigned.

## Quick start

### 1) Custom backend

```bash
cd custom-backend
python -m venv .venv
. .venv\Scripts\activate
pip install -r requirements.txt
python -m app.main
```

Then open the browser at `http://localhost:8000` for the API, or use the included `index.html` and select the custom backend mode.

### 2) Appwrite backend

Follow the instructions in `appwrite-backend/README.md`.

---

## Security choices

- Passwords are hashed with `bcrypt` before storage.
- JWT tokens are signed using a server-side secret and checked on every protected route.
- Logout invalidates the token server-side by storing it in a revoked token set.
- User isolation is enforced by querying the authenticated user id on every file or profile route.
- Failed logins return a generic message and are rate-limited.

## Notes

The mock files in this task are for UI simulation only. The real backend logic is implemented in the folders above.
