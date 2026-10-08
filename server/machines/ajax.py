from django.contrib.auth.mixins import PermissionRequiredMixin
from django.db.models import Q
from django.shortcuts import get_object_or_404, render
from django.views import View

from .models import Machine

AUTOCOMPLETE_RESULT_LIMIT = 20


def get_machines(request, term):
    if not term:
        return Machine.objects.none()
    return Machine.objects.filter(Q(name__icontains=term) | Q(hostname__icontains=term))


class QualifyableMachineAutocompleteView(PermissionRequiredMixin, View):
    """Search partial backing the multi-select "qualify person for
    machine(s)" flow - renders matching, qualifiable, not-already-selected
    machines as clickable rows for htmx to swap into the results list."""

    permission_required = "machines.view_machine"

    def get(self, request, person=None):
        machines = get_machines(request, request.GET.get("term", None))
        machines = machines.filter(
            needs_qualification=True, state=Machine.MachineStatus.ACTIVE
        ).exclude(type=Machine.MachineType.LOCK_GROUP)
        machines = machines.exclude(qualified_people__person__id=person)
        machines = machines.exclude(pk__in=request.GET.getlist("machine_ids"))
        machines = machines[:AUTOCOMPLETE_RESULT_LIMIT]
        return render(
            request,
            "qualifyable_machine_results.html",
            {"machines": machines},
        )


class MachineInstructorOptionsView(PermissionRequiredMixin, View):
    """`<option>` list of one machine's instructors - used to dynamically
    scope the "Instructed By" field while qualifying a person for machines,
    only while exactly one machine is currently selected."""

    permission_required = "machines.view_machine"

    def get(self, request, pk):
        machine = get_object_or_404(Machine, pk=pk)
        instructors = machine.instructors.select_related("person").order_by(
            "person__name"
        )
        return render(
            request,
            "instructor_options.html",
            {"instructors": instructors},
        )
