

class Filter:
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

    def resolve(self, value):
        if self.mapping is not None:
            if value in self.mapping:
                return self.mapping[value]
            return self.mapping.get("default", {})
        if value == "all":
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
            value = self.data.get(self.param_name(name))
            if value is None:
                value = filter_.get_default(self.request)
            if value is None:
                continue
            kwargs = filter_.resolve(value)
            if kwargs:
                queryset = queryset.filter(**kwargs)
        return queryset

    def get_filter_choices(self):
        return {
            name: {"label": filter_.label, "options": filter_.get_options()}
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
                "schema": {"type": "string"},
            }
            for name, filter_ in filterset_class.declared_filters.items()
        ]
