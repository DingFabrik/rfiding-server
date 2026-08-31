from holidays.models import Holiday
from holidays.serializers import HolidaySerializer

from .base import BaseModelViewSet


class HolidayViewSet(BaseModelViewSet):
    queryset = Holiday.objects.all()
    serializer_class = HolidaySerializer
    search_fields = ["name"]
    ordering_fields = ["date", "name"]
