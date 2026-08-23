const APPWRITE_ENDPOINT = 'https://sgp.cloud.appwrite.io/v1';
const APPWRITE_PROJECT_ID = '6a89db4c00229eba40ca';
const APPWRITE_DATABASE_ID = '6a89dc580022c8de2e51';
const PROFILES_COLLECTION_ID = 'profiles';
const FILES_COLLECTION_ID = 'files';
const STORAGE_BUCKET_ID = '6a8a8af20011e4c3163d';

const client = new Appwrite.Client();
client.setEndpoint(APPWRITE_ENDPOINT).setProject(APPWRITE_PROJECT_ID);

const account = new Appwrite.Account(client);
const databases = new Appwrite.Databases(client);
const storage = new Appwrite.Storage(client);

async function ensureProfileRecord(user) {
  const currentEmail = user.email;
  const currentName = user.name || currentEmail.split('@')[0];
  const profileQuery = await databases.listDocuments(APPWRITE_DATABASE_ID, PROFILES_COLLECTION_ID, [
    Appwrite.Query.equal('userId', user.$id)
  ]);

  if (profileQuery.documents.length === 0) {
    return databases.createDocument(
      APPWRITE_DATABASE_ID,
      PROFILES_COLLECTION_ID,
      Appwrite.ID.unique(),
      {
        userId: user.$id,
        name: currentName,
        email: currentEmail,
        createdAt: new Date().toISOString()
      }
    );
  }

  return profileQuery.documents[0];
}

async function doRegister() {
  const email = document.getElementById('regEmail').value.trim();
  const password = document.getElementById('regPassword').value;
  const name = email.split('@')[0];

  try {
    const user = await account.create(Appwrite.ID.unique(), email, password, name);
    await account.createEmailPasswordSession(email, password);
    const profile = await ensureProfileRecord(user);
    log('POST /register', { status: 201, user, profile });
  } catch (error) {
    log('POST /register', { status: error.code || 400, body: { error: error.message || 'Registration failed' } });
  }
}

async function doLogin() {
  const email = document.getElementById('loginEmail').value.trim();
  const password = document.getElementById('loginPassword').value;

  try {
    const session = await account.createEmailPasswordSession(email, password);
    const user = await account.get();
    document.getElementById('token').value = 'appwrite-session-active';
    log('POST /login', { status: 200, session, user });
  } catch (error) {
    log('POST /login', { status: error.code || 401, body: { error: error.message || 'Invalid email or password' } });
  }
}

async function doLogout() {
  try {
    await account.deleteSession('current');
    document.getElementById('token').value = '';
    log('POST /logout', { status: 200, body: { message: 'Logged out' } });
  } catch (error) {
    log('POST /logout', { status: error.code || 400, body: { error: error.message || 'Logout failed' } });
  }
}

async function getMe() {
  try {
    const user = await account.get();
    const profile = await databases.listDocuments(APPWRITE_DATABASE_ID, PROFILES_COLLECTION_ID, [
      Appwrite.Query.equal('userId', user.$id)
    ]);
    log('GET /me', { status: 200, body: { user, profile: profile.documents[0] || null } });
  } catch (error) {
    log('GET /me', { status: error.code || 401, body: { error: error.message || 'Not authenticated' } });
  }
}

async function getFiles() {
  try {
    const user = await account.get();
    const result = await databases.listDocuments(APPWRITE_DATABASE_ID, FILES_COLLECTION_ID, [
      Appwrite.Query.equal('userId', user.$id)
    ]);
    if (result.documents[0]?.fileId) {
      document.getElementById('fileId').value = result.documents[0].fileId;
    }
    log('GET /files', { status: 200, body: { files: result.documents } });
  } catch (error) {
    log('GET /files', { status: error.code || 401, body: { error: error.message || 'Not authenticated' } });
  }
}

async function findOwnedFile(fileIdentifier) {
  const user = await account.get();
  const result = await databases.listDocuments(APPWRITE_DATABASE_ID, FILES_COLLECTION_ID, [
    Appwrite.Query.equal('userId', user.$id)
  ]);
  return result.documents.find((file) => file.fileId === fileIdentifier || file.$id === fileIdentifier) || null;
}

async function getFileById() {
  const id = document.getElementById('fileId').value.trim();
  try {
    const file = await findOwnedFile(id);
    if (!file) {
      log('GET /files/' + id, { status: 404, body: { error: 'File not found or access denied' } });
      return;
    }
    log('GET /files/' + id, { status: 200, body: { file } });
  } catch (error) {
    log('GET /files/' + id, { status: error.code || 401, body: { error: error.message || 'Not authenticated' } });
  }
}

async function downloadFileById() {
  const id = document.getElementById('fileId').value.trim();
  try {
    const fileMeta = await findOwnedFile(id);
    if (!fileMeta) {
      log('GET /files/' + id + '/download', { status: 403, body: { error: 'Access denied' } });
      return;
    }

    const url = storage.getFileDownload(STORAGE_BUCKET_ID, fileMeta.fileId);
    window.open(url, '_blank', 'noopener');
    log('GET /files/' + id + '/download', { status: 200, body: { note: 'File download triggered.', file: fileMeta } });
  } catch (error) {
    log('GET /files/' + id + '/download', { status: error.code || 401, body: { error: error.message || 'Download failed' } });
  }
}

window.appwriteAuthAdapter = {
  client,
  account,
  databases,
  storage,
  doRegister,
  doLogin,
  doLogout,
  getMe,
  getFiles,
  getFileById,
  downloadFileById,
  APPWRITE_ENDPOINT,
  APPWRITE_PROJECT_ID,
  APPWRITE_DATABASE_ID,
  FILES_COLLECTION_ID,
  PROFILES_COLLECTION_ID,
  STORAGE_BUCKET_ID,
};

console.info('Appwrite client adapter ready. Replace the mock fetch layer with this script when selecting Appwrite mode.');
