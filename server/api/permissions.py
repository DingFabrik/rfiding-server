from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import SAFE_METHODS, BasePermission, DjangoModelPermissions


class DjangoModelPermissionsWithView(DjangoModelPermissions):
    """DjangoModelPermissions, but GET also requires the `view_<model>` permission.

    DRF's stock DjangoModelPermissions leaves GET/HEAD/OPTIONS unrestricted;
    the dashboard's `PermissionRequiredMixin` views all require
    `<app>.view_<model>` to read, so the API default should match.
    """

    perms_map = {
        "GET": ["%(app_label)s.view_%(model_name)s"],
        "OPTIONS": [],
        "HEAD": ["%(app_label)s.view_%(model_name)s"],
        "POST": ["%(app_label)s.add_%(model_name)s"],
        "PUT": ["%(app_label)s.change_%(model_name)s"],
        "PATCH": ["%(app_label)s.change_%(model_name)s"],
        "DELETE": ["%(app_label)s.delete_%(model_name)s"],
    }


def check_perm(request, perm):
    """Raise PermissionDenied unless `request.user` has `perm` (e.g. "people.qualify_person").

    Mirrors the `permission_required` used by the equivalent Django dashboard view.
    """
    if not request.user.has_perm(perm):
        raise PermissionDenied(f"Missing permission: {perm}")


class ActionPermission(BasePermission):
    """DRF permission class checking one Django permission for reads, another for writes.

    Set `read_perm`/`write_perm` on a subclass - mirrors the single
    `permission_required` string dashboard views use, for resources (like
    Qualification) where the dashboard's custom permission doesn't match the
    default `DjangoModelPermissions` add/change/delete perms.
    """

    read_perm = None
    write_perm = None

    def has_permission(self, request, view):
        perm = self.read_perm if request.method in SAFE_METHODS else self.write_perm
        return perm is None or request.user.has_perm(perm)
