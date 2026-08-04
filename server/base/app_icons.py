APP_ICONS = {
    "tokens": "radio-tower",
    "people": "users",
    "machines": "hard-drive",
    "access_log": "list",
    "users": "id-card",
    "groups": "users",
    "holidays": "calendar-days",
    "locations": "map-pin",
}

DEFAULT_ICON = "circle"


def app_icon(app_name):
    return APP_ICONS.get(app_name, DEFAULT_ICON)
