"""Regressões de validação, autenticação e geração de documentos sem banco."""
from contextlib import contextmanager
from io import BytesIO
import unittest
from unittest.mock import MagicMock, patch

from docx import Document
from api import app, normalizar_numero, validar_cliente, validar_produto
from reports import make_csv, make_docx, make_pdf


class SecurityTest(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True, COOKIE_SECURE=False)
        self.client = app.test_client()

    @contextmanager
    def session(self, role="consulta"):
        self.client.set_cookie("nexusgest_session", "test-session")
        cursor = MagicMock()
        cursor.fetchone.return_value = dict(id=1, name="Teste", email="test@example.test", role=role, active=True, csrf_token="csrf-test")
        @contextmanager
        def db():
            yield MagicMock(), cursor
        with patch("security.database", db):
            yield

    def test_anonymous_routes_are_protected(self):
        for path in ("/api/clientes", "/api/produtos", "/api/users", "/api/reports/clientes.pdf"):
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 401)

    def test_consulta_cannot_write(self):
        with self.session():
            self.assertEqual(self.client.post('/api/produtos', json={}, headers={'X-CSRF-Token':'csrf-test'}).status_code, 403)
            self.assertEqual(self.client.get('/api/users').status_code, 403)

    def test_operador_cannot_delete(self):
        with self.session('operador'):
            self.assertEqual(self.client.delete('/api/clientes/1', headers={'X-CSRF-Token':'csrf-test'}).status_code, 403)

    def test_admin_still_requires_csrf(self):
        with self.session('admin'):
            self.assertEqual(self.client.post('/api/produtos', json={}).status_code, 403)

    def test_login_cross_origin_is_rejected(self):
        self.assertEqual(self.client.post('/api/auth/login', json={}, headers={'Origin':'https://attacker.example'}).status_code, 403)

    def test_invalid_setup_token(self):
        with patch('security.setup_token', return_value='a' * 32):
            self.assertEqual(self.client.post('/api/auth/setup', json={}).status_code, 403)

    def test_last_admin_cannot_be_disabled(self):
        self.client.set_cookie('nexusgest_session', 'test-session')
        cursor = MagicMock()
        cursor.fetchone.return_value = dict(id=1, name='Admin', email='admin@example.test', role='admin', active=True, csrf_token='csrf-test')
        cursor.fetchall.return_value = [{'id':1}]
        @contextmanager
        def db():
            yield MagicMock(), cursor
        with patch('security.database', db):
            response = self.client.put('/api/users/1', json=dict(name='Admin', email='admin@example.test', role='consulta', active=False), headers={'X-CSRF-Token':'csrf-test'})
            self.assertEqual(response.status_code, 409)

    def test_invalid_session_is_rejected(self):
        self.client.set_cookie('nexusgest_session', 'invalid')
        cursor = MagicMock(); cursor.fetchone.return_value = None
        @contextmanager
        def db():
            yield MagicMock(), cursor
        with patch('security.database', db):
            self.assertEqual(self.client.get('/api/auth/me').status_code, 401)

    def test_body_is_bounded(self):
        response = self.client.post('/api/auth/login', json={'email':'a' * 70000})
        self.assertEqual(response.status_code, 413)

    def test_security_headers(self):
        response = self.client.get('/api/clientes')
        self.assertEqual(response.headers['Cache-Control'], 'no-store')
        self.assertEqual(response.headers['X-Content-Type-Options'], 'nosniff')
        self.assertNotIn('Access-Control-Allow-Origin', response.headers)

    def test_numbers_reject_non_finite_and_fractional_stock(self):
        for value in ('NaN', 'Infinity', '-Infinity', -1, True, 10**30):
            self.assertIsNotNone(normalizar_numero(value, 'Preço')[1])
        self.assertIsNotNone(normalizar_numero('2.5', 'Estoque', inteiro=True)[1])

    def test_required_client_fields(self):
        self.assertEqual(validar_cliente({})[1], 'Razão social é obrigatória.')
        self.assertIsNotNone(validar_produto(dict(name='Tinta', category='Tintas', brand='Teste', stock=-1, price=5))[1])

    def test_reports_preserve_portuguese_and_escape_csv(self):
        columns = ['Nome', 'Preço']
        rows = [['Decorações & Tinta "Acrílica"', 'R$ 10,00'], ['=1+1', '2']]
        pdf = make_pdf('Produtos', columns, rows, 'José')
        self.assertTrue(pdf.read().startswith(b'%PDF'))
        docx = make_docx('Produtos', columns, rows, 'José')
        document = Document(docx)
        self.assertEqual(document.tables[0].rows[1].cells[0].text, rows[0][0])
        csv = make_csv(columns, rows).getvalue()
        self.assertTrue(csv.startswith(b'\xef\xbb\xbf'))
        self.assertIn("'=1+1", csv.decode('utf-8-sig'))
        self.assertIn('""Acrílica""', csv.decode('utf-8-sig'))

    @patch('api.conectar_banco', return_value=None)
    def test_health_unavailable(self, _):
        self.assertEqual(self.client.get('/api/health').status_code, 503)


if __name__ == '__main__':
    unittest.main()
