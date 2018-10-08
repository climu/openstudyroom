from django.utils import timezone
from django.utils.deprecation import MiddlewareMixin
import pytz


class TimezoneMiddleware(MiddlewareMixin):

    def process_request(self, request):
        user = request.user
        if user.is_authenticated and hasattr(user, 'profile') and user.profile.timezone is not None:
            if user.profile.timezone == '---------':
                timezone.activate(pytz.timezone('UTC'))
            else:
                timezone.activate(pytz.timezone(user.profile.timezone))
        else:
            timezone.deactivate()
