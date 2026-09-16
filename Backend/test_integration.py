"""RUN_INTEGRATION=1: testa o MySQL configurado usando apenas registros temporários.

Cria usuários e cadastros com um identificador exclusivo, excluindo somente
esses IDs no tearDownClass. Não altera registros já existentes.
"""
from io import BytesIO
import os
import secrets
import unittest
import uuid

from docx import Document
from werkzeug.security import generate_password_hash
from api import app
from security import database, digest


@unittest.skipUnless(os.getenv('RUN_INTEGRATION') == '1', 'Habilite RUN_INTEGRATION=1 para testar MySQL')
class IntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        app.config.update(TESTING=True, COOKIE_SECURE=False)
        cls.marker = 'test-' + uuid.uuid4().hex
        cls.password = secrets.token_urlsafe(24)
        cls.user_ids, cls.product_ids, cls.client_ids, cls.clients = [], [], [], {}
        with database() as (conn, cur):
            for role in ('admin', 'operador', 'consulta'):
                email = f'{cls.marker}-{role}@example.test'
                cur.execute('INSERT INTO users (name,email,password_hash,role) VALUES (%s,%s,%s,%s)',
                            (cls.marker, email, generate_password_hash(cls.password), role))
                cls.user_ids.append(cur.lastrowid)
            conn.commit()
        for role in ('admin', 'operador', 'consulta'):
            client = app.test_client()
            client.environ_base['REMOTE_ADDR'] = cls.marker
            response = client.post('/api/auth/login', json={'email':f'{cls.marker}-{role}@example.test','password':cls.password})
            assert response.status_code == 200, response.json
            cls.clients[role] = (client, {'X-CSRF-Token':response.json['data']['csrf']})

    @classmethod
    def tearDownClass(cls):
        with database() as (conn, cur):
            for identifier in cls.product_ids:
                cur.execute('DELETE FROM produtos WHERE id=%s', (identifier,))
            for identifier in cls.client_ids:
                cur.execute('DELETE FROM clientes WHERE id=%s', (identifier,))
            for identifier in cls.user_ids:
                cur.execute('DELETE FROM users WHERE id=%s', (identifier,))
            for scope in ['ip:' + cls.marker] + ['email:' + f'{cls.marker}-{role}@example.test' for role in ('admin', 'operador', 'consulta')]:
                cur.execute('DELETE FROM auth_attempts WHERE bucket=%s', (digest(scope),))
            conn.commit()

    def test_client_crud_and_duplicate(self):
        client, headers = self.clients['admin']
        digits = ''.join(str(secrets.randbelow(10)) for _ in range(14))
        data = dict(company='Empresa Árvore ' + self.marker, name='Decorações', cnpj=digits, state='SP', status='Ativo', revenue=12.34)
        created = client.post('/api/clientes', json=data, headers=headers)
        self.assertEqual(created.status_code, 201, created.json)
        identifier = created.json['data']['id']; self.client_ids.append(identifier)
        self.assertEqual(client.post('/api/clientes', json=data, headers=headers).status_code, 409)
        data['name'] = 'Comércio São José'
        updated = client.put(f'/api/clientes/{identifier}', json=data, headers=headers)
        self.assertEqual(updated.json['data']['name'], data['name'])
        self.assertEqual(client.delete(f'/api/clientes/{identifier}', headers=headers).status_code, 200)

    def test_product_crud_roles_and_unicode(self):
        operator, headers = self.clients['operador']; viewer, viewer_headers = self.clients['consulta']
        data = dict(name='Tinta Acrílica ' + self.marker, brand='São José', category='Tintas', stock=7, price=23.45)
        self.assertEqual(viewer.post('/api/produtos', json=data, headers=viewer_headers).status_code, 403)
        created = operator.post('/api/produtos', json=data, headers=headers)
        self.assertEqual(created.status_code, 201, created.json)
        identifier = created.json['data']['id']; self.product_ids.append(identifier)
        data['stock'] = 9
        self.assertEqual(operator.put(f'/api/produtos/{identifier}', json=data, headers=headers).json['data']['stock'], 9)
        self.assertEqual(operator.delete(f'/api/produtos/{identifier}', headers=headers).status_code, 403)
        rows = viewer.get('/api/produtos').json['data']
        self.assertEqual(next(r for r in rows if r['id'] == identifier)['name'], data['name'])

    def test_all_nine_reports(self):
        client, _ = self.clients['consulta']
        for kind in ('clientes', 'produtos', 'financeiro'):
            for extension in ('pdf', 'docx', 'csv'):
                with self.subTest(kind=kind, extension=extension):
                    response = client.get(f'/api/reports/{kind}.{extension}')
                    self.assertEqual(response.status_code, 200)
                    self.assertIn('attachment', response.headers['Content-Disposition'])
                    if extension == 'pdf': self.assertTrue(response.data.startswith(b'%PDF'))
                    elif extension == 'docx': self.assertGreaterEqual(len(Document(BytesIO(response.data)).tables), 1)
                    else: self.assertTrue(response.data.startswith(b'\xef\xbb\xbf'))

    def test_admin_user_management_and_revocation(self):
        admin, headers = self.clients['admin']
        data = dict(name=self.marker + '-extra', email=self.marker + '-extra@example.test', role='consulta', password=self.password)
        created = admin.post('/api/users', json=data, headers=headers)
        self.assertEqual(created.status_code, 201, created.json)
        identifier = created.json['data']['id']; self.user_ids.append(identifier)
        client = app.test_client(); client.environ_base['REMOTE_ADDR'] = self.marker
        login = client.post('/api/auth/login', json=data)
        self.assertEqual(login.status_code, 200)
        self.assertIn('HttpOnly', login.headers['Set-Cookie'])
        self.assertIn('SameSite=Lax', login.headers['Set-Cookie'])
        data.update(active=False, password='')
        self.assertEqual(admin.put(f'/api/users/{identifier}', json=data, headers=headers).status_code, 200)
        self.assertEqual(client.get('/api/auth/me').status_code, 401)
        with database() as (conn, cur):
            cur.execute('DELETE FROM auth_attempts WHERE bucket=%s', (digest('email:' + data['email']),)); conn.commit()

    def test_logout_revokes_server_session(self):
        client = app.test_client(); client.environ_base['REMOTE_ADDR'] = self.marker
        login = client.post('/api/auth/login', json={'email':f'{self.marker}-consulta@example.test','password':self.password})
        headers = {'X-CSRF-Token':login.json['data']['csrf']}
        self.assertEqual(client.post('/api/auth/logout', headers=headers).status_code, 200)
        self.assertEqual(client.get('/api/auth/me').status_code, 401)

    def test_password_change_revokes_other_sessions(self):
        # Usuário extra: não invalida sessões usadas pelos demais testes.
        admin, headers = self.clients['admin']
        data = dict(name=self.marker, email=self.marker + '-password@example.test', role='consulta', password=self.password)
        result = admin.post('/api/users', json=data, headers=headers)
        self.assertEqual(result.status_code, 201)
        self.user_ids.append(result.json['data']['id'])
        one, two = app.test_client(), app.test_client()
        for client in (one, two):
            client.environ_base['REMOTE_ADDR'] = self.marker
            login = client.post('/api/auth/login', json=data)
            self.assertEqual(login.status_code, 200)
        csrf = one.get('/api/auth/me').json['data']['csrf']
        headers = {'X-CSRF-Token': csrf}
        self.assertEqual(one.post('/api/auth/password', json={'currentPassword':'incorrect', 'password':self.password}, headers=headers).status_code, 403)
        new_password = secrets.token_urlsafe(24)
        changed = one.post('/api/auth/password', json={'currentPassword':self.password, 'password':new_password}, headers=headers)
        self.assertEqual(changed.status_code, 200)
        self.assertEqual(one.get('/api/auth/me').status_code, 200)
        self.assertEqual(two.get('/api/auth/me').status_code, 401)
        self.assertEqual(two.post('/api/auth/login', json=data).status_code, 401)
        data['password'] = new_password
        self.assertEqual(two.post('/api/auth/login', json=data).status_code, 200)
        with database() as (conn, cur):
            cur.execute('DELETE FROM auth_attempts WHERE bucket=%s', (digest('email:' + data['email']),))
            conn.commit()


if __name__ == '__main__': unittest.main()
