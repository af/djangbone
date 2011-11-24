=========
Djangbone
=========

Djangbone is a small django app that makes it easy to work with `Backbone.js
<http://backbonejs.org/>`_ frontends. More specifically, it allows you to
quickly build a backend that works with the default Backbone.sync implementation.

Djangbone provides one abstract class-based view (BackboneView), which gives you
hooks to customize it easily.


Example Usage
-------------

After downloading/installing djangbone, all you need to do is subclass
`BackboneView`, and then wire it up in your urlconf.

In myapp/views.py::

    from myapp.models import Widget
    from djangbone.views import BackboneView

    class WidgetView(BackboneView):
        base_queryset = Widget.objects.all()
        serialize_fields = ('id', 'name', 'description', 'created_at')
        add_form_class = ...    # Specify this if you want to support POST requests
        edit_form_class = ...   # Specify this if you want to support PUT requests

In myapp/urls.py::

    from myapp.views import WidgetView

    # Create url patterns for both "collections" and single items:
    urlpatterns = patterns('',
        url(r'^widgets', WidgetView.as_view()),
        url(r'^widgets/(?P<id>\d+)', WidgetView.as_view()),
    )

If you want to run the djangbone tests, you'll need to add `"djangobone"` to your
INSTALLED_APPS, and run `python manage.py test djangbone`.


Assumptions
-----------

Djangbone makes a few assumptions about your models in order to work:

    * your model has an integer primary key named 'id'


Alternatives
------------

Djangbone is designed to be a simple way to serialize your models to JSON in
a way that works with Backbone. It's not trying to be a generalized, 
format-agnostic API generator. If that's what you're looking for, you probably
will want to go with something like tastypie or django-piston instead.

If you're already using django-tastypie, or are looking for a more full-featured API
backend than Djangbone provides, you may want to look at `backbone-tastypie 
<https://github.com/PaulUithol/backbone-tastypie>`_, which overrides
Backbone.sync (via javascript) in a way that works nicely with tastypie.
