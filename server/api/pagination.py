from rest_framework.pagination import PageNumberPagination


class PageLengthPagination(PageNumberPagination):
    """Mirrors `BaseListView.get_paginate_by`: page size follows the user's preference."""

    page_size_query_param = "page_size"
    max_page_size = 300

    def get_page_size(self, request):
        user = request.user
        if user and user.is_authenticated:
            return user.page_length
        return super().get_page_size(request) or 50
