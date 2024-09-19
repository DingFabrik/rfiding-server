from .models import SpaceState

def space_state_processor(request):
    state = None
    if request.user.is_authenticated:
        state = SpaceState.objects.first()
    return { "space_state": state }