"""Système visuel partagé de l'application.

Couleurs, typographie et petits utilitaires de rendu (image de couverture
arrondie, image de remplacement) utilisés par toutes les vues. Centralisé
ici pour que les écrans restent visuellement cohérents sans dupliquer des
valeurs de style un peu partout.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QLinearGradient, QPainter, QPainterPath, QPixmap

PAPER = "#F6F1EA"
SURFACE = "#FCFAF7"
SURFACE_SUNKEN = "#EFE6D6"
INK = "#232C1E"
INK_SOFT = "#5C6653"
INK_FAINT = "#97A08A"
ACCENT = "#C6491F"
ACCENT_HOVER = "#AC3D18"
ACCENT_TINT = "#F6DDCF"
ACCENT_DEEP = "#8A3417"
LINE = "#E4DCCF"
DANGER_TEXT = "#9A5142"
DANGER_TINT = "#F7E7E1"

FONT_DISPLAY = '"Georgia", "Times New Roman", serif'
FONT_BODY = '"Segoe UI", "Helvetica Neue", Arial, sans-serif'

# Une couleur par catégorie suggérée : le badge porte l'information, pas
# la photo de couverture (qui reste la vraie image extraite de la vidéo).
CATEGORY_COLORS: dict[str, tuple[str, str]] = {
    "Entrée": ("#E4EBDA", "#4B6142"),
    "Plat": ("#FBE3D8", "#B34A26"),
    "Dessert": ("#F6E8C9", "#7C5710"),
    "Apéritif": ("#EFDDE6", "#7A3A5C"),
    "Accompagnement": ("#EAD9CB", "#7A4E32"),
    "Boisson": ("#DCE8E6", "#3C6864"),
}
DEFAULT_CATEGORY_COLOR = ("#EDE7DC", INK_SOFT)


def category_colors(category: str | None) -> tuple[str, str]:
    if not category:
        return DEFAULT_CATEGORY_COLOR
    return CATEGORY_COLORS.get(category, DEFAULT_CATEGORY_COLOR)


def build_stylesheet() -> str:
    return f"""
    QWidget {{
        color: {INK};
        font-family: {FONT_BODY};
        font-size: 13px;
    }}
    QMainWindow {{ background: {PAPER}; }}

    QScrollArea {{ border: none; background: transparent; }}
    QScrollArea > QWidget > QWidget {{ background: transparent; }}

    QLabel[role="wordmark"] {{
        font-family: {FONT_DISPLAY};
        font-style: italic;
        font-weight: 700;
        font-size: 22px;
        color: {INK};
    }}
    QLabel[role="tagline"] {{
        color: {INK_SOFT};
        font-size: 12px;
    }}
    QLabel[role="title"] {{
        font-family: {FONT_DISPLAY};
        font-weight: 700;
        font-size: 17px;
        color: {INK};
    }}
    QLabel[role="detail-title"] {{
        font-family: {FONT_DISPLAY};
        font-weight: 700;
        font-size: 26px;
        color: {INK};
    }}
    QLabel[role="section-label"] {{
        font-weight: 700;
        font-size: 11px;
        letter-spacing: 1px;
        color: {INK_SOFT};
        text-transform: uppercase;
    }}
    QLabel[role="muted"] {{ color: {INK_SOFT}; }}
    QLabel[role="faint"] {{ color: {INK_SOFT}; font-size: 12px; }}

    QPushButton {{
        border-radius: 10px;
        padding: 9px 16px;
        font-weight: 600;
        font-size: 12.5px;
        border: 1px solid transparent;
    }}
    QPushButton[variant="primary"] {{
        background: {ACCENT};
        color: {SURFACE};
    }}
    QPushButton[variant="primary"]:hover {{ background: {ACCENT_HOVER}; }}
    QPushButton[variant="secondary"] {{
        background: {SURFACE};
        color: {INK};
        border: 1px solid {LINE};
    }}
    QPushButton[variant="secondary"]:hover {{ background: {SURFACE_SUNKEN}; }}
    QPushButton[variant="ghost"] {{
        background: transparent;
        color: {INK_SOFT};
        border: none;
        padding: 8px 4px;
    }}
    QPushButton[variant="ghost"]:hover {{ color: {INK}; }}
    QPushButton[variant="danger-ghost"] {{
        background: transparent;
        color: {DANGER_TEXT};
        border: none;
    }}
    QPushButton[variant="danger-ghost"]:hover {{ background: {DANGER_TINT}; border-radius: 8px; }}

    QPushButton[variant="pill"] {{
        background: transparent;
        color: {INK_SOFT};
        border: 1px solid {LINE};
        border-radius: 14px;
        padding: 7px 15px;
        font-size: 12px;
    }}
    QPushButton[variant="pill"]:checked {{
        background: {INK};
        color: {SURFACE};
        border-color: {INK};
    }}

    QLineEdit, QPlainTextEdit, QComboBox, QTableWidget {{
        background: {SURFACE};
        border: 1px solid {LINE};
        border-radius: 9px;
        padding: 7px 10px;
        selection-background-color: {ACCENT_TINT};
    }}
    QLineEdit:focus, QPlainTextEdit:focus, QComboBox:focus {{
        border: 1px solid {ACCENT};
    }}
    QTableWidget {{ gridline-color: {LINE}; }}
    QHeaderView::section {{
        background: {SURFACE_SUNKEN};
        color: {INK_SOFT};
        border: none;
        padding: 6px;
        font-weight: 600;
    }}

    QGroupBox {{
        border: 1px solid {LINE};
        border-radius: 12px;
        margin-top: 14px;
        padding: 16px 14px 14px;
        font-weight: 600;
        color: {INK_SOFT};
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 6px;
        color: {INK_SOFT};
    }}

    QFrame[role="card"] {{
        background: {SURFACE};
        border-radius: 16px;
        border: 1px solid {LINE};
    }}
    QFrame[role="notes"] {{
        background: {SURFACE};
        border-radius: 14px;
        border: 1px solid {LINE};
    }}
    QLabel[role="notes-text"] {{
        font-family: {FONT_DISPLAY};
        font-style: italic;
        font-size: 14px;
    }}
    """


def rounded_pixmap(
    pixmap: QPixmap,
    size: QSize,
    radius: int = 16,
    round_top: bool = True,
    round_bottom: bool = True,
) -> QPixmap:
    """Recadre `pixmap` en 'cover' sur `size` puis arrondit les coins
    demandés — utilisé pour les vignettes de recette et l'image héro."""

    scaled = pixmap.scaled(size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
    x = max(0, (scaled.width() - size.width()) // 2)
    y = max(0, (scaled.height() - size.height()) // 2)
    cropped = scaled.copy(x, y, size.width(), size.height())

    result = QPixmap(size)
    result.fill(Qt.transparent)
    painter = QPainter(result)
    painter.setRenderHint(QPainter.Antialiasing)

    rect = QRectF(0, 0, size.width(), size.height())
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    if not round_top:
        path = path.united(_half_rect_path(rect, top=True))
    if not round_bottom:
        path = path.united(_half_rect_path(rect, top=False))

    painter.setClipPath(path)
    painter.drawPixmap(0, 0, cropped)
    painter.end()
    return result


def placeholder_cover(size: QSize, radius: int = 16, round_top: bool = True, round_bottom: bool = True) -> QPixmap:
    """Vignette de remplacement (dégradé + silhouette d'assiette) tant
    qu'aucune image de couverture n'a été extraite pour la recette."""

    result = QPixmap(size)
    result.fill(Qt.transparent)
    painter = QPainter(result)
    painter.setRenderHint(QPainter.Antialiasing)

    rect = QRectF(0, 0, size.width(), size.height())
    path = QPainterPath()
    path.addRoundedRect(rect, radius, radius)
    if not round_top:
        path = path.united(_half_rect_path(rect, top=True))
    if not round_bottom:
        path = path.united(_half_rect_path(rect, top=False))
    painter.setClipPath(path)

    gradient = QLinearGradient(0, 0, size.width(), size.height())
    gradient.setColorAt(0, QColor(SURFACE))
    gradient.setColorAt(1, QColor(SURFACE_SUNKEN))
    painter.fillRect(rect, gradient)

    cx, cy = size.width() / 2, size.height() / 2 + 4
    outer_r = min(size.width(), size.height()) * 0.19
    pen_color = QColor(INK_FAINT)
    pen_color.setAlphaF(0.75)
    painter.setPen(pen_color)
    painter.setBrush(Qt.NoBrush)
    painter.drawEllipse(QRectF(cx - outer_r, cy - outer_r, outer_r * 2, outer_r * 2))
    inner_r = outer_r * 0.62
    painter.drawEllipse(QRectF(cx - inner_r, cy - inner_r, inner_r * 2, inner_r * 2))

    painter.end()
    return result


def _half_rect_path(rect: QRectF, top: bool) -> QPainterPath:
    path = QPainterPath()
    half_h = rect.height() / 2
    if top:
        path.addRect(QRectF(rect.left(), rect.top(), rect.width(), half_h))
    else:
        path.addRect(QRectF(rect.left(), rect.top() + half_h, rect.width(), half_h))
    return path
