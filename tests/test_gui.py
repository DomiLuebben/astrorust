"""Offline integration tests; no real user profiles or paid providers are accessed."""
import atexit
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
(ROOT / 'work').mkdir(exist_ok=True)
TEMP = tempfile.TemporaryDirectory(prefix='gui-tests-', dir=ROOT / 'work')
atexit.register(TEMP.cleanup)
os.environ['HOME'] = TEMP.name
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
sys.path.insert(0, str(ROOT / 'gui'))
from PyQt6.QtCore import QDate
from PyQt6.QtWidgets import QApplication, QMessageBox, QFileDialog
from appsettings import AppSettings
from mainwindow import MainWindow
from profilestore import ProfileStore
from settings_dialog import SettingsDialog
from database_dialog import DatabaseDialog
from widgets import AstroDateEdit, CivilDate
from ai_engine import AiGenerationWorker
import aaf
import i18n

APP = QApplication([])
MESSAGES = []
for level in ('warning', 'critical', 'information'):
    setattr(QMessageBox, level, lambda *args, _level=level, **kwargs: MESSAGES.append((_level, args[1:3])))


class GuiTests(unittest.TestCase):
    def setUp(self):
        i18n.set_language('de')
        MESSAGES.clear()
        self.window = MainWindow(AppSettings())
        self.view = self.window.current()

    def tearDown(self):
        self.window.close()
        APP.processEvents()

    def test_initial_chart_and_independent_tabs(self):
        self.assertEqual(self.view.tabs.count(), 7)
        self.assertEqual(self.view.chart['name'], 'Albert Einstein')
        second = self.window.add_tab(dict(self.view.request_a(), name='Second'))
        second.person_a.edit_name.setText('Changed')
        second.calculate()
        self.assertEqual(self.view.chart['name'], 'Albert Einstein')
        self.window.close_tab(1)
        self.assertEqual(self.window.tabs.count(), 1)

    def test_changed_birth_data_clear_derived_results(self):
        v = self.view
        v.vedic.run()
        v.astromap.run()
        v.forecast.prog_date.setDate(QDate(1920, 3, 14))
        v.forecast.run_progression()
        v._ai_text = 'Old person'
        v.person_a.edit_name.setText('New person')
        v.calculate()
        self.assertIsNone(v.vedic.res)
        self.assertIsNone(v.astromap.res)
        self.assertIsNone(v.forecast.last_progression)
        self.assertEqual(v.forecast.table_prog.rowCount(), 0)
        self.assertEqual(v._ai_text, '')
        self.assertEqual(v.overlays, {})

    def test_derived_calculation_synchronizes_pending_edits(self):
        self.view.person_a.edit_name.setText('Fresh input')
        self.view.vedic.run()
        self.assertEqual(self.view.chart['name'], 'Fresh input')
        self.assertEqual(self.view.vedic.res['chart']['name'], 'Fresh input')

    def test_invalid_birth_date_is_never_silently_reused(self):
        v = self.view
        v.person_a.edit_date.setText('2024-02-30')
        with self.assertRaises(ValueError):
            v.request_a()
        v.forecast.run_return()
        v.forecast.run_sky()
        v.vedic.run()
        v.save_profile()
        self.assertIsNone(v.forecast.last_return)
        self.assertIsNone(v.vedic.res)
        self.assertTrue(MESSAGES)

    def test_julian_leap_day_and_calendar_transition(self):
        edit = AstroDateEdit()
        edit.setText('1500-02-29')
        self.assertTrue(edit.is_valid_input())
        self.assertEqual((edit.date().year(), edit.date().month(), edit.date().day()), (1500, 2, 29))
        edit.setDate(CivilDate(1500, 2, 29))
        self.assertEqual(edit.text(), '1500-02-29')
        self.assertEqual(CivilDate(1582, 10, 4).daysTo(CivilDate(1582, 10, 15)), 1)
        edit.setText('1900-02-29')
        self.assertFalse(edit.is_valid_input())

    def test_typed_zone_overrides_old_combo_selection(self):
        a = self.view.person_a
        a.combo_zone.setEditText('America/New_York')
        self.assertEqual(a.zone(), 'America/New_York')

    def test_partner_city_completer_only_changes_partner(self):
        v = self.view
        before = v.person_a.profile()
        berlin = next(c for c in v.backend.search_cities('Berlin') if c['name'] == 'Berlin')
        v.person_b._on_city_chosen(berlin)
        self.assertEqual(v.person_a.profile(), before)
        self.assertEqual(v.person_b.zone(), 'Europe/Berlin')

    def test_settings_cancel_and_zero_ayanamsa(self):
        settings = AppSettings({'calc': {'ayanamsa': 0}})
        dialog = SettingsDialog(self.view.backend, settings)
        dialog._reset()
        dialog.reject()
        self.assertEqual(settings.data['calc']['ayanamsa'], 0)
        dialog = SettingsDialog(self.view.backend, settings)
        dialog._apply()
        self.assertEqual(settings.data['calc']['ayanamsa'], 0)

    def test_renamed_profile_updates_existing_id(self):
        store = self.window.store
        original = store.upsert(dict(self.view.person_a.profile(), name='Rename me'))
        self.view.load_profile(original)
        self.view.person_a.edit_name.setText('Renamed')
        self.view.save_profile()
        found = [p for p in store.profiles if p['id'] == original['id']]
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0]['name'], 'Renamed')
        self.assertFalse(any(p['name'] == 'Rename me' for p in store.profiles))

    def test_notes_survive_database_filter_refresh(self):
        dialog = DatabaseDialog(self.window.store)
        dialog.table.selectRow(0)
        ident = dialog._notes_target
        dialog.notes.setPlainText('Keep this note')
        dialog.edit_search.setText('no such profile')
        p = next(p for p in self.window.store.profiles if p['id'] == ident)
        self.assertEqual(p['notes'], 'Keep this note')
        dialog.close()

    def test_aaf_round_trip_dst_lmt_seconds_and_notes(self):
        backend = self.view.backend
        profiles = [
            dict(self.view.person_a.profile(), second=17, group='Test', tags=['A', 'B'], notes='Line one, comma\nLine two'),
            dict(self.view.person_a.profile(), name='Summer Berlin', year=1990, month=7, day=15, second=33),
            dict(self.view.person_a.profile(), name='Julian leap', year=1500, month=2, day=29),
        ]
        text = aaf.dumps(profiles, backend)
        imported = aaf.loads(text, backend)
        self.assertEqual(len(imported), 3)
        for old, new in zip(profiles, imported):
            self.assertAlmostEqual(backend.call('chart', old)['julian_day'], backend.call('chart', new)['julian_day'], places=7)
        self.assertEqual(imported[0]['notes'], profiles[0]['notes'])
        self.assertEqual(imported[0]['tags'], ['A', 'B'])
        self.assertEqual(imported[1]['second'], 33)
        self.assertIn(',1\n', text)  # DST is separate from the standard offset.
        self.assertIn(',L\n', text)

    def test_aaf_external_standard_dst_and_jd_precedence(self):
        text = '#A93:Test,Person,e,15.7.1990,14:30,Berlin,D\n#B93:*,52n31,13e24,1he,1\n'
        p = aaf.loads(text, self.view.backend)[0]
        self.assertEqual(p['timezone_offset'], 2)
        text = '#A93:Test,,e,1.1.1900,12:00,Berlin,D\n#B93:2451545.0,52n31,13e24,0h,0\n'
        p = aaf.loads(text, self.view.backend)[0]
        self.assertEqual((p['year'], p['month'], p['day'], p['hour']), (2000, 1, 1, 12))

    def test_import_is_atomic_and_csv_keeps_seconds(self):
        store = self.window.store
        before = json.dumps(store.profiles, sort_keys=True)
        good = dict(self.view.person_a.profile(), name='Would be imported')
        path = Path(TEMP.name) / 'bad.json'
        path.write_text(json.dumps([good, dict(good, day=99)]))
        with self.assertRaises(ValueError):
            store.import_file(str(path))
        self.assertEqual(json.dumps(store.profiles, sort_keys=True), before)
        p = dict(good, second=29)
        store.export_csv(str(path.with_suffix('.csv')), [p])
        store.import_file(str(path.with_suffix('.csv')))
        self.assertEqual(next(p for p in store.profiles if p['name'] == good['name'])['second'], 29)

    def test_english_ui_is_translated(self):
        i18n.set_language('en')
        window = MainWindow(AppSettings({'language': 'en'}))
        self.assertEqual(window.menuBar().actions()[0].text(), 'File')
        self.assertEqual(window.current().tabs.tabText(2), 'Forecast')
        self.assertEqual(window.current().person_a.title(), 'Birth data (natal)')
        self.assertIn('Natal personality profile', window.current().combo_ai.itemText(0))
        window.close()
        i18n.set_language('de')

    def test_cli_streams_without_newlines_and_drains_large_stderr(self):
        worker = AiGenerationWorker(self.view.chart, 'gesamt', {})
        text = []
        worker.chunk_signal.connect(text.append)
        worker._run_cli(sys.executable, ['-c', 'import sys; sys.stderr.write("x"*200000); sys.stdout.write("streamed without newline")'], 'Test CLI')
        self.assertEqual(''.join(text), 'streamed without newline')

    def test_cli_cancel_ends_child_process(self):
        class SlowWorker(AiGenerationWorker):
            def run(self):
                self._run_cli(sys.executable, ['-c', 'import time; time.sleep(60)'], 'Test CLI')
        worker = SlowWorker(self.view.chart, 'gesamt', {})
        worker.start()
        deadline = time.monotonic() + 3
        while worker._proc is None and time.monotonic() < deadline:
            APP.processEvents()
            time.sleep(0.01)
        self.assertIsNotNone(worker._proc)
        proc = worker._proc
        worker.cancel()
        self.assertTrue(worker.wait(3000))
        self.assertIsNotNone(proc.poll())


if __name__ == '__main__':
    unittest.main(verbosity=2)
