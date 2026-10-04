

class Filter:
    multiple = False

    def __init__(self, field=None, *, lookup="exact", label=None, choices=None, mapping=None, default=None):
        self.field = field
        self.lookup = lookup
        self.label = label
        self.choices = choices
        self.mapping = mapping
        self.default = default
        self.name = None

    def get_options(self):
        choices = self.choices() if callable(self.choices) else self.choices
        return list(choices or [])

    def get_default(self, request):
        if callable(self.default):
            return self.default(request)
        return self.default

    def get_value(self, data, param_name, request):
        value = data.get(param_name)
        if value is None:
            value = self.get_default(request)
        return value

    def resolve(self, value):
        if self.mapping is not None:
            if value in self.mapping:
                return self.mapping[value]
            return self.mapping.get("default", {})
        if value == "all":
            return None
        field = self.field or self.name
        return {f"{field}__{self.lookup}": value}


class MultipleChoiceFilter(Filter):
    """Filter that accepts several values for the same parameter (e.g. checkboxes).

    As soon as the parameter is present the submitted values are used, so an
    empty value (as sent by a hidden input when nothing is checked) means
    "nothing selected" rather than falling back to the default.
    """

    multiple = True

    def __init__(self, field=None, *, lookup="in", **kwargs):
        super().__init__(field, lookup=lookup, **kwargs)

    def get_value(self, data, param_name, request):
        if param_name not in data:
            default = self.get_default(request)
            return None if default is None else list(default)
        values = []
        for value in data.getlist(param_name):
            values.extend(v for v in value.split(",") if v)
        return values

    def resolve(self, value):
        if "all" in value:
            return None
        field = self.field or self.name
        return {f"{field}__{self.lookup}": value}


class FilterSetMeta(type):
    def __new__(mcs, name, bases, namespace):
        declared_filters = {}
        for base in bases:
            declared_filters.update(getattr(base, "declared_filters", {}))
        for key, value in namespace.items():
            if isinstance(value, Filter):
                value.name = key
                declared_filters[key] = value
        cls = super().__new__(mcs, name, bases, namespace)
        cls.declared_filters = declared_filters
        return cls


class FilterSet(metaclass=FilterSetMeta):
    param_prefix = "filter_"

    def __init__(self, data, queryset, *, request=None):
        self.data = data
        self.queryset = queryset
        self.request = request

    def param_name(self, name):
        return f"{self.param_prefix}{name}"

    @property
    def qs(self):
        queryset = self.queryset
        for name, filter_ in self.declared_filters.items():
            value = filter_.get_value(self.data, self.param_name(name), self.request)
            if value is None:
                continue
            kwargs = filter_.resolve(value)
            if kwargs:
                queryset = queryset.filter(**kwargs)
        return queryset

    def get_filter_choices(self):
        return {
            name: {
                "label": filter_.label,
                "options": filter_.get_options(),
                "multiple": filter_.multiple,
                "value": filter_.get_value(
                    self.data, self.param_name(name), self.request
                ),
            }
            for name, filter_ in self.declared_filters.items()
        }

    def get_filter_defaults(self):
        return {
            name: filter_.get_default(self.request)
            for name, filter_ in self.declared_filters.items()
        }


class DRFFilterBackend:

    def filter_queryset(self, request, queryset, view):
        filterset_class = getattr(view, "filterset_class", None)
        # Only apply on the list action - like the dashboard's BaseListView, this
        # filters listings (including their default status filter); it must not
        # narrow single-object lookups (retrieve/update/destroy/detail actions),
        # or e.g. toggling a person inactive would make them unreachable afterwards.
        if filterset_class is None or getattr(view, "action", None) != "list":
            return queryset
        return filterset_class(request.query_params, queryset, request=request).qs

    def get_schema_operation_parameters(self, view):
        filterset_class = getattr(view, "filterset_class", None)
        if filterset_class is None:
            return []
        return [
            {
                "name": f"{filterset_class.param_prefix}{name}",
                "required": False,
                "in": "query",
                "description": str(filter_.label) if filter_.label else name,
                "schema": (
                    {"type": "array", "items": {"type": "string"}}
                    if filter_.multiple
                    else {"type": "string"}
                ),
            }
            for name, filter_ in filterset_class.declared_filters.items()
        ]
