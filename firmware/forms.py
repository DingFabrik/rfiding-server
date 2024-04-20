from django.forms import ModelForm

from .models import Firmware

class FirmwareForm(ModelForm):
    class Meta:
        model = Firmware
        fields = ['name', 'version', 'file']