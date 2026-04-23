from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from accounts.models import CustomUser

class JWTAuthenticationTests(APITestCase):
    def setUp(self):
        self.user = CustomUser.objects.create_user(
            username='testuser', 
            password='testpassword123',
            role='PATIENT'
        )
        self.url = '/api/token/'

    def test_jwt_login_successful(self):
        response = self.client.post(self.url, {
            'username': 'testuser',
            'password': 'testpassword123'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)

    def test_invalid_login_returns_401(self):
        response = self.client.post(self.url, {
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertNotIn('access', response.data)

    def test_protected_endpoint_without_token_returns_401(self):
        response = self.client.get('/api/patients/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_expired_token_returns_401(self):
        from rest_framework_simplejwt.tokens import AccessToken
        from django.utils import timezone
        import datetime
        
        token = AccessToken.for_user(self.user)
        # Manually backdate the token
        token.payload['exp'] = (timezone.now() - datetime.timedelta(days=1)).timestamp()
        
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
        response = self.client.get('/api/patients/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
