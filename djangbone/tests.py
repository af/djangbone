import json
from django import forms
from django.contrib.auth.models import User
from django.http import Http404
from django.test.client import RequestFactory
from django.utils import unittest

from djangbone.views import BackboneAPIView


class AddUserForm(forms.ModelForm):
    """
    Simple ModelForm for testing POST requests.
    """
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name')

    def set_request(self, request):
        """
        add_form_class and edit_form_class classes can optionally provide this
        method in order to get access to the request object.
        """
        self.request = request

class EditUserForm(forms.ModelForm):
    """
    Simple ModelForm for testing PUT requests.
    """
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name')

    def set_request(self, request):
        """
        add_form_class and edit_form_class classes can optionally provide this
        method in order to get access to the request object.
        """
        self.request = request


class ReadOnlyView(BackboneAPIView):
    """
    BackboneAPIView subclass for testing read-only functionality.
    """
    base_queryset = User.objects.all()
    serialize_fields = ('id', 'username', 'first_name', 'last_name')

class FullView(BackboneAPIView):
    """
    The subclass used to test BackboneAPIView's PUT/POST requests.
    """
    base_queryset = User.objects.all()
    add_form_class = AddUserForm
    edit_form_class = EditUserForm
    serialize_fields = ('id', 'username', 'first_name', 'last_name')
    page_size = 2


class ViewTest(unittest.TestCase):
    """
    Tests for BackboneAPIView.

    Note that django.contrib.auth must be in INSTALLED_APPS for these to work.
    """
    def setUp(self):
        self.factory = RequestFactory()
        self.view = ReadOnlyView.as_view()
        self.writable_view = FullView.as_view()
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

        # Test pagination:
        response = self.writable_view(request)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assert_(isinstance(response_data, list))
        self.assertEqual(len(response_data), 2)

        # Page 2 should only have one item:
        request = self.factory.get('/users/?p=2')
        response = self.writable_view(request)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assert_(isinstance(response_data, list))
        self.assertEqual(len(response_data), 1)

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

    def test_post(self):
        request = self.factory.post('/users')
        response = self.view(request)
        self.assertEqual(response.status_code, 405)     # "Method not supported" if no add_form_class specified

        # Testing BackboneAPIView subclasses that support POST via add_form_class:

        # If no JSON provided in POST body, return HTTP 400:
        response = self.writable_view(request)
        self.assertEqual(response.status_code, 400)

        # Test the case where invalid input is given (leading to form errors):
        request = self.factory.post('/users', '{"wrong_field": "xyz"}', content_type='application/json')
        response = self.writable_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, 'ERROR: validation failed')

        # If valid JSON was provided, a new instance should be created:
        request = self.factory.post('/users', '{"username": "post_test"}', content_type='application/json')
        response = self.writable_view(request)
        self.assertEqual(response.status_code, 200)
        self.assert_(User.objects.get(username='post_test'))
        response_json = json.loads(response.content)
        self.assertEqual(response_json['username'], 'post_test')

    def test_put(self):
        request = self.factory.put('/users/1')
        response = self.view(request, id='1')
        self.assertEqual(response.status_code, 405)     # "Method not supported" if no edit_form_class specified

        # PUT is also not supported for collections (when no id is provided):
        request = self.factory.put('/users')
        response = self.writable_view(request)
        self.assertEqual(response.status_code, 405)

        # If no JSON in PUT body, return HTTP 400:
        response = self.writable_view(request, id='1')
        self.assertEqual(response.status_code, 400)

        # Raise 404 if an object with the given id doesn't exist:
        request = self.factory.put('/users/27', '{"username": "put_test"}', content_type='application/json')
        self.assertRaises(Http404, lambda: self.writable_view(request, id='27'))

        # If the object exists and an edit_form_class is supplied, it actually does something:
        request = self.factory.put('/users/1', '{"username": "put_test"}', content_type='application/json')
        response = self.writable_view(request, id='1')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.get(id=1).username, 'put_test')
        response_json = json.loads(response.content)
        self.assertEqual(response_json['username'], 'put_test')

        # Test the case where invalid input is given (leading to form errors):
        request = self.factory.put('/users/1', '{"wrong_field": "xyz"}', content_type='application/json')
        response = self.writable_view(request, id='1')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, 'ERROR: validation failed')

    def test_delete(self):
        # Delete is not supported for collections:
        request = self.factory.delete('/users')
        response = self.view(request)
        self.assertEqual(response.status_code, 405)
        self.assertEqual(User.objects.filter(id=1).count(), 1)

        # But it is supported for single items (specified by id):
        request = self.factory.delete('/users/1')
        response = self.view(request, id='1')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(User.objects.filter(id=1).count(), 0)

        # Should raise 404 if we try to access a deleted resource again:
        request = self.factory.delete('/users/1')
        self.assertRaises(Http404, lambda: self.view(request, id='1'))
