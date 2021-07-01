import pytz

from django.utils import timezone
from database_course import settings


class TimezoneMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        tzname = settings.CLASS_TIMEZONE
        if tzname:
            timezone.activate(pytz.timezone(tzname))
        else:
            timezone.deactivate()

        return self.get_response(request)
