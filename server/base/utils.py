def get_int_list(querydict, key):
    """Return the integer values of `key` from a GET/POST QueryDict.

    Anything that is not a plain non-negative integer is dropped, so tampered
    or empty values (`?ids=`, `?ids=abc`) never reach a `pk__in` lookup, where
    they would raise a ValueError.
    """
    return [int(value) for value in querydict.getlist(key) if value.isdigit()]
