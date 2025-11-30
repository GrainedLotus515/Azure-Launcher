"""Catppuccin color palette definitions."""

from dataclasses import dataclass


@dataclass(frozen=True)
class CatppuccinMocha:
    """Catppuccin Mocha color palette.

    A warm, dark theme with excellent contrast and accessibility.
    https://github.com/catppuccin/catppuccin
    """

    # Base colors
    rosewater: str = "#f5e0dc"
    flamingo: str = "#f2cdcd"
    pink: str = "#f5c2e7"
    mauve: str = "#cba6f7"
    red: str = "#f38ba8"
    maroon: str = "#eba0ac"
    peach: str = "#fab387"
    yellow: str = "#f9e2af"
    green: str = "#a6e3a1"
    teal: str = "#94e2d5"
    sky: str = "#89dceb"
    sapphire: str = "#74c7ec"
    blue: str = "#89b4fa"
    lavender: str = "#b4befe"

    # Text colors
    text: str = "#cdd6f4"
    subtext1: str = "#bac2de"
    subtext0: str = "#a6adc8"

    # Overlay colors
    overlay2: str = "#9399b2"
    overlay1: str = "#7f849c"
    overlay0: str = "#6c7086"

    # Surface colors
    surface2: str = "#585b70"
    surface1: str = "#45475a"
    surface0: str = "#313244"

    # Base backgrounds
    base: str = "#1e1e2e"
    mantle: str = "#181825"
    crust: str = "#11111b"
