import json
from django.contrib.auth.models import User
from django.http import Http404
from django.test.client import RequestFactory
from django.utils import unittest

from djangbone.views import BackboneView


class MyView(BackboneView):
    """
    The subclass used to test BackboneView.
    """
    model = User
    serialize_fields = ('id', 'username', 'first_name', 'last_name')


class ViewTest(unittest.TestCase):
    """
    Tests for BackboneView.

    Note that django.contrib.auth must be in INSTALLED_APPS for these to work.
    """
    def setUp(self):
        self.factory = RequestFactory()
        self.view = MyView.as_view()
        self.user1 = User.objects.create(username='test1', first_name='Test', last_name='One')

    def tearDown(self):
        User.objects.all().delete()

    def add_two_more_users(self):
        self.user2 = User.objects.create(username='test2', first_name='Test', last_name='Two')
        self.user3 = User.objects.create(username='test3', first_name='Test', last_name='Three')

    def test_collection_get(self):
        request = self.factory.get('/users/')
        response = self.view(request)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)

        # Ensure response json deserializes to a 1-item list:
        self.assert_(isinstance(response_data, list))
        self.assertEqual(len(response_data), 1)
        self.assertEqual(response_data[0]['username'], self.user1.username)

        # Try again with a few more users in the database:
        self.add_two_more_users()
        response = self.view(request)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assert_(isinstance(response_data, list))
        self.assertEqual(len(response_data), 3)
        # With User model's default ordering (by id), user3 should be last:
        self.assertEqual(response_data[2]['username'], self.user3.username)

    def test_single_item_get(self):
        request = self.factory.get('/users/1')
        response = self.view(request, id='1')   # Simulate a urlconf passing in the 'id' kwarg
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assert_(isinstance(response_data, dict))
        self.assertEqual(response_data['username'], self.user1.username)

        # Ensure 404s are raised for non-existent items:
        request = self.factory.get('/users/7')
        self.assertRaises(Http404, lambda: self.view(request, id='7'))
