def toggle_active(obj):
    """Flip `is_active` on any model instance that has the field and persist it."""
    obj.is_active = not obj.is_active
    obj.save()
    return obj
