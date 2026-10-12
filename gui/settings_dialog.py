# -*- coding: utf-8 -*-
"""
Astrorust — Einstellungsdialog: Berechnung (Knoten, Lilith, Asteroiden, Tierkreis), Aspekte/Orben, Allgemeines.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QComboBox, QCheckBox, QDoubleSpinBox,
    QPushButton, QTabWidget, QWidget, QGroupBox,
)

import styles
import copy
from appsettings import AppSettings, ASPECT_KEYS
from i18n import tr
from widgets import tab_text


class SettingsDialog(QDialog):
    def __init__(self, backend, settings: AppSettings, parent=None):
        super().__init__(parent)
        self.backend = backend
        self._target = settings
        self.settings = AppSettings(settings.data)
        self.setWindowTitle(tr("Einstellungen"))
        self.setMinimumWidth(560)
        self.setStyleSheet(styles.DARK_STYLESHEET)

        lay = QVBoxLayout(self)
        tabs = QTabWidget()
        tabs.addTab(self._tab_calc(), tr("Berechnung"))
        tabs.addTab(self._tab_aspects(), tab_text(tr("Aspekte & Orben")))
        tabs.addTab(self._tab_general(), tr("Allgemein"))
        lay.addWidget(tabs)

        row = QHBoxLayout()
        btn_reset = QPushButton(tr("Standard wiederherstellen"))
        btn_reset.clicked.connect(self._reset)
        row.addWidget(btn_reset)
        row.addStretch()
        btn_cancel = QPushButton(tr("Abbrechen"))
        btn_cancel.clicked.connect(self.reject)
        row.addWidget(btn_cancel)
        btn_ok = QPushButton(tr("Übernehmen"))
        btn_ok.setObjectName("btn_start")
        btn_ok.clicked.connect(self._apply)
        row.addWidget(btn_ok)
        lay.addLayout(row)

        self._load()

    # ── Tabs ──
    def _tab_calc(self):
        w = QWidget()
        g = QGridLayout(w)
        g.setSpacing(8)
        r = 0

        g.addWidget(QLabel(tr("Tierkreis:")), r, 0)
        self.combo_zodiac = QComboBox()
        self.combo_zodiac.addItem(tr("Tropisch (westlich)"), "Tropical")
        self.combo_zodiac.addItem(tr("Siderisch"), "Sidereal")
        g.addWidget(self.combo_zodiac, r, 1)
        r += 1

        g.addWidget(QLabel(tr("Ayanamsa:")), r, 0)
        self.combo_ayan = QComboBox()
        try:
            for a in self.backend.call("ayanamsas"):
                self.combo_ayan.addItem(a["name"], a["id"])
        except Exception:
            self.combo_ayan.addItem("Lahiri", 1)
        g.addWidget(self.combo_ayan, r, 1)
        self.combo_zodiac.currentIndexChanged.connect(
            lambda: self.combo_ayan.setEnabled(self.combo_zodiac.currentData() == "Sidereal"))
        r += 1

        g.addWidget(QLabel(tr("Mondknoten:")), r, 0)
        self.combo_node = QComboBox()
        self.combo_node.addItem(tr("Wahr (oskulierend)"), "True")
        self.combo_node.addItem(tr("Mittel"), "Mean")
        g.addWidget(self.combo_node, r, 1)
        r += 1

        g.addWidget(QLabel(tr("Lilith:")), r, 0)
        self.combo_lilith = QComboBox()
        self.combo_lilith.addItem(tr("Mittleres Apogäum"), "Mean")
        self.combo_lilith.addItem(tr("Oskulierendes Apogäum"), "Osculating")
        g.addWidget(self.combo_lilith, r, 1)
        r += 1

        self.chk_asteroids = QCheckBox(tr("Ceres, Pallas, Juno, Vesta berechnen"))
        g.addWidget(self.chk_asteroids, r, 0, 1, 2)
        r += 1
        self.chk_south = QCheckBox(tr("Südknoten als eigenen Punkt anzeigen"))
        g.addWidget(self.chk_south, r, 0, 1, 2)
        r += 1
        self.chk_topo = QCheckBox(tr("Topozentrische Positionen (Beobachter am Geburtsort, wirkt v. a. beim Mond)"))
        g.addWidget(self.chk_topo, r, 0, 1, 2)
        r += 1
        self.chk_stars = QCheckBox(tr("Fixsterne einbeziehen"))
        g.addWidget(self.chk_stars, r, 0)
        self.spin_star_orb = QDoubleSpinBox()
        self.spin_star_orb.setRange(0.1, 3.0)
        self.spin_star_orb.setSingleStep(0.1)
        self.spin_star_orb.setSuffix(" °")
        g.addWidget(self.spin_star_orb, r, 1)
        r += 1
        self.chk_analysis = QCheckBox(tr("Zusatzanalysen berechnen (Würden, Figuren, Halbsummen, Lose)"))
        g.addWidget(self.chk_analysis, r, 0, 1, 2)
        r += 1
        g.setRowStretch(r, 1)
        return w

    def _tab_aspects(self):
        w = QWidget()
        g = QGridLayout(w)
        g.setSpacing(6)
        g.addWidget(QLabel(f"<b>{tr('Aspekt')}</b>"), 0, 0, 1, 2)
        g.addWidget(QLabel(f"<b>{tr('Orbis (°)')}</b>"), 0, 2)
        self.aspect_checks = {}
        self.aspect_orbs = {}
        for i, (key, name, glyph, default_orb) in enumerate(ASPECT_KEYS, start=1):
            chk = QCheckBox(f"{glyph}  {tr(name)}")
            g.addWidget(chk, i, 0, 1, 2)
            spin = QDoubleSpinBox()
            spin.setRange(0.2, 12.0)
            spin.setSingleStep(0.5)
            spin.setDecimals(1)
            spin.setValue(default_orb)
            g.addWidget(spin, i, 2)
            self.aspect_checks[key] = chk
            self.aspect_orbs[key] = spin
        n = len(ASPECT_KEYS) + 1
        g.addWidget(QLabel(tr("Zuschlag für Sonne/Mond (°):")), n, 0, 1, 2)
        self.spin_lum = QDoubleSpinBox()
        self.spin_lum.setRange(0.0, 5.0)
        self.spin_lum.setSingleStep(0.5)
        g.addWidget(self.spin_lum, n, 2)
        g.addWidget(QLabel(tr("Abschlag für Knoten/Chiron/Lilith/Asteroiden (°):")), n + 1, 0, 1, 2)
        self.spin_minor = QDoubleSpinBox()
        self.spin_minor.setRange(0.0, 5.0)
        self.spin_minor.setSingleStep(0.5)
        g.addWidget(self.spin_minor, n + 1, 2)
        g.setRowStretch(n + 2, 1)
        return w

    def _tab_general(self):
        w = QWidget()
        g = QGridLayout(w)
        g.setSpacing(8)
        g.addWidget(QLabel(tr("Sprache der Oberfläche:")), 0, 0)
        self.combo_lang = QComboBox()
        self.combo_lang.addItem("Deutsch", "de")
        self.combo_lang.addItem("English", "en")
        g.addWidget(self.combo_lang, 0, 1)
        hint = QLabel(tr("Die Sprache wird nach einem Neustart vollständig übernommen."))
        hint.setStyleSheet(f"color: {styles.TEXT_MUTED}; font-size: 11px;")
        g.addWidget(hint, 1, 0, 1, 2)

        g.addWidget(QLabel(tr("Standard-Häusersystem:")), 2, 0)
        self.combo_house = QComboBox()
        for hs in ["Placidus", "Koch", "Regiomontanus", "Campanus", "WholeSign", "Equal", "Topocentric", "Porphyry"]:
            self.combo_house.addItem(hs, hs)
        g.addWidget(self.combo_house, 2, 1)
        g.setRowStretch(3, 1)
        return w

    # ── Daten ──
    def _load(self):
        d = self.settings.data
        c = d["calc"]
        self.combo_zodiac.setCurrentIndex(max(0, self.combo_zodiac.findData(c.get("zodiac", "Tropical"))))
        self.combo_ayan.setCurrentIndex(max(0, self.combo_ayan.findData(c.get("ayanamsa", 1))))
        self.combo_ayan.setEnabled(c.get("zodiac") == "Sidereal")
        self.combo_node.setCurrentIndex(max(0, self.combo_node.findData(c.get("node", "True"))))
        self.combo_lilith.setCurrentIndex(max(0, self.combo_lilith.findData(c.get("lilith", "Mean"))))
        self.chk_asteroids.setChecked(bool(c.get("asteroids")))
        self.chk_south.setChecked(bool(c.get("south_node")))
        self.chk_topo.setChecked(bool(c.get("topocentric")))
        self.chk_stars.setChecked(bool(c.get("fixed_stars", True)))
        self.spin_star_orb.setValue(float(c.get("fixed_star_orb", 1.0)))
        self.chk_analysis.setChecked(bool(c.get("analysis", True)))
        enabled = set(c.get("aspects", []))
        orbs = c.get("orbs", {})
        for key, name, glyph, default_orb in ASPECT_KEYS:
            self.aspect_checks[key].setChecked(key in enabled)
            self.aspect_orbs[key].setValue(float(orbs.get(key, default_orb)))
        self.spin_lum.setValue(float(c.get("luminary_bonus", 1.5)))
        self.spin_minor.setValue(float(c.get("minor_point_reduction", 1.5)))
        self.combo_lang.setCurrentIndex(max(0, self.combo_lang.findData(d.get("language", "de"))))
        self.combo_house.setCurrentIndex(max(0, self.combo_house.findData(d.get("house_system", "Placidus"))))

    def _reset(self):
        self.settings.data = AppSettings().data
        self._load()

    def _apply(self):
        d = self.settings.data
        c = d["calc"]
        c["zodiac"] = self.combo_zodiac.currentData()
        c["ayanamsa"] = int(self.combo_ayan.currentData() if self.combo_ayan.currentData() is not None else 1)
        c["node"] = self.combo_node.currentData()
        c["lilith"] = self.combo_lilith.currentData()
        c["asteroids"] = self.chk_asteroids.isChecked()
        c["south_node"] = self.chk_south.isChecked()
        c["topocentric"] = self.chk_topo.isChecked()
        c["fixed_stars"] = self.chk_stars.isChecked()
        c["fixed_star_orb"] = self.spin_star_orb.value()
        c["analysis"] = self.chk_analysis.isChecked()
        c["aspects"] = [k for k, _, _, _ in ASPECT_KEYS if self.aspect_checks[k].isChecked()]
        # nur abweichende Orben speichern
        c["orbs"] = {k: self.aspect_orbs[k].value() for k, _, _, default in ASPECT_KEYS
                     if abs(self.aspect_orbs[k].value() - default) > 1e-9}
        c["luminary_bonus"] = self.spin_lum.value()
        c["minor_point_reduction"] = self.spin_minor.value()
        d["language"] = self.combo_lang.currentData()
        d["house_system"] = self.combo_house.currentData()
        self.settings.save()
        self._target.data = copy.deepcopy(self.settings.data)
        self.accept()
