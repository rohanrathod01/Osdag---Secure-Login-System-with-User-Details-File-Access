# Appwrite setup guide

## 1) Create the Appwrite project

1. Open the Appwrite Console.
2. Create a new project called `osdag-auth-demo`.
3. Under `Auth`, enable Email/Password login.
4. Note the Project ID and API Endpoint.

## 2) Create the database and collections

Create a database named `osdag`.

### Collection: `profiles`

Attributes:

- `userId` (string, required)
- `name` (string, required)
- `email` (string, required)
- `createdAt` (string, required)

Indexes:

- `userId` unique index
- `email` unique index

Permissions:

- Create: `users` (authenticated users)
- Read: `users` (authenticated users)
- Update: `users` (authenticated users)
- Delete: `users` (authenticated users)

### Collection: `files`

Attributes:

- `userId` (string, required)
- `fileId` (string, required)   // Appwrite Storage file ID
- `fileName` (string, required)
- `mimeType` (string, required)
- `sizeBytes` (integer, required)
- `uploadedAt` (string, required)

Indexes:

- `userId` index
- `fileId` unique index

Permissions:

- Create: `users` (authenticated users)
- Read: `users` (authenticated users)
- Update: `users` (authenticated users)
- Delete: `users` (authenticated users)

## 3) Create the storage bucket

Create a bucket called `user-files`.

Recommended settings:

- File size limit: 10 MB
- Allowed extensions: `jpg`, `png`, `pdf`, `txt`, `docx`
- Compression: optional
- Encryption: enabled

Bucket permissions:

- `role:users` -> `read`, `create`, `update`, `delete`

> This is bucket-level access. Ownership is still enforced in the client code and database queries by checking `userId == currentUser.$id` before allowing file reads/downloads.

## 4) Create seeded users

Use the Appwrite Auth API to create three seeded users:

- `alice@example.com` / `Password123!`
- `bob@example.com` / `Password123!`
- `carol@example.com` / `Password123!`

For each account, create a matching `profiles` document and a few files in the `user-files` bucket, with the corresponding `files` metadata records referencing the storage file IDs.

## 5) Client-side usage

Inject the client script from `appwrite-backend/appwrite-client.js` in place of the mock fetch layer. Set your Appwrite endpoint and project ID in the browser UI or in the script constants.

## What Appwrite handles automatically

- Password hashing and session management
- JWT/session creation and validation
- Secure session storage for the current browser session
- Storage bucket and database primitives

## What you configure yourself

- The Auth provider and allowed methods
- Database collections, indexes, and permissions
- Bucket-level policies and validation rules
- File metadata documents that track ownership
