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
            "/usr/lib/libastrorust.so",
            "/usr/lib/astrorust/libastrorust.so",
            "/usr/local/lib/libastrorust.so",
        ]

        lib_path = None
        for path in candidates:
            if os.path.exists(path):
                lib_path = path
                break

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
            return None

        try:
            val_bytes = ctypes.string_at(raw_ptr)
            val_str = val_bytes.decode("utf-8", errors="replace")
            return val_str
        finally:
            self.lib.astrorust_free_string(raw_ptr)

    def calculate_chart(self, req_dict: dict) -> dict:
        res_str = self._call_c_func(self.lib.astrorust_calculate_chart, req_dict)
        data = json.loads(res_str)
        if "error" in data:
            raise ValueError(data["error"])
        return data

    def calculate_transit(self, req_dict: dict) -> dict:
        res_str = self._call_c_func(self.lib.astrorust_calculate_transit, req_dict)
        data = json.loads(res_str)
        if "error" in data:
            raise ValueError(data["error"])
        return data

    def calculate_synastry(self, req_dict: dict) -> dict:
        res_str = self._call_c_func(self.lib.astrorust_calculate_synastry, req_dict)
        data = json.loads(res_str)
        if "error" in data:
            raise ValueError(data["error"])
        return data

    def get_profiles(self) -> list:
        res_str = self._call_c_func(self.lib.astrorust_get_profiles)
        return json.loads(res_str)

    def search_cities(self, query: str = "") -> list:
        res_str = self._call_c_func(self.lib.astrorust_search_cities, query)
        return json.loads(res_str)

    def export_svg(self, req_dict: dict) -> str:
        return self._call_c_func(self.lib.astrorust_export_svg, req_dict)
