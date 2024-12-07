from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.conf import settings
import json

from .models import SpaceState

channel_layer = get_channel_layer()

state_reporters = []

if hasattr(settings, "SPACE_REPORTERS"):
    for reporter_conf in settings.SPACE_REPORTERS:
        reporter_path = reporter_conf["TYPE"].split(".")
        module = ".".join(reporter_path[:-1])
        reporter_class_name = reporter_path[-1]
        reporter = getattr(__import__(module, fromlist=[reporter_class_name]), reporter_class_name)
        settings = reporter_conf.get("SETTINGS", {})
        state_reporters.append(reporter(settings))

def get_current_space_state():    
    current_state = SpaceState.objects.first()
    if current_state is None:
        return SpaceState(is_open=False)
    return current_state

async def aget_current_space_state():    
    current_state = await SpaceState.objects.afirst()
    if current_state is None:
        return SpaceState(is_open=False)
    return current_state
        
def parse_state(new_state):
    new_state = str(new_state).lower()
    if new_state == "1" or new_state == "true" or new_state == "open":
        new_state = True
    elif new_state == "0" or new_state == "false" or new_state == "closed":
        new_state = False
    return new_state
        
def update_space_state(new_state):
    current_state = get_current_space_state()
    new_state = parse_state(new_state)
    if new_state == current_state.is_open:
        return current_state
    state = SpaceState.objects.create(is_open=new_state)
    if channel_layer is not None:
        async_to_sync(channel_layer.group_send)("space_state", {"type": "space_state", "state": new_state})
    for reporter in state_reporters:
        reporter.report(state)
    return state
    
async def aupdate_space_state(new_state):
    current_state = await aget_current_space_state()
    new_state = parse_state(new_state)
    if new_state == current_state.is_open:
        return current_state
    state = await SpaceState.objects.acreate(is_open=new_state)
    if channel_layer is not None:
        await channel_layer.group_send("space_state", {"type": "space_state", "state": state.is_open})
    for reporter in state_reporters:
        reporter.report(state)
    return state