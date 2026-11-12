from unittest.mock import patch

from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status

from accounts.models.users import UserProfile


class GoogleLoginTests(APITestCase):

    def setUp(self):
        self.url = '/api/auth/google/'

    def test_sin_credencial(self):
        response = self.client.post(self.url, {})

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )

    @patch('api.views.id_token.verify_oauth2_token')
    def test_credencial_invalida(self, mock_verify):
        mock_verify.side_effect = ValueError()

        response = self.client.post(
            self.url,
            {'credential': 'credencial_invalida'}
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED
        )

    @patch('api.views.id_token.verify_oauth2_token')
    def test_correo_no_verificado(self, mock_verify):
        mock_verify.return_value = {
            'sub': 'google123',
            'email': 'usuario@gmail.com',
            'email_verified': False
        }

        response = self.client.post(
            self.url,
            {'credential': 'credencial_valida'}
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST
        )

    @patch('api.views.id_token.verify_oauth2_token')
    def test_crear_usuario_nuevo(self, mock_verify):
        mock_verify.return_value = {
            'sub': 'google123',
            'email': 'usuario@gmail.com',
            'email_verified': True,
            'given_name': 'Usuario',
            'family_name': 'Prueba',
            'picture': 'https://example.com/foto.jpg'
        }

        response = self.client.post(
            self.url,
            {'credential': 'credencial_valida'}
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(UserProfile.objects.count(), 1)

        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

        self.assertEqual(
            response.data['user']['email'],
            'usuario@gmail.com'
        )

    @patch('api.views.id_token.verify_oauth2_token')
    def test_reutilizar_usuario_existente(self, mock_verify):
        user = User.objects.create_user(
            username='google_google123',
            email='usuario@gmail.com'
        )

        UserProfile.objects.create(
            user=user,
            google_sub='google123'
        )

        mock_verify.return_value = {
            'sub': 'google123',
            'email': 'usuario@gmail.com',
            'email_verified': True
        }

        response = self.client.post(
            self.url,
            {'credential': 'credencial_valida'}
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(UserProfile.objects.count(), 1)

    def test_current_user_sin_autenticacion(self):
        response = self.client.get('/api/auth/me/')

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED
        )


    def test_current_user_autenticado(self):
        user = User.objects.create_user(
            username='usuario_prueba',
            email='usuario@gmail.com'
        )

        UserProfile.objects.create(
            user=user,
            google_sub='google123'
        )

        self.client.force_authenticate(user=user)

        response = self.client.get('/api/auth/me/')

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK
        )

        self.assertEqual(
            response.data['email'],
            'usuario@gmail.com'
        )

        self.assertIn('is_admin', response.data)    