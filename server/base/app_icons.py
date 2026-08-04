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
    if not app_name:
        return DEFAULT_ICON
    for part in reversed(app_name.split(":")):
        if part in APP_ICONS:
            return APP_ICONS[part]
    return DEFAULT_ICON
