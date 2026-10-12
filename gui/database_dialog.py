# -*- coding: utf-8 -*-
"""
Astrorust — Horoskop-Datenbank: Suchen, Gruppieren, Laden, Importieren/Exportieren.
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QComboBox, QPushButton, QLabel, QTableWidgetItem,
    QFileDialog, QMessageBox, QInputDialog, QAbstractItemView, QTextEdit,
)

import styles
from i18n import tr
from widgets import make_table


class DatabaseDialog(QDialog):
    # Profil, Ziel ("a" | "b" | "new_tab")
    loadRequested = pyqtSignal(dict, str)

    def __init__(self, store, parent=None):
        super().__init__(parent)
        self.store = store
        self.setWindowTitle(tr("Horoskop-Datenbank"))
        self.resize(900, 560)
        self.setStyleSheet(styles.DARK_STYLESHEET)

        lay = QVBoxLayout(self)
        row = QHBoxLayout()
        self.edit_search = QLineEdit()
        self.edit_search.setPlaceholderText(tr("Suchen: Name, Ort, Gruppe, Stichwort, Jahr…"))
        self.edit_search.textChanged.connect(self.refresh)
        row.addWidget(self.edit_search, 1)
        self.combo_group = QComboBox()
        self.combo_group.currentIndexChanged.connect(self.refresh)
        row.addWidget(self.combo_group)
        lay.addLayout(row)

        self.table = make_table(["Name", "Datum", "Zeit", "Ort", "Gruppe", "Stichwörter"], stretch_col=3)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.doubleClicked.connect(lambda: self._load("a"))
        self.table.itemSelectionChanged.connect(self._on_select)
        lay.addWidget(self.table, 1)

        self.notes = QTextEdit()
        self.notes.setPlaceholderText(tr("Notizen zum Profil (werden beim Verlassen des Feldes gespeichert)"))
        self.notes.setMaximumHeight(70)
        lay.addWidget(self.notes)

        row = QHBoxLayout()
        for label, slot in [(tr("In neuem Tab öffnen"), lambda: self._load("new_tab")), (tr("Als Person A laden"), lambda: self._load("a")),
                            (tr("Als Partner B laden"), lambda: self._load("b"))]:
            b = QPushButton(label)
            b.clicked.connect(slot)
            row.addWidget(b)
        row.addStretch()
        for label, slot in [(tr("Gruppe…"), self._set_group), (tr("Stichwörter…"), self._set_tags), (tr("Löschen"), self._delete)]:
            b = QPushButton(label)
            b.clicked.connect(slot)
            row.addWidget(b)
        lay.addLayout(row)

        row = QHBoxLayout()
        b = QPushButton(tr("Importieren…"))
        b.clicked.connect(self._import)
        row.addWidget(b)
        b = QPushButton(tr("Auswahl exportieren (JSON)…"))
        b.clicked.connect(lambda: self._export("json"))
        row.addWidget(b)
        b = QPushButton(tr("Auswahl exportieren (CSV)…"))
        b.clicked.connect(lambda: self._export("csv"))
        row.addWidget(b)
        b = QPushButton(tr("Auswahl exportieren (AAF)…"))
        b.clicked.connect(lambda: self._export("aaf"))
        row.addWidget(b)
        row.addStretch()
        self.lbl_count = QLabel("")
        self.lbl_count.setStyleSheet(f"color:{styles.TEXT_MUTED};")
        row.addWidget(self.lbl_count)
        b = QPushButton(tr("Schließen"))
        b.clicked.connect(self.accept)
        row.addWidget(b)
        lay.addLayout(row)

        self._current = []
        self._notes_target = None
        self.notes.installEventFilter(self)
        self.refresh()

    def eventFilter(self, obj, ev):
        from PyQt6.QtCore import QEvent
        if obj is self.notes and ev.type() == QEvent.Type.FocusOut:
            self._save_notes()
        return super().eventFilter(obj, ev)

    def refresh(self, *_):
        self._save_notes()
        self.table.blockSignals(True)
        current_group = self.combo_group.currentData()
        self.combo_group.blockSignals(True)
        self.combo_group.clear()
        self.combo_group.addItem(tr("Alle Gruppen"), "")
        for g in self.store.groups():
            self.combo_group.addItem(g, g)
        idx = self.combo_group.findData(current_group)
        self.combo_group.setCurrentIndex(max(0, idx))
        self.combo_group.blockSignals(False)

        self._current = sorted(self.store.search(self.edit_search.text(), self.combo_group.currentData() or ""),
                               key=lambda p: p.get("name", "").lower())
        self.table.setRowCount(len(self._current))
        for r, p in enumerate(self._current):
            vals = [p["name"], f"{p['year']:04d}-{p['month']:02d}-{p['day']:02d}", f"{p.get('hour', 12):02d}:{p.get('minute', 0):02d}",
                    p.get("location_name", ""), p.get("group", ""), ", ".join(p.get("tags", []))]
            for c, v in enumerate(vals):
                self.table.setItem(r, c, QTableWidgetItem(v))
        self.lbl_count.setText(f"{len(self._current)} / {len(self.store.profiles)}")
        self.notes.clear()
        self._notes_target = None
        self.table.blockSignals(False)

    def _selected(self) -> list[dict]:
        rows = sorted({i.row() for i in self.table.selectedIndexes()})
        return [self._current[r] for r in rows if r < len(self._current)]

    def _on_select(self):
        self._save_notes()
        sel = self._selected()
        self._notes_target = sel[0]["id"] if len(sel) == 1 else None
        self.notes.setPlainText(sel[0].get("notes", "") if len(sel) == 1 else "")

    def _save_notes(self):
        if self._notes_target:
            for p in self.store.profiles:
                if p["id"] == self._notes_target and p.get("notes", "") != self.notes.toPlainText():
                    p["notes"] = self.notes.toPlainText()
                    self.store.save()

    def _load(self, target):
        sel = self._selected()
        if not sel:
            return
        self._save_notes()
        self.loadRequested.emit(sel[0], target)
        if target != "new_tab":
            self.accept()

    def _set_group(self):
        sel = self._selected()
        if not sel:
            return
        text, ok = QInputDialog.getText(self, tr("Gruppe"), tr("Gruppenname:"), text=sel[0].get("group", ""))
        if ok:
            for p in sel:
                p["group"] = text.strip()
            self.store.save()
            self.refresh()

    def _set_tags(self):
        sel = self._selected()
        if not sel:
            return
        text, ok = QInputDialog.getText(self, tr("Stichwörter"), tr("Stichwörter (durch Komma getrennt):"), text=", ".join(sel[0].get("tags", [])))
        if ok:
            tags = [t.strip() for t in text.split(",") if t.strip()]
            for p in sel:
                p["tags"] = tags
            self.store.save()
            self.refresh()

    def _delete(self):
        sel = self._selected()
        if not sel:
            return
        names = ", ".join(p["name"] for p in sel[:5]) + ("…" if len(sel) > 5 else "")
        if QMessageBox.question(self, tr("Löschen"), f"{len(sel)} {tr('Profil(e) endgültig löschen?')}\n{names}") == QMessageBox.StandardButton.Yes:
            for p in sel:
                self.store.delete(p["id"])
            self.refresh()

    def _import(self):
        path, _ = QFileDialog.getOpenFileName(self, tr("Profile importieren"), "", "Profile (*.json *.csv *.aaf *.txt)")
        if not path:
            return
        try:
            n = self.store.import_file(path)
        except Exception as e:
            QMessageBox.critical(self, tr("Importfehler"), str(e))
            return
        QMessageBox.information(self, tr("Import"), f"{n} {tr('Profile importiert/aktualisiert.')}")
        self.refresh()

    def _export(self, kind):
        sel = self._selected() or self._current
        if not sel:
            return
        ext = kind
        path, _ = QFileDialog.getSaveFileName(self, tr("Profile exportieren"), f"astrorust-profile.{ext}", f"{ext.upper()} (*.{ext})")
        if not path:
            return
        try:
            getattr(self.store, "export_" + kind)(path, sel)
        except (OSError, ValueError) as e:
            QMessageBox.critical(self, tr("Exportfehler"), str(e))
