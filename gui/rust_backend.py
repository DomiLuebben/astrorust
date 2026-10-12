# -*- coding: utf-8 -*-
"""
Astrorust — High-Performance Swiss Ephemeris FFI Bridge to Rust
"""

import ctypes
import json
import os
import sys

class RustBackend:
    _instance = None

    @classmethod
    def get(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Check potential library paths (debug, release, or system)
        candidates = [
            os.path.join(base_dir, "target", "debug", "libastrorust.so"),
            os.path.join(base_dir, "target", "release", "libastrorust.so"),
            os.path.join(base_dir, "libastrorust.so"),
            os.path.abspath(os.path.join(base_dir, "..", "..", "lib", "libastrorust.so")),
            "/usr/lib/libastrorust.so",
            "/usr/lib/astrorust/libastrorust.so",
            "/usr/local/lib/libastrorust.so",
        ]

        # Mehrere Treffer (z. B. debug + release): die zuletzt gebaute Bibliothek gewinnt,
        # sonst läuft die GUI gegen eine veraltete Debug-Datei.
        existing = [p for p in candidates if os.path.exists(p)]
        lib_path = None
        if existing:
            project_builds = [p for p in candidates[:2] if p in existing]
            lib_path = (max(project_builds, key=os.path.getmtime)
                        if project_builds else existing[0])
        override = os.environ.get("ASTRORUST_LIBRARY")
        if override:
            lib_path = override if os.path.isfile(override) else None

        if not lib_path:
            raise RuntimeError(
                f"libastrorust.so nicht gefunden! Bitte zuerst im Projektordner 'cargo build' ausführen. Gesucht in: {candidates}"
            )

        self.lib = ctypes.CDLL(lib_path)

        # Configure C signatures
        self.lib.astrorust_calculate_chart.argtypes = [ctypes.c_char_p]
        self.lib.astrorust_calculate_chart.restype = ctypes.c_void_p

        self.lib.astrorust_calculate_transit.argtypes = [ctypes.c_char_p]
        self.lib.astrorust_calculate_transit.restype = ctypes.c_void_p

        self.lib.astrorust_calculate_synastry.argtypes = [ctypes.c_char_p]
        self.lib.astrorust_calculate_synastry.restype = ctypes.c_void_p

        self.lib.astrorust_get_profiles.argtypes = []
        self.lib.astrorust_get_profiles.restype = ctypes.c_void_p

        self.lib.astrorust_search_cities.argtypes = [ctypes.c_char_p]
        self.lib.astrorust_search_cities.restype = ctypes.c_void_p

        self.lib.astrorust_export_svg.argtypes = [ctypes.c_char_p]
        self.lib.astrorust_export_svg.restype = ctypes.c_void_p

        self.lib.astrorust_call.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        self.lib.astrorust_call.restype = ctypes.c_void_p

        self.lib.astrorust_free_string.argtypes = [ctypes.c_void_p]
        self.lib.astrorust_free_string.restype = None

    def _call_c_func(self, func, *args):
        c_args = []
        for a in args:
            if isinstance(a, str):
                c_args.append(a.encode("utf-8"))
            elif isinstance(a, dict):
                c_args.append(json.dumps(a).encode("utf-8"))
            else:
                c_args.append(a)

        raw_ptr = func(*c_args)
        if not raw_ptr:
            raise RuntimeError("Die Rust-Bibliothek lieferte keine Antwort.")

        try:
            val_bytes = ctypes.string_at(raw_ptr)
            val_str = val_bytes.decode("utf-8", errors="replace")
            return val_str
        finally:
            self.lib.astrorust_free_string(raw_ptr)

    def _call_json(self, func, req_dict):
        data = json.loads(self._call_c_func(func, req_dict))
        if isinstance(data, dict) and "error" in data:
            raise ValueError(data["error"])
        return data

    def call(self, method: str, req: dict | None = None):
        """Allgemeiner Aufruf der Rust-Bibliothek (`astrorust_call`); wirft ValueError bei {"error": ...}."""
        payload = json.dumps(req if req is not None else {}).encode("utf-8")
        raw_ptr = self.lib.astrorust_call(method.encode("utf-8"), payload)
        if not raw_ptr:
            raise RuntimeError("Die Rust-Bibliothek lieferte keine Antwort.")
        try:
            text = ctypes.string_at(raw_ptr).decode("utf-8", errors="replace")
        finally:
            self.lib.astrorust_free_string(raw_ptr)
        data = json.loads(text)
        if isinstance(data, dict) and "error" in data and len(data) == 1:
            raise ValueError(data["error"])
        return data

    def calculate_chart(self, req_dict: dict) -> dict:
        return self._call_json(self.lib.astrorust_calculate_chart, req_dict)

    def calculate_transit(self, req_dict: dict) -> dict:
        return self._call_json(self.lib.astrorust_calculate_transit, req_dict)

    def calculate_synastry(self, req_dict: dict) -> dict:
        return self._call_json(self.lib.astrorust_calculate_synastry, req_dict)

    def get_profiles(self) -> list:
        res_str = self._call_c_func(self.lib.astrorust_get_profiles)
        return json.loads(res_str)

    def search_cities(self, query: str = "") -> list:
        return self.call("atlas_search", {"query": query})

    def export_svg(self, req_dict: dict) -> str:
        # Die Bibliothek liefert den SVG-Text als JSON-String, Fehler als {"error": ...}.
        return self._call_json(self.lib.astrorust_export_svg, req_dict)
