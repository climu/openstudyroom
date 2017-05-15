from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin
import pytz


class TimezoneMiddleware(MiddlewareMixin):

    def process_request(self, request):
        if request.user.is_authenticated() and request.user.profile.timezone is not None:
            timezone.activate(pytz.timezone(request.user.profile.timezone))
        else:
            timezone.deactivate()
