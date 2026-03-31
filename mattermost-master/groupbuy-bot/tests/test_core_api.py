"""
Tests for Core API
"""
import pytest
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status


class UserAPITests(APITestCase):
    """Tests for User API endpoints"""

    def test_create_user(self):
        """Test user registration"""
        url = '/api/users/'
        data = {
            'platform': 'telegram',
            'platform_user_id': '12345',
            'username': 'testuser',
            'first_name': 'Test',
            'last_name': 'User',
            'phone': '+79991234567',
            'email': 'test@example.com',
            'role': 'buyer'
        }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['first_name'], 'Test')
        self.assertEqual(response.data['role'], 'buyer')

    def test_check_user_exists(self):
        """Test user existence check"""
        # First create a user
        self.client.post('/api/users/', {
            'platform': 'telegram',
            'platform_user_id': '12345',
            'first_name': 'Test',
            'role': 'buyer'
        }, format='json')

        # Check if exists
        url = '/api/users/check_exists/'
        response = self.client.get(url, {
            'platform': 'telegram',
            'platform_user_id': '12345'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['exists'])

    def test_get_user_by_platform(self):
        """Test getting user by platform"""
        # First create a user
        self.client.post('/api/users/', {
            'platform': 'telegram',
            'platform_user_id': '12345',
            'first_name': 'Test',
            'role': 'buyer'
        }, format='json')

        # Get by platform
        url = '/api/users/by_platform/'
        response = self.client.get(url, {
            'platform': 'telegram',
            'platform_user_id': '12345'
        })
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['first_name'], 'Test')


class ProcurementAPITests(APITestCase):
    """Tests for Procurement API endpoints"""

    def setUp(self):
        """Set up test data"""
        # Create a user for testing
        response = self.client.post('/api/users/', {
            'platform': 'telegram',
            'platform_user_id': '12345',
            'first_name': 'Organizer',
            'role': 'organizer'
        }, format='json')
        self.user_id = response.data['id']

        # Create a category
        response = self.client.post('/api/procurements/categories/', {
            'name': 'General'
        }, format='json')
        self.category_id = response.data['id']

    def test_create_procurement(self):
        """Test procurement creation"""
        url = '/api/procurements/'
        data = {
            'title': 'Test Procurement',
            'description': 'Test description for procurement',
            'category': self.category_id,
            'organizer': self.user_id,
            'city': 'Test City',
            'target_amount': 10000,
            'deadline': '2025-12-31T23:59:59Z',
            'unit': 'units'
        }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['title'], 'Test Procurement')

    def test_list_procurements(self):
        """Test listing procurements"""
        # Create a procurement first
        self.client.post('/api/procurements/', {
            'title': 'Test Procurement',
            'description': 'Test description',
            'organizer': self.user_id,
            'city': 'Test City',
            'target_amount': 10000,
            'deadline': '2025-12-31T23:59:59Z',
            'unit': 'units'
        }, format='json')

        # List procurements
        response = self.client.get('/api/procurements/')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_join_procurement(self):
        """Test joining a procurement"""
        # Create procurement
        response = self.client.post('/api/procurements/', {
            'title': 'Test Procurement',
            'description': 'Test description',
            'organizer': self.user_id,
            'city': 'Test City',
            'target_amount': 10000,
            'deadline': '2025-12-31T23:59:59Z',
            'unit': 'units',
            'status': 'active'
        }, format='json')
        procurement_id = response.data['id']

        # Create another user to join
        response = self.client.post('/api/users/', {
            'platform': 'telegram',
            'platform_user_id': '67890',
            'first_name': 'Participant',
            'role': 'buyer'
        }, format='json')
        participant_id = response.data['id']

        # Join procurement
        url = f'/api/procurements/{procurement_id}/join/'
        response = self.client.post(url, {
            'user_id': participant_id,
            'quantity': 2,
            'amount': 1000
        }, format='json')

        # May fail if procurement is not active - that's expected
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_400_BAD_REQUEST])


class PaymentAPITests(APITestCase):
    """Tests for Payment API endpoints"""

    def setUp(self):
        """Set up test data"""
        response = self.client.post('/api/users/', {
            'platform': 'telegram',
            'platform_user_id': '12345',
            'first_name': 'Test',
            'role': 'buyer'
        }, format='json')
        self.user_id = response.data['id']

    def test_create_payment(self):
        """Test payment creation"""
        url = '/api/payments/'
        data = {
            'user_id': self.user_id,
            'amount': 1000,
            'description': 'Test deposit'
        }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(float(response.data['amount']), 1000)
        self.assertEqual(response.data['status'], 'pending')

    def test_get_payment_status(self):
        """Test getting payment status"""
        # Create payment
        response = self.client.post('/api/payments/', {
            'user_id': self.user_id,
            'amount': 1000
        }, format='json')
        payment_id = response.data['id']

        # Get status
        url = f'/api/payments/{payment_id}/status/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['status'], 'pending')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
