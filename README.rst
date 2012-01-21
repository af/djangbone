=========
Djangbone
=========

Djangbone is a small django app that makes it easy to work with `Backbone.js
<http://backbonejs.org/>`_ frontends. More specifically, it allows you to
quickly build a web API that works with the default Backbone.sync implementation.

Djangbone provides one abstract class-based view (BackboneAPIView), which has a
bunch of hooks for customization.


Example Usage
-------------

After downloading/installing djangbone, all you need to do is:

#. Subclass ``BackboneAPIView``, and set the ``base_queryset`` and
   ``serialize_fields`` attributes.
#. Wire up the view subclass in your urlconf.

For example, in myapp/views.py::

    from myapp.models import Widget
    from djangbone.views import BackboneAPIView

    class WidgetView(BackboneAPIView):
        # base_queryset is a queryset that contains all the objects that are
        # accessible by the API:
        base_queryset = Widget.objects.all()

        # serialize_fields is a list of model fields that you want to be sent
        # in your JSON resonses:
        serialize_fields = ('id', 'name', 'description', 'created_at')

In myapp/urls.py::

    from myapp.views import WidgetView

    # Create url patterns for both "collections" and single items:
    urlpatterns = patterns('',
        url(r'^widgets$', WidgetView.as_view()),
        url(r'^widgets/(?P<id>\d+)', WidgetView.as_view()),
    )

If you want to run the djangbone tests, you'll need to add ``"djangobone"`` to your
INSTALLED_APPS, and run ``python manage.py test djangbone``. The tests use
``django.contrib.auth``, so that app will also need to be in your INSTALLED_APPS
for the tests to work.


Handling POST and PUT requests
------------------------------

Backbone.sync uses POST requests when new objects are created, and PUT requests
when objects are changed. If you want to support these HTTP methods, you need to
specify which form classes to use for validation for each request type.

To do this, give your BackboneAPIView subclass ``add_form_class`` and
``edit_form_class`` attributes. Usually you'll want to use a ModelForm
for both, but regardless, each form's save() method should return the model
instance that was created or modified.

Here's an example (assume AddWidgetForm and EditWidgetForm are both ModelForms)::

    from djangbone.views import BackboneAPIView
    from myapp.models import Widget
    from myapp.forms import AddWidgetForm, EditWidgetForm

    class WidgetView(BackboneAPIView):
        base_queryset = ...
        serialize_fields = ...
        add_form_class = AddWidgetForm      # Used for POST requests
        edit_form_class = EditWidgetForm    # Used for PUT requests

If you need access to the ``request`` object in your form classes (maybe to
save ``request.user`` to your model, or perform extra validation), add
a ``set_request()`` method to your form classes as follows::

    class AddWidgetForm(ModelForm):
        class Meta:
            model = Widget

        def set_request(self, request):
            self.request = request

        # Now you have access to self.request in clean() and save()


Pagination
----------

If you want to limit the number of items returned for a collection, you can
turn on basic pagination with BackboneAPIView's ``page_size`` attribute. Set it to
an integer and GETs without an ``id`` will be paginated. The default GET
parameter is "p", but you can override this with
``BackboneAPIView.page_param_name``.


Customization
-------------

There's a decent chance that you'll want to wrap your BackboneAPIView subclass
with additional functionality, for example to only allow registered users to
access this view. You can use django's method_decorator on BackboneAPIView's
dispatch() method to do this as follows::

    from django.contrib.auth.decorators import login_required
    from django.utils.decorators import method_decorator

    class WidgetView(BackboneAPIView):
        ...

        @method_decorator(login_required)
        def dispatch(self, request, *args, **kwargs):
            return super(WidgetView, self).dispatch(*args, **kwargs)


You might also want to vary the base_queryset depending on the request (or an
extra url parameter). You can also override dispatch() to do this, for example::

    class WidgetView(BackboneAPIView):
        base_queryset = Widgets.objects.all()

        def dispatch(self, request, *args, **kwargs):
            if request.method in ['PUT', 'DELETE']:
                self.base_queryset = Widgets.objects.filter(owner=request.user)
            return super(WidgetView, self).dispatch(*args, **kwargs)


A Note on CSRF Protection
-------------------------

Backbone.sync sends POST request data as JSON, which doesn't work so well with
`Django's built-in CSRF middleware <https://docs.djangoproject.com/en/1.3/ref/contrib/csrf/>`_
(the latter expects form-encoded POST data). As a result, if you're using the CSRF
middleware, you'll want to either:

#. Wrap your BackboneAPIView's dispatch method with the csrf_exempt decorator
   to disable CSRF protection, or...
#. (recommended) In javascript, configure jQuery's ajax method to always send
   the ``X-CSRFToken`` HTTP header. See the `Django CSRF docs
   <https://docs.djangoproject.com/en/1.3/ref/contrib/csrf/#ajax>`_ for one way
   to do it, or if you have ``{% csrf_token %}`` somewhere in your Django
   template you can use something like::

       // Setup $.ajax to always send an X-CSRFToken header:
       var csrfToken = $('input[name=csrfmiddlewaretoken]').val();
       $(document).ajaxSend(function(e, xhr, settings) {
           xhr.setRequestHeader('X-CSRFToken', csrfToken);
       });


Requirements
------------

Djangbone uses class-based views, and as such will only work with Django 1.3
and above. Python 2.6+ is also required.

Djangbone makes a few assumptions about your models in order to work:

    * Your model has an integer primary key named 'id' (Django creates this
      field by default).
    * The model fields in ``serialize_fields`` can be serialized to JSON.
      This isn't a problem for simple CharFields, IntegerFields, etc, but
      more complex fields will not work by default. You can fix this by
      overriding ``BackboneAPIView.json_encoder`` with your own JSONEncoder subclass.
      See the djangbone source for an example of this, which adds support for
      serializing ``datetime`` instances.


Alternatives
------------

Djangbone is designed to be a simple way to serialize your models to JSON in
a way that works with Backbone. It's not trying to be a generalized,
format-agnostic API generator. If that's what you're looking for, you probably
will want to go with something like django-tastypie or django-piston instead.

If you're already using django-tastypie, or are looking for a more full-featured API
backend than Djangbone provides, you may want to look at `backbone-tastypie
<https://github.com/PaulUithol/backbone-tastypie>`_, which overrides
Backbone.sync (via javascript) in a way that works nicely with tastypie.
