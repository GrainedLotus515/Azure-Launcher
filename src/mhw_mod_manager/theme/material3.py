"""Material 3 design system implementation using Catppuccin colors."""

from dataclasses import dataclass

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

from .catppuccin import CatppuccinMocha


@dataclass(frozen=True)
class Material3Theme:
    """Material 3 semantic color roles mapped to Catppuccin Mocha."""

    # Primary colors
    primary: str = CatppuccinMocha.blue
    on_primary: str = CatppuccinMocha.crust
    primary_container: str = CatppuccinMocha.surface0
    on_primary_container: str = CatppuccinMocha.blue

    # Secondary colors
    secondary: str = CatppuccinMocha.mauve
    on_secondary: str = CatppuccinMocha.crust
    secondary_container: str = CatppuccinMocha.surface0
    on_secondary_container: str = CatppuccinMocha.mauve

    # Tertiary colors
    tertiary: str = CatppuccinMocha.teal
    on_tertiary: str = CatppuccinMocha.crust
    tertiary_container: str = CatppuccinMocha.surface0
    on_tertiary_container: str = CatppuccinMocha.teal

    # Error colors
    error: str = CatppuccinMocha.red
    on_error: str = CatppuccinMocha.crust
    error_container: str = CatppuccinMocha.surface0
    on_error_container: str = CatppuccinMocha.red

    # Success colors
    success: str = CatppuccinMocha.green
    on_success: str = CatppuccinMocha.crust
    success_container: str = CatppuccinMocha.surface0
    on_success_container: str = CatppuccinMocha.green

    # Warning colors
    warning: str = CatppuccinMocha.peach
    on_warning: str = CatppuccinMocha.crust
    warning_container: str = CatppuccinMocha.surface0
    on_warning_container: str = CatppuccinMocha.peach

    # Background colors
    background: str = CatppuccinMocha.base
    on_background: str = CatppuccinMocha.text

    # Surface colors
    surface: str = CatppuccinMocha.mantle
    on_surface: str = CatppuccinMocha.text
    surface_variant: str = CatppuccinMocha.surface0
    on_surface_variant: str = CatppuccinMocha.subtext1

    # Surface container colors (elevation)
    surface_container_lowest: str = CatppuccinMocha.crust
    surface_container_low: str = CatppuccinMocha.mantle
    surface_container: str = CatppuccinMocha.surface0
    surface_container_high: str = CatppuccinMocha.surface1
    surface_container_highest: str = CatppuccinMocha.surface2

    # Outline colors
    outline: str = CatppuccinMocha.overlay0
    outline_variant: str = CatppuccinMocha.surface2

    # Other
    shadow: str = CatppuccinMocha.crust
    scrim: str = CatppuccinMocha.crust
    inverse_surface: str = CatppuccinMocha.text
    inverse_on_surface: str = CatppuccinMocha.base
    inverse_primary: str = CatppuccinMocha.blue


def apply_palette(app: QApplication, theme: Material3Theme = Material3Theme()) -> None:
    """Apply Material 3 color palette to Qt application."""
    palette = QPalette()

    # Window and base
    palette.setColor(QPalette.ColorRole.Window, QColor(theme.background))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(theme.on_background))
    palette.setColor(QPalette.ColorRole.Base, QColor(theme.surface))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(theme.surface_variant))
    palette.setColor(QPalette.ColorRole.Text, QColor(theme.on_surface))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(theme.on_surface_variant))

    # Buttons
    palette.setColor(QPalette.ColorRole.Button, QColor(theme.primary_container))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(theme.on_primary_container))

    # Highlights
    palette.setColor(QPalette.ColorRole.Highlight, QColor(theme.primary))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(theme.on_primary))

    # Links
    palette.setColor(QPalette.ColorRole.Link, QColor(theme.primary))
    palette.setColor(QPalette.ColorRole.LinkVisited, QColor(theme.tertiary))

    # Tooltips
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(theme.surface_container_high))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(theme.on_surface))

    # Disabled states
    palette.setColor(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.WindowText,
        QColor(theme.on_surface_variant),
    )
    palette.setColor(
        QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(theme.on_surface_variant)
    )
    palette.setColor(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.ButtonText,
        QColor(theme.on_surface_variant),
    )

    app.setPalette(palette)


def get_stylesheet(theme: Material3Theme = Material3Theme()) -> str:
    """Generate Qt stylesheet with Material 3 design tokens."""
    return f"""
        /* Material 3 + Catppuccin Mocha Theme */

        QMainWindow {{
            background-color: {theme.background};
        }}

        QWidget {{
            color: {theme.on_background};
            background-color: {theme.background};
            font-size: 14px;
            font-family: "Segoe UI", "Roboto", "Noto Sans", sans-serif;
        }}

        /* Buttons - Material 3 filled style */
        QPushButton {{
            background-color: {theme.primary};
            color: {theme.on_primary};
            border: none;
            border-radius: 20px;
            padding: 10px 24px;
            font-weight: 500;
            min-height: 20px;
        }}

        QPushButton:hover {{
            background-color: {theme.primary};
            opacity: 0.9;
        }}

        QPushButton:pressed {{
            background-color: {theme.primary_container};
        }}

        QPushButton:disabled {{
            background-color: {theme.surface_container_highest};
            color: {theme.on_surface_variant};
        }}

        /* Outlined buttons */
        QPushButton[outlined="true"] {{
            background-color: transparent;
            color: {theme.primary};
            border: 1px solid {theme.outline};
        }}

        QPushButton[outlined="true"]:hover {{
            background-color: {theme.surface_container_highest};
        }}

        /* Small buttons for table actions */
        QPushButton[small="true"] {{
            padding: 4px 12px;
            border-radius: 14px;
            font-size: 12px;
            min-height: 16px;
        }}

        QPushButton[outlined="true"][small="true"] {{
            background-color: transparent;
            color: {theme.primary};
            border: 1px solid {theme.outline};
            padding: 4px 12px;
            border-radius: 14px;
        }}

        QPushButton[outlined="true"][small="true"]:hover {{
            background-color: {theme.surface_container_high};
            border-color: {theme.primary};
        }}

        /* Flat small buttons for profile actions */
        QPushButton[flat="true"][small="true"] {{
            background-color: transparent;
            color: {theme.primary};
            border: none;
            padding: 4px 12px;
            border-radius: 14px;
            font-size: 12px;
            min-height: 16px;
        }}

        QPushButton[flat="true"][small="true"]:hover {{
            background-color: {theme.surface_container_high};
        }}

        QPushButton[flat="true"][small="true"]:pressed {{
            background-color: {theme.surface_container_highest};
        }}

        QPushButton[flat="true"][small="true"]:disabled {{
            color: {theme.on_surface_variant};
        }}

        /* Text buttons */
        QPushButton[flat="true"] {{
            background-color: transparent;
            color: {theme.primary};
            border: none;
            padding: 10px 12px;
        }}

        QPushButton[flat="true"]:hover {{
            background-color: {theme.surface_container_highest};
        }}

        /* Line edits */
        QLineEdit {{
            background-color: {theme.surface_container_highest};
            color: {theme.on_surface};
            border: none;
            border-bottom: 1px solid {theme.outline_variant};
            border-radius: 4px 4px 0 0;
            padding: 12px 16px;
        }}

        QLineEdit:focus {{
            border-bottom: 2px solid {theme.primary};
        }}

        QLineEdit:disabled {{
            background-color: {theme.surface_container_low};
            color: {theme.on_surface_variant};
        }}

        /* Combo boxes */
        QComboBox {{
            background-color: {theme.surface_container_highest};
            color: {theme.on_surface};
            border: 1px solid {theme.outline};
            border-radius: 4px;
            padding: 8px 16px;
            min-height: 20px;
        }}

        QComboBox:hover {{
            background-color: {theme.surface_container_high};
        }}

        QComboBox:on {{
            border-color: {theme.primary};
        }}

        QComboBox::drop-down {{
            border: none;
            width: 30px;
        }}

        QComboBox::down-arrow {{
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 5px solid {theme.on_surface};
            margin-right: 8px;
        }}

        QComboBox QAbstractItemView {{
            background-color: {theme.surface_container_high};
            color: {theme.on_surface};
            border: 1px solid {theme.outline};
            border-radius: 4px;
            selection-background-color: {theme.primary_container};
            selection-color: {theme.on_primary_container};
            padding: 4px;
        }}

        /* List widgets */
        QListWidget {{
            background-color: {theme.surface};
            color: {theme.on_surface};
            border: 1px solid {theme.outline_variant};
            border-radius: 12px;
            padding: 4px;
        }}

        QListWidget::item {{
            background-color: transparent;
            border-radius: 8px;
            padding: 12px 16px;
            margin: 2px 4px;
        }}

        QListWidget::item:selected {{
            background-color: {theme.secondary_container};
            color: {theme.on_secondary_container};
        }}

        QListWidget::item:hover {{
            background-color: {theme.surface_container_highest};
        }}

        /* Table widgets */
        QTableWidget {{
            background-color: {theme.surface};
            color: {theme.on_surface};
            border: 1px solid {theme.outline_variant};
            border-radius: 12px;
            gridline-color: transparent;
            selection-background-color: {theme.secondary_container};
            selection-color: {theme.on_secondary_container};
            outline: none;
        }}

        QTableWidget::item {{
            padding: 8px 12px;
            border: none;
            border-bottom: 1px solid {theme.surface_container};
        }}

        QTableWidget::item:selected {{
            background-color: {theme.secondary_container};
            color: {theme.on_secondary_container};
        }}

        QTableWidget::item:hover {{
            background-color: {theme.surface_container_high};
        }}

        QHeaderView {{
            background-color: {theme.surface_container_high};
        }}

        QHeaderView::section {{
            background-color: {theme.surface_container_high};
            color: {theme.on_surface_variant};
            padding: 12px 12px;
            border: none;
            border-bottom: 1px solid {theme.outline_variant};
            font-weight: 500;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        QHeaderView::section:first {{
            border-top-left-radius: 12px;
        }}

        QHeaderView::section:last {{
            border-top-right-radius: 12px;
        }}

        QHeaderView::section:hover {{
            background-color: {theme.surface_container_highest};
        }}

        /* Table cell widgets (checkboxes, action buttons) */
        QWidget[tableCell="true"] {{
            background-color: transparent;
        }}

        /* Checkboxes in table cells */
        QTableWidget QCheckBox {{
            background-color: transparent;
        }}

        QTableWidget QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border: 2px solid {theme.outline};
            border-radius: 2px;
            background-color: transparent;
        }}

        QTableWidget QCheckBox::indicator:checked {{
            background-color: {theme.primary};
            border-color: {theme.primary};
        }}

        QTableWidget QCheckBox::indicator:hover {{
            border-color: {theme.primary};
        }}

        /* Buttons in table cells */
        QTableWidget QPushButton {{
            background-color: transparent;
            color: {theme.primary};
            border: 1px solid {theme.outline};
            border-radius: 14px;
            padding: 4px 12px;
            font-size: 12px;
            min-width: 60px;
        }}

        QTableWidget QPushButton:hover {{
            background-color: {theme.surface_container_high};
            border-color: {theme.primary};
        }}

        QTableWidget QPushButton:pressed {{
            background-color: {theme.surface_container_highest};
        }}

        /* Text edits */
        QTextEdit, QPlainTextEdit {{
            background-color: {theme.surface_container};
            color: {theme.on_surface};
            border: 1px solid {theme.outline_variant};
            border-radius: 8px;
            padding: 8px;
        }}

        /* Scroll bars */
        QScrollBar:vertical {{
            background-color: {theme.surface};
            width: 12px;
            border-radius: 6px;
            margin: 0;
        }}

        QScrollBar::handle:vertical {{
            background-color: {theme.outline};
            border-radius: 6px;
            min-height: 30px;
        }}

        QScrollBar::handle:vertical:hover {{
            background-color: {theme.outline_variant};
        }}

        QScrollBar:horizontal {{
            background-color: {theme.surface};
            height: 12px;
            border-radius: 6px;
            margin: 0;
        }}

        QScrollBar::handle:horizontal {{
            background-color: {theme.outline};
            border-radius: 6px;
            min-width: 30px;
        }}

        QScrollBar::handle:horizontal:hover {{
            background-color: {theme.outline_variant};
        }}

        QScrollBar::add-line, QScrollBar::sub-line {{
            height: 0;
            width: 0;
        }}

        /* Tab widget */
        QTabWidget::pane {{
            background-color: {theme.surface};
            border: 1px solid {theme.outline_variant};
            border-radius: 12px;
            top: -1px;
        }}

        QTabBar::tab {{
            background-color: transparent;
            color: {theme.on_surface_variant};
            border: none;
            border-bottom: 2px solid transparent;
            padding: 12px 24px;
            font-weight: 500;
        }}

        QTabBar::tab:selected {{
            color: {theme.primary};
            border-bottom: 2px solid {theme.primary};
        }}

        QTabBar::tab:hover {{
            background-color: {theme.surface_container_highest};
            color: {theme.on_surface};
        }}

        /* Checkboxes - Material 3 style */
        QCheckBox {{
            spacing: 8px;
            color: {theme.on_surface};
            background-color: transparent;
        }}

        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border: 2px solid {theme.outline};
            border-radius: 2px;
            background-color: transparent;
        }}

        QCheckBox::indicator:hover {{
            border-color: {theme.primary};
            background-color: rgba(137, 180, 250, 0.08);
        }}

        QCheckBox::indicator:checked {{
            background-color: {theme.primary};
            border-color: {theme.primary};
        }}

        QCheckBox::indicator:checked:hover {{
            background-color: {theme.primary};
            border-color: {theme.primary};
        }}

        QCheckBox::indicator:disabled {{
            border-color: {theme.outline_variant};
            background-color: {theme.surface_container_low};
        }}

        QCheckBox::indicator:checked:disabled {{
            background-color: {theme.outline_variant};
            border-color: {theme.outline_variant};
        }}

        /* Radio buttons */
        QRadioButton {{
            spacing: 8px;
            color: {theme.on_surface};
        }}

        QRadioButton::indicator {{
            width: 18px;
            height: 18px;
            border: 2px solid {theme.outline};
            border-radius: 9px;
            background-color: transparent;
        }}

        QRadioButton::indicator:hover {{
            border-color: {theme.primary};
        }}

        QRadioButton::indicator:checked {{
            background-color: {theme.primary};
            border-color: {theme.primary};
        }}

        /* Progress bar */
        QProgressBar {{
            background-color: {theme.surface_container_highest};
            border: none;
            border-radius: 8px;
            text-align: center;
            height: 8px;
        }}

        QProgressBar::chunk {{
            background-color: {theme.primary};
            border-radius: 8px;
        }}

        /* Menu bar */
        QMenuBar {{
            background-color: {theme.surface};
            color: {theme.on_surface};
            border-bottom: 1px solid {theme.outline_variant};
        }}

        QMenuBar::item {{
            padding: 8px 12px;
            background-color: transparent;
        }}

        QMenuBar::item:selected {{
            background-color: {theme.surface_container_highest};
        }}

        /* Menu */
        QMenu {{
            background-color: {theme.surface_container_high};
            color: {theme.on_surface};
            border: 1px solid {theme.outline};
            border-radius: 8px;
            padding: 4px;
        }}

        QMenu::item {{
            padding: 8px 32px 8px 16px;
            border-radius: 4px;
        }}

        QMenu::item:selected {{
            background-color: {theme.secondary_container};
            color: {theme.on_secondary_container};
        }}

        /* Dialogs */
        QDialog {{
            background-color: {theme.surface_container_high};
        }}

        /* Toolbar */
        QToolBar {{
            background-color: {theme.surface};
            border: none;
            border-bottom: 1px solid {theme.outline_variant};
            spacing: 12px;
            padding: 12px 16px;
        }}

        QToolBar::separator {{
            background-color: {theme.outline_variant};
            width: 1px;
            margin: 4px 8px;
        }}

        QToolButton {{
            background-color: transparent;
            color: {theme.on_surface};
            border: none;
            border-radius: 8px;
            padding: 8px;
        }}

        QToolButton:hover {{
            background-color: {theme.surface_container_highest};
        }}

        QToolButton:pressed {{
            background-color: {theme.surface_container_high};
        }}

        /* Status bar */
        QStatusBar {{
            background-color: {theme.surface};
            color: {theme.on_surface_variant};
            border-top: 1px solid {theme.outline_variant};
        }}

        /* Group box */
        QGroupBox {{
            background-color: {theme.surface_container};
            border: 1px solid {theme.outline_variant};
            border-radius: 12px;
            margin-top: 12px;
            padding-top: 12px;
            font-weight: 600;
        }}

        QGroupBox::title {{
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 16px;
            padding: 0 8px;
            background-color: {theme.surface_container};
            color: {theme.on_surface};
        }}

        /* Splitter */
        QSplitter::handle {{
            background-color: {theme.outline_variant};
        }}

        QSplitter::handle:horizontal {{
            width: 2px;
        }}

        QSplitter::handle:vertical {{
            height: 2px;
        }}

        /* Labels */
        QLabel {{
            color: {theme.on_surface};
            background-color: transparent;
        }}

        QLabel[heading="h1"] {{
            font-size: 32px;
            font-weight: 400;
        }}

        QLabel[heading="h2"] {{
            font-size: 24px;
            font-weight: 400;
        }}

        QLabel[heading="h3"] {{
            font-size: 20px;
            font-weight: 500;
        }}

        QLabel[secondary="true"] {{
            color: {theme.on_surface_variant};
        }}

        QLabel[heading="true"] {{
            font-size: 16px;
            font-weight: 600;
            color: {theme.on_surface};
        }}

        QLabel[title="true"] {{
            font-size: 24px;
            font-weight: 500;
            color: {theme.on_surface};
        }}

        /* Cards */
        QWidget[card="true"] {{
            background-color: {theme.surface_container};
            border: 1px solid {theme.outline_variant};
            border-radius: 12px;
            padding: 12px;
        }}

        QWidget[card="true"]:hover {{
            background-color: {theme.surface_container_high};
            border-color: {theme.outline};
        }}

        /* Scroll area styling */
        QScrollArea {{
            background-color: transparent;
            border: none;
        }}

        QScrollArea > QWidget > QWidget {{
            background-color: transparent;
        }}
    """
