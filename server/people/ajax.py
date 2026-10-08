from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Q
from django.shortcuts import render
from django.views import View

from base.utils import get_int_list

from .models import Person

AUTOCOMPLETE_RESULT_LIMIT = 20


def get_people(request, term):
    if not term:
        return Person.objects.none()
    return Person.objects.filter(Q(name__icontains=term) | Q(email__icontains=term))


class PersonAutocompleteView(PermissionRequiredMixin, View):
    """Search partial backing the single-person picker on the token form -
    renders matching active people as clickable rows for htmx to swap in."""

    permission_required = "people.view_person"

    def get(self, request):
        people = get_people(request, request.GET.get("term", None))
        people = people.filter(is_active=True)[:AUTOCOMPLETE_RESULT_LIMIT]
        return render(
            request,
            "person_autocomplete_results.html",
            {"people": people, "term": request.GET.get("term", "")},
        )


class QualifyablePersonAutocompleteView(PermissionRequiredMixin, View):
    """Search partial backing the multi-select "qualify person(s) for a
    machine" flow - renders matching, not-yet-qualified, not-already-selected
    people as clickable rows for htmx to swap into the results list."""

    permission_required = "people.view_person"

    def get(self, request, machine=None):
        people = get_people(request, request.GET.get("term", None))
        people = people.filter(is_active=True)
        people = people.exclude(qualifications__machine__id=machine)
        people = people.exclude(pk__in=get_int_list(request.GET, "person_ids"))
        people = people[:AUTOCOMPLETE_RESULT_LIMIT]
        return render(
            request,
            "qualifyable_person_results.html",
            {"people": people},
        )
