from datetime import datetime
import json     #FIXME: fallback to simplejson if json not available

from django.http import HttpResponse, Http404
from django.views.generic import View


class BackboneView(View):
    """
    Abstract class view, which makes it easy for subclasses to talk to backbone.js.

    Supported operations (copied from backbone.js docs):
        create -> POST   /collection
        read ->   GET    /collection[/id]
        update -> PUT    /collection/id
        delete -> DELETE /collection/id

    Assumptions:
        - Your model has an integer primary key named 'id'
        - Your model has a Manager at Mymodel.objects
    """
    model = None
    serialize_fields = tuple()

    def get(self, request, *args, **kwargs):
        """
        Handle GET requests, either for a single resource or a collection.
        """
        if kwargs.get('id'):
            return self.get_single_item(request, *args, **kwargs)
        else:
            return self.get_collection(request, *args, **kwargs)

    def get_single_item(self, request, *args, **kwargs):
        """
        Handle a GET request for a single model instance.
        """
        try:
            qs = self.model.objects.filter(id=kwargs['id'])
            assert len(qs) == 1
        except AssertionError:
            raise Http404
        output = self.serialize_qs(qs)
        return self.build_response(output)

    def get_collection(self, request, *args, **kwargs):
        """
        Handle a GET request for a full collection (when no id was provided).
        """
        qs = self.model.objects.all()
        output = self.serialize_qs(qs)
        return self.build_response(output)

    def post(self, request, *args, **kwargs):
        pass

    def put(self, request, *args, **kwargs):
        pass

    def delete(self, request, *args, **kwargs):
        pass

    def serialize_qs(self, queryset):
        """
        Serialize a queryset into a JSON object that can be consumed by backbone.js.
        """
        values = queryset.values(*self.serialize_fields)
        if self.kwargs.get('id'):
            # For single-item requests, convert ValuesQueryset to a dict simply
            # by slicing the first item:
            json_output = json.dumps(values[0], default=BackboneView.date_serializer)
        else:
            json_output = json.dumps(list(values), default=BackboneView.date_serializer)
        return json_output

    def build_response(self, output):
        """
        Convert json to an HttpResponse object, with the correct mimetype
        """
        return HttpResponse(output, mimetype='application/json')


    @staticmethod
    def date_serializer(obj):
        """
        Convert datetime objects to ISO-compatible strings during json serialization.
        """
        return obj.isoformat() if isinstance(obj, datetime.datetime) else None
