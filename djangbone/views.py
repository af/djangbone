import datetime
import json

from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse, Http404
from django.views.generic import View


class DjangboneJSONEncoder(json.JSONEncoder):
    """
    JSON encoder that converts additional Python types to JSON.

    Currently only datetime.datetime instances are supported.
    """
    def default(self, obj):
        """
        Convert datetime objects to ISO-compatible strings during json serialization.
        """
        return obj.isoformat() if isinstance(obj, datetime.datetime) else None


class BackboneAPIView(View):
    """
    Abstract class view, which makes it easy for subclasses to talk to backbone.js.

    Supported operations (copied from backbone.js docs):
        create -> POST   /collection
        read ->   GET    /collection[/id]
        update -> PUT    /collection/id
        delete -> DELETE /collection/id
    """
    base_queryset = None        # Queryset to use for all data accesses, eg. User.objects.all()
    serialize_fields = tuple()  # Tuple of field names that should appear in json output

    # Optional pagination settings:
    page_size = None            # Set to an integer to enable GET pagination (at the specified page size)
    page_param_name = 'p'       # HTTP GET parameter to use for accessing pages (eg. /widgets?p=2)

    # Override these attributes with ModelForm instances to support PUT and POST requests:
    add_form_class = None       # Form class to be used for POST requests
    edit_form_class = None      # Form class to be used for PUT requests

    # Override these if you have custom JSON encoding/decoding needs:
    json_encoder = DjangboneJSONEncoder()
    json_decoder = json.JSONDecoder()

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
            qs = self.base_queryset.filter(id=kwargs['id'])
            assert len(qs) == 1
        except AssertionError:
            raise Http404
        output = self.serialize_qs(qs)
        return self.success_response(output)

    def get_collection(self, request, *args, **kwargs):
        """
        Handle a GET request for a full collection (when no id was provided).
        """
        qs = self.base_queryset
        output = self.serialize_qs(qs)
        return self.success_response(output)

    def post(self, request, *args, **kwargs):
        """
        Handle a POST request by adding a new model instance.

        This view will only do something if BackboneAPIView.add_form_class is specified
        by the subclass. This should be a ModelForm corresponding to the model used by
        base_queryset.

        Backbone.js will send the new object's attributes as json in the request body,
        so use our json decoder on it, rather than looking at request.POST.
        """
        if self.add_form_class == None:
            return HttpResponse('POST not supported', status=405)
        try:
            request_dict = self.json_decoder.decode(request.raw_post_data)
        except ValueError:
            return HttpResponse('Invalid POST JSON', status=400)
        form = self.add_form_class(request_dict)
        if hasattr(form, 'set_request'):
            form.set_request(request)
        if form.is_valid():
            new_object = form.save()
            # Serialize the new object to json using our built-in methods.
            # The extra DB read here is not ideal, but it keeps the code DRY:
            wrapper_qs = self.base_queryset.filter(id=new_object.id)
            return self.success_response(self.serialize_qs(wrapper_qs, single_object=True))
        else:
            return self.validation_error_response(form.errors)

    def put(self, request, *args, **kwargs):
        """
        Handle a PUT request by editing an existing model.

        This view will only do something if BackboneAPIView.edit_form_class is specified
        by the subclass. This should be a ModelForm corresponding to the model used by
        base_queryset.
        """
        if self.edit_form_class == None or not kwargs.has_key('id'):
            return HttpResponse('PUT not supported', status=405)
        try:
            # Just like with POST requests, Backbone will send the object's data as json:
            request_dict = self.json_decoder.decode(request.raw_post_data)
            instance = self.base_queryset.get(id=kwargs['id'])
        except ValueError:
            return HttpResponse('Invalid PUT JSON', status=400)
        except ObjectDoesNotExist:
            raise Http404
        form = self.edit_form_class(request_dict, instance=instance)
        if hasattr(form, 'set_request'):
            form.set_request(request)
        if form.is_valid():
            item = form.save()
            wrapper_qs = self.base_queryset.filter(id=item.id)
            return self.success_response(self.serialize_qs(wrapper_qs, single_object=True))
        else:
            return self.validation_error_response(form.errors)

    def delete(self, request, *args, **kwargs):
        """
        Respond to DELETE requests by deleting the model and returning its JSON representation.
        """
        if not kwargs.has_key('id'):
            return HttpResponse('DELETE is not supported for collections', status=405)
        qs = self.base_queryset.filter(id=kwargs['id'])
        if qs:
            output = self.serialize_qs(qs)
            qs.delete()
            return self.success_response(output)
        else:
            raise Http404

    def serialize_qs(self, queryset, single_object=False):
        """
        Serialize a queryset into a JSON object that can be consumed by backbone.js.

        If the single_object argument is True, or the url specified an id, return a
        single JSON object, otherwise return a JSON array of objects.
        """
        values = queryset.values(*self.serialize_fields)
        if single_object or self.kwargs.get('id'):
            # For single-item requests, convert ValuesQueryset to a dict simply
            # by slicing the first item:
            json_output = self.json_encoder.encode(values[0])
        else:
            values = queryset.values(*self.serialize_fields)
            # Process pagination options if they are enabled:
            if isinstance(self.page_size, int):
                try:
                    page_number = int(self.request.GET.get(self.page_param_name, 1))
                    offset = (page_number - 1) * self.page_size
                except ValueError:
                    offset = 0
                values = values[offset:offset+self.page_size]
            json_output = self.json_encoder.encode(list(values))
        return json_output

    def success_response(self, output):
        """
        Convert json output to an HttpResponse object, with the correct mimetype.
        """
        return HttpResponse(output, mimetype='application/json')

    def validation_error_response(self, form_errors):
        """
        Return an HttpResponse indicating that input validation failed.

        The form_errors argument contains the contents of form.errors, and you
        can override this method is you want to use a specific error response format.
        By default, the output is a simple text response.
        """
        return HttpResponse('ERROR: validation failed')
