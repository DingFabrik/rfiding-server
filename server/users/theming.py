
THEME_COLOR_SLUGS = {
    "default": "blue",
    "purple": "purple",
    "red": "red",
    "orange": "orange",
    "yellow": "yellow",
    "green": "green",
    "pink": "pink",
    "teal": "teal",
    "cyan": "cyan",
}

THEME_ACCENT_COLORS = {
    "blue": ("#0d6efd", "#ffffff"),
    "purple": ("#6f42c1", "#ffffff"),
    "red": ("#dc3545", "#ffffff"),
    "orange": ("#fd7e14", "#212529"),
    "yellow": ("#ffc107", "#212529"),
    "green": ("#198754", "#ffffff"),
    "pink": ("#d63384", "#ffffff"),
    "teal": ("#20c997", "#ffffff"),
    "cyan": ("#0dcaf0", "#212529"),
}

THEME_MODE_BASE = {
    "light": {
        "base-100": "#ffffff",
        "base-200": "#f8f9fa",
        "base-300": "#e9ecef",
        "base-content": "#212529",
        "neutral": "#495057",
        "neutral-content": "#f8f9fa",
    },
    "dark": {
        "base-100": "#212529",
        "base-200": "#1a1d20",
        "base-300": "#16181a",
        "base-content": "#dee2e6",
        "neutral": "#343a40",
        "neutral-content": "#f8f9fa",
    },
}


def theme_color_slug(color):
    return THEME_COLOR_SLUGS.get(color, color)


def theme_name(color, mode):
    return f"{theme_color_slug(color)}-{mode}"


def theme_css_declarations(color, mode):
    slug = theme_color_slug(color)
    accent, accent_content = THEME_ACCENT_COLORS.get(slug, THEME_ACCENT_COLORS["blue"])
    base = THEME_MODE_BASE[mode]
    declarations = [f"color-scheme: {mode};"]
    for name, value in (
        ("base-100", base["base-100"]),
        ("base-200", base["base-200"]),
        ("base-300", base["base-300"]),
        ("base-content", base["base-content"]),
        ("neutral", base["neutral"]),
        ("neutral-content", base["neutral-content"]),
        ("primary", accent),
        ("primary-content", accent_content),
        ("accent", accent),
        ("accent-content", accent_content),
    ):
        declarations.append(f"--color-{name}: {value};")
    return declarations
