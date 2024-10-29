from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError, NotFound

from machines.models import Machine

def formatted_mac(mac_address):
    if mac_address is None:
        return None
    if ":" not in mac_address:
        return ":".join(
            mac_address[i : i + 2].lower() for i in range(0, len(mac_address), 2)
        )
    return mac_address


class BaseAPIView(APIView):
    required_get_parameters = None
    required_post_parameters = None
    required_delete_parameters = None


    def get_machine(self, mac_address):
        try:
            return Machine.objects.get(mac_address=mac_address, is_active=True)
        except Machine.DoesNotExist:
            raise NotFound("Machine does not exist") from None

    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        if request.method.lower() == "get" and self.required_get_parameters:
            for param in self.required_get_parameters:
                if request.GET.get(param, None) is None:
                    raise ValidationError(f"Missing parameter {param}")
        if request.method.lower() == "post" and self.required_post_parameters:
            for param in self.required_post_parameters:
                if request.POST.get(param, None) is None:
                    raise ValidationError(f"Missing parameter {param}")
        if request.method.lower() == "delete" and self.required_delete_parameters:
            for param in self.required_delete_parameters:
                if request.GET.get(param, None) is None:
                    raise ValidationError(f"Missing parameter {param}")
