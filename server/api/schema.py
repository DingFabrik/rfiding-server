ADMIN_API_PREFIX = "/api/rest/"


def only_admin_api(endpoints, **kwargs):
    """drf-spectacular preprocessing hook: the schema documents the admin REST API
    only, not the machine and space status APIs under /api/ that devices use."""
    return [endpoint for endpoint in endpoints if endpoint[0].startswith(ADMIN_API_PREFIX)]
