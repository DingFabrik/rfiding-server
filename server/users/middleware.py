from django.conf import settings
from django.utils import translation
from django.utils.cache import patch_vary_headers


class LanguageMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = request.user
        language = user.language if user.is_authenticated else None
        language = language or settings.LANGUAGE_CODE

        translation.activate(language)
        request.LANGUAGE_CODE = translation.get_language()
        try:
            response = self.get_response(request)
        finally:
            translation.deactivate()

        response.setdefault("Content-Language", language)
        patch_vary_headers(response, ("Accept-Language",))
        return response
