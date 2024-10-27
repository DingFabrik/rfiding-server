from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

from .models import SpaceState

channel_layer = get_channel_layer()

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
        
def update_space_state(new_state):
    new_state = str(new_state)
    current_state = get_current_space_state()
    if new_state == "1":
        new_state = True
    elif new_state == "0":
        new_state = False
    if new_state == current_state.is_open:
        return current_state
    state = SpaceState.objects.create(is_open=new_state)
    state.save()
    async_to_sync(channel_layer.group_send)("space_state", {"type": "space_state", "state": new_state})
    
async def aupdate_space_state(new_state):
    new_state = str(new_state)
    current_state = await aget_current_space_state()
    if new_state == "1":
        new_state = True
    elif new_state == "0":
        new_state = False
    if new_state == current_state.is_open:
        return current_state
    state = await SpaceState.objects.acreate(is_open=new_state)
    await channel_layer.group_send("space_state", {"type": "space_state", "state": state.is_open})