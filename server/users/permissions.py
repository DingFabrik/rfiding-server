"""Guards against privilege escalation through user and group management.

Plain `change_rfidinguser` / `change_group` must not let someone take over a
more privileged account (by resetting its password or email) or grant
permissions they don't hold themselves. Shared by the dashboard views and the
REST API; raises Django's PermissionDenied, which both turn into a 403.
"""

from django.contrib.auth.models import Permission
from django.core.exceptions import PermissionDenied
from django.db.models import Q


def permission_names(permissions):
    """`app_label.codename` strings for an iterable/queryset of Permission objects."""
    return {f"{perm.content_type.app_label}.{perm.codename}" for perm in permissions}


def granted_permissions(user):
    """Every permission granted to `user`, directly or through groups.

    Unlike `get_all_permissions()`, this ignores `is_active`, so a deactivated
    account still counts as holding what it would regain on reactivation.
    """
    return permission_names(
        Permission.objects.filter(Q(user=user) | Q(group__user=user))
        .select_related("content_type")
        .distinct()
    )


def missing_permissions(user, perms):
    """The permissions in `perms` that `user` does not hold."""
    if user.is_superuser:
        return set()
    return set(perms) - user.get_all_permissions()


def check_within_own_permissions(user, perms):
    missing = missing_permissions(user, perms)
    if missing:
        raise PermissionDenied(
            "Cannot modify a user or group with permissions you don't have: "
            + ", ".join(sorted(missing))
        )


def check_can_modify_user(user, target):
    """Raise PermissionDenied unless `user` may edit/delete/reset `target`."""
    if (target.is_superuser or target.is_staff) and not user.is_superuser:
        raise PermissionDenied("Only superusers can modify superuser or staff accounts.")
    check_within_own_permissions(user, granted_permissions(target))


def check_can_modify_group(user, group):
    check_within_own_permissions(
        user, permission_names(group.permissions.select_related("content_type"))
    )
