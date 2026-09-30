"""Dialogue pour renommer une catégorie existante — appliqué à toutes les
recettes qui l'utilisent (ex. corriger « Plat » en « Plats »)."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)


class RenameCategoryDialog(QDialog):
    def __init__(self, categories: list[str], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Renommer une catégorie")
        self.setMinimumWidth(360)

        self._category_combo = QComboBox()
        self._category_combo.addItems(categories)
        self._category_combo.currentTextChanged.connect(self._new_name_edit_set_text)

        self._new_name_edit = QLineEdit()

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.addWidget(QLabel("Catégorie à renommer"))
        layout.addWidget(self._category_combo)
        layout.addWidget(QLabel("Nouveau nom"))
        layout.addWidget(self._new_name_edit)
        layout.addWidget(buttons)

        if categories:
            self._new_name_edit.setText(categories[0])

    def _new_name_edit_set_text(self, text: str) -> None:
        self._new_name_edit.setText(text)

    def selected_category(self) -> str:
        return self._category_combo.currentText()

    def new_name(self) -> str:
        return self._new_name_edit.text().strip()
