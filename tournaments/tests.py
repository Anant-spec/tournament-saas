from rest_framework.test import APITestCase
from rest_framework.authtoken.models import Token
from django.contrib.auth import get_user_model

User = get_user_model()

class TournamentAPITest(APITestCase):

    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='pass123')
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)

    def test_unauthenticated_request_returns_401(self):
        self.client.credentials()  # remove auth
        response = self.client.get('/api/tournaments/')
        self.assertEqual(response.status_code, 401)

    def test_authenticated_user_can_list_tournaments(self):
        response = self.client.get('/api/tournaments/')
        self.assertEqual(response.status_code, 200)

    def test_tournament_list_returns_empty_for_new_user(self):
        response = self.client.get('/api/tournaments/')
        self.assertEqual(response.data, [])