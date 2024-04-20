from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions

from .models import Machine, MachineConfig
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
            machine = Machine.objects.get(mac_address=mac_address)
        except Machine.DoesNotExist:
            return Response({"error": "Machine does not exist"}, status=status.HTTP_404_NOT_FOUND)
        
        if not machine.is_active or not machine.is_now_valid_time():
            return Response({"error": "Machine is restricted"}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            config = machine.config
            log = AccessLog.objects.create(machine=machine, type=LOG_TYPE_BOOTED)
            log.save()
            return Response({"runTimer": config.runtimer, "minPower": config.min_power, "controlParameter": config.control_parameter}, status=status.HTTP_200_OK)
        except MachineConfig.DoesNotExist:
            return Response({"runTimer": 0, "minPower": 0, "controlParameter": ""}, status=status.HTTP_200_OK)
        

class CheckMachineAccessView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, format=None):
        mac_address = formatted_mac(request.GET.get('machine', None))
        tokenID = request.GET.get('tokenUid', None)

        if mac_address is None or tokenID is None:
            return Response({"error": "Missing parameters", "access": 0}, status=status.HTTP_400_BAD_REQUEST)
        

        try:
            machine = Machine.objects.get(mac_address=mac_address)
        except Machine.DoesNotExist:
            return Response({"error": "Machine does not exist", "access": 0}, status=status.HTTP_404_NOT_FOUND)
        
        if not machine.is_active or not machine.is_now_valid_time():
            return Response({"error": "Machine is restricted", "access": 0}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            token = Token.objects.get(serial=tokenID)
        except Token.DoesNotExist:
            return Response({"error": "Token does not exist", "access": 0}, status=status.HTTP_404_NOT_FOUND)
        
        if not token.is_active or not token.user.is_active:
            return Response({"error": "Token/User is not active", "access": 0}, status=status.HTTP_403_FORBIDDEN)
        
        if not token.user.qualifications.filter(machine=machine).exists():
            return Response({"error": "User does not have access to machine", "access": 0}, status=status.HTTP_403_FORBIDDEN)
        
        log = AccessLog.objects.create(machine=machine, token=token, type=LOG_TYPE_ENABLED)
        log.save()
        return Response({"access": 1}, status=status.HTTP_200_OK)