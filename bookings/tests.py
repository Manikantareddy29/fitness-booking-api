from datetime import timedelta
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from unittest.mock import patch, MagicMock

from bookings.models import Booking, FitnessClass
import base64


class FitnessClassListTests(APITestCase):
    
    def setUp(self):
        self.url = reverse('fitness-classes-list')

        self.class_1 = FitnessClass.objects.create(
            name="Yoga",
            datetime=timezone.now() + timezone.timedelta(days=1),
            instructor="John Doe",
            available_slots=10
        )
        self.class_2 = FitnessClass.objects.create(
            name="Zumba",
            datetime=timezone.now() + timezone.timedelta(days=2),
            instructor="Jane Smith",
            available_slots=5
        )
        self.past_class = FitnessClass.objects.create(
            name="Pilates",
            datetime=timezone.now() - timezone.timedelta(days=1),
            instructor="Old Trainer",
            available_slots=15
        )

    def test_get_fitness_classes_success(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        self.assertIn("Yoga", [c["name"] for c in response.data])
        self.assertIn("Zumba", [c["name"] for c in response.data])
        self.assertNotIn("Pilates", [c["name"] for c in response.data])

    def test_get_fitness_classes_empty(self):
        FitnessClass.objects.all().delete()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_internal_error_handling(self):
        from unittest.mock import patch
        with patch('bookings.views.FitnessClass.objects.filter') as mock_filter:
            mock_filter.side_effect = Exception("Simulated DB failure")
            response = self.client.get(self.url)
            self.assertEqual(response.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)
            self.assertIn("error", response.data)



def get_basic_auth_header(username, password):
    credentials = f'{username}:{password}'
    base64_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
    return {
        'HTTP_AUTHORIZATION': f'Basic {base64_credentials}',
    }

class FitnessClassCreateAdminTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='normaluser', password='password123')
        self.admin_user = User.objects.create_superuser(username='adminuser', password='adminpass')

        self.client = APIClient()
        self.url = reverse('fitness-class-create-admin')

        self.valid_payload = {
        "fitness_class_name": "Zumba",
        "class_datetime": "06/06/2025 06:30 AM",
        "instructor": "John Doe",
        "available_slots": 20
        }

    def test_admin_can_create_fitness_class(self):
        auth_headers = get_basic_auth_header('adminuser', 'adminpass')
        response = self.client.post(self.url, self.valid_payload, format='json', **auth_headers)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_non_admin_user_cannot_create(self):
        auth_headers = get_basic_auth_header('normaluser', 'password123')
        response = self.client.post(self.url, self.valid_payload, format='json', **auth_headers)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_validation_failure_returns_400(self):
        auth_headers = get_basic_auth_header('adminuser', 'adminpass')
        invalid_payload = {
            "datetime": "10/06/2025 08:00 AM",
            "instructor": "John Doe",
            "available_slots": 15
        }
        response = self.client.post(self.url, invalid_payload, format='json', **auth_headers)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)



class BookingCreateTests(APITestCase):
    def setUp(self):
        self.fitness_class = FitnessClass.objects.create(
            name="Yoga",
            datetime="2025-06-10 08:00:00",
            instructor="John Doe",
            available_slots=5
        )
        self.url = reverse('booking-create') 

    def test_booking_successful_when_slots_available(self):
        payload = {
            "fitness_class": self.fitness_class.id,
            "client_name": "Alice",
            "client_email": "alice@example.com"
        }
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.fitness_class.refresh_from_db()
        self.assertEqual(self.fitness_class.available_slots, 4)

    def test_booking_fails_if_fitness_class_missing(self):
        payload = {
            "client_name": "Charlie",
            "client_email": "charlie@example.com"
          
        }
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertIn('fitness_class', response.data)
        error_list = response.data['fitness_class']
        self.assertTrue(any(err.code == 'required' for err in error_list))


    @patch('bookings.views.BookingSerializer.save') 
    def test_unexpected_error_during_save(self, mock_save):
        mock_save.side_effect = Exception("DB failure")

        payload = {
            "fitness_class": self.fitness_class.id,
            "client_name": "Eve",
            "client_email": "eve@example.com"
        }
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertIn('An unexpected error occurred', str(response.data))



class BookingListByEmailTests(APITestCase):
    def setUp(self):
        self.url = "/bookings/"
        self.email = "testuser@example.com"

        self.fitness_class = FitnessClass.objects.create(
            name="Zumba",
            datetime=timezone.now(),
            instructor="John Doe",
            available_slots=10
        )

        self.booking = Booking.objects.create(
            fitness_class=self.fitness_class,
            client_name="Test User",
            client_email=self.email
        )

    def test_returns_200_with_valid_email(self):
        response = self.client.get(self.url, {"email": self.email})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['client_email'], self.email)

    def test_returns_empty_list_for_unknown_email(self):
        response = self.client.get(self.url, {"email": "unknown@example.com"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    def test_returns_400_if_email_missing(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data["error"], "Email parameter is required.")

    def test_returns_500_if_db_error(self):
        Booking.objects.all().delete()
        FitnessClass.objects.all().delete()

        response = self.client.get(self.url, {"email": self.email})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
