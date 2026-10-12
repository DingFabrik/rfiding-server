from .models import Comment


def comment_permission_for(content_object):
    """Permission string required to comment on `content_object` (e.g. "people.comment_person")."""
    meta = content_object._meta
    return f"{meta.app_label}.comment_{meta.model_name}"


def comments_for(content_object):
    """Comments on `content_object`, with their authors fetched in the same query."""
    return content_object.comments.select_related("author")


def create_comment(content_object, author, text):
    return Comment.objects.create(
        content_object=content_object, author=author, text=text
    )
