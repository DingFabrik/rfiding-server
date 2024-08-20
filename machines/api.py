import datetime
from people.models import PERMISSION_LEVELS, Qualification
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from space.models import SpaceState

from .models import Machine
from tokens.models import Token
from access_log.models import AccessLog, LOG_TYPE_BOOTED, LOG_TYPE_ENABLED

def formatted_mac(mac_address):
    if mac_address is None:
        return None
    if not ":" in mac_address:
        return ":".join(mac_address[i:i+2] for i in range(0, len(mac_address), 2))
    return mac_address

class MachineConfigView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, format=None):
        mac_address = formatted_mac(request.GET.get('machine', None))

        if mac_address is None:
            return Response({"error": "Missing parameters"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            machine = Machine.objects.get(mac_address__iexact=mac_address)
        except Machine.DoesNotExist:
            return Response({"error": "Machine does not exist"}, status=status.HTTP_404_NOT_FOUND)
        
        if not machine.is_active or not machine.is_now_valid_time():
            return Response({"error": "Machine is restricted"}, status=status.HTTP_403_FORBIDDEN)
        
        log = AccessLog.objects.create(machine=machine, type=LOG_TYPE_BOOTED)
        log.save()
        return Response({"runTimer": machine.runtimer, "minPower": machine.min_power, "controlParameter": machine.control_parameter}, status=status.HTTP_200_OK)
        

class CheckMachineAccessView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, format=None):
        mac_address = formatted_mac(request.GET.get('machine', None))
        tokenID = request.GET.get('tokenUid', None)

        if mac_address is None or tokenID is None:
            return Response({"error": "Missing parameters", "access": 0}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            machine = Machine.objects.prefetch_related('times').get(mac_address__iexact=mac_address)
        except Machine.DoesNotExist:
            return Response({"error": "Machine does not exist", "access": 0}, status=status.HTTP_404_NOT_FOUND)
        
        if not machine.is_active or not machine.is_now_valid_time():
            return Response({"error": "Machine is restricted", "access": 0}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            token = Token.objects.select_related('person').get(serial__iexact=tokenID)
        except Token.DoesNotExist:
            return Response({"error": "Token does not exist", "access": 0}, status=status.HTTP_404_NOT_FOUND)
        
        if not token.is_active or not token.person.is_active:
            return Response({"error": "Token/Person is not active", "access": 0}, status=status.HTTP_403_FORBIDDEN)
        
        qualification = token.person.qualifications.filter(machine=machine).first()
        if qualification == None:
            return Response({"error": "Person does not have access to machine", "access": 0}, status=status.HTTP_403_FORBIDDEN)
        
        if qualification.permission_level == PERMISSION_LEVELS[0][0]:
            space_state = SpaceState.objects.first()
            if space_state != None and not space_state.is_open:
                return Response({"error": "Space is closed", "access": 0}, status=status.HTTP_403_FORBIDDEN)
        now = datetime.datetime.now()
        time = machine.times.filter(weekdays__contains=now.weekday()).filter(start_time__lte=now.time()).filter(end_time__gte=now.time()).first()
        AccessLog.objects.create(machine=machine, token=token, type=LOG_TYPE_ENABLED)
        return Response({"access": 1, "workingtime": (datetime.datetime.combine(datetime.now(), time.end_time) - now).total_seconds()}, status=status.HTTP_200_OK)