import sys
from fastapi.testclient import TestClient

sys.path.insert(0, '.')
from app.main import app

client = TestClient(app)

reg = client.post('/api/register', json={'email': 'dana@example.com', 'password': 'Password123!', 'name': 'Dana'})
print('REGISTER', reg.status_code, reg.json())

login = client.post('/api/login', json={'email': 'alice@example.com', 'password': 'Password123!'})
print('LOGIN', login.status_code, login.json())

token = login.json()['token']
headers = {'Authorization': f'Bearer {token}'}
me = client.get('/api/user', headers=headers)
print('ME', me.status_code, me.json())

files = client.get('/api/files', headers=headers)
print('FILES', files.status_code, files.json())
file_id = files.json()['files'][0]['id']

download = client.get(f'/api/files/{file_id}/download', headers=headers)
print('DOWNLOAD', download.status_code, download.headers.get('content-type'))

acct = client.post('/api/login', json={'email': 'bob@example.com', 'password': 'Password123!'})
other_token = acct.json()['token']
forbidden = client.get(f'/api/files/{file_id}', headers={'Authorization': f'Bearer {other_token}'})
print('FORBIDDEN', forbidden.status_code, forbidden.json())

bad = client.post('/api/login', json={'email': 'unknown@example.com', 'password': 'bad'})
print('BAD_LOGIN', bad.status_code, bad.json())
