"""
Shared test infrastructure for headless GUI tests.

Key difference from tests/conftest.py: PySide6 is NOT blocked, so real Qt widgets
are created.  Chemistry/scientific libraries (rdkit, numpy, pyvista, …) are still
replaced with MagicMock so no chemistry stack needs to be installed.

Environment requirement (set by CI, or locally before running):
    QT_QPA_PLATFORM=offscreen
"""

from __future__ import annotations

import contextlib
import importlib.abc
import importlib.machinery
import importlib.util
import sys
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock

import pytest

# On Windows, PySide6's Qt DLLs must be discoverable before any PySide6 sub-module
# is imported.  When PyQt6 is also installed the wrong Qt runtime can win the
# DLL search; os.add_dll_directory() pins the correct one.
import os
import sys as _sys

if _sys.platform == "win32":
    try:
        import PySide6 as _pyside6_pkg  # noqa: PLC0415

        _qt6_bin = os.path.join(os.path.dirname(_pyside6_pkg.__file__))
        if os.path.isdir(_qt6_bin):
            os.add_dll_directory(_qt6_bin)
    except Exception:
        pass  # best-effort; let the actual import surface the real error


ROOT = Path(__file__).resolve().parents[1]
PLUGINS_DIR = ROOT / "plugins"

# ---------------------------------------------------------------------------
# Same as BLOCKED_TOPS in tests/conftest.py, but PySide6 is intentionally absent
# so plugin classes that inherit from Qt bases become real widgets, not mocks.
# ---------------------------------------------------------------------------

BLOCKED_CHEMISTRY: frozenset[str] = frozenset(
    {
        "rdkit",
        "pyvista",
        "pyvistaqt",
        "numpy",
        "scipy",
        "PIL",
        "google",
        "openai",
        "anthropic",
        "truststore",
        "pymatgen",
        "openbabel",
        "pyscf",
        "ase",
        "sip",
        "modules",
        "moleditpy_linux",
        "pybel",
        "matplotlib",
        "markdown",
        "vtk",
        "vtkmodules",
        "cryptography",
        "requests",
        "moleditpy",
    }
)


# ---------------------------------------------------------------------------
# MetaPathFinder / Loader — same mechanism as tests/conftest.py
# ---------------------------------------------------------------------------


class _ChemLoader(importlib.abc.Loader):
    def create_module(self, spec: importlib.machinery.ModuleSpec) -> MagicMock:
        m = MagicMock()
        m.__name__ = spec.name
        m.__spec__ = spec
        m.__path__ = []
        m.__package__ = spec.name.split(".")[0]
        return m  # type: ignore[return-value]

    def exec_module(self, module: object) -> None:
        pass


class _ChemFinder(importlib.abc.MetaPathFinder):
    _loader = _ChemLoader()

    def find_spec(
        self,
        fullname: str,
        path: object,
        target: object = None,
    ) -> importlib.machinery.ModuleSpec | None:
        if fullname.split(".")[0] in BLOCKED_CHEMISTRY:
            return importlib.machinery.ModuleSpec(fullname, self._loader)
        return None


@contextlib.contextmanager
def mock_chemistry_imports() -> Generator[None, None, None]:
    """
    Block chemistry/scientific imports (replacing them with MagicMock) while
    letting PySide6 through so real Qt widgets are constructed.
    """
    removed = {
        k: sys.modules.pop(k)
        for k in list(sys.modules)
        if k.split(".")[0] in BLOCKED_CHEMISTRY
    }
    finder = _ChemFinder()
    sys.meta_path.insert(0, finder)
    try:
        yield
    finally:
        sys.meta_path.remove(finder)
        sys.modules.update(removed)
        for k in list(sys.modules):
            if k.split(".")[0] in BLOCKED_CHEMISTRY and k not in removed:
                del sys.modules[k]


def load_plugin_for_gui(path: Path) -> object:
    """
    Load *path* as an isolated module with chemistry mocked.
    Must be called inside a ``mock_chemistry_imports()`` block.
    """
    mod_name = f"_gui_{path.stem}_{abs(hash(path))}"
    spec = importlib.util.spec_from_file_location(mod_name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


class _MockOverlay:
    """Stand-in for a mock that overrides some attributes and forwards the rest."""

    def __init__(self, base: object, **attrs: object) -> None:
        self.__dict__.update(attrs)
        self.__dict__["_overlay_base"] = base

    def __getattr__(self, name: str) -> object:
        return getattr(self.__dict__["_overlay_base"], name)

    def __call__(self, *args: object, **kwargs: object) -> object:
        return self.__dict__["_overlay_base"](*args, **kwargs)


def patch_mock_attr(monkeypatch, owner: object, name: str, attr: str, value: object) -> None:
    """Patch ``owner.<name>.<attr>`` where ``owner.<name>`` is one of the suite's mocks.

    pytest 9.2 undoes ``monkeypatch.setattr(mock, attr, ...)`` by deleting the
    attribute, after which a MagicMock raises AttributeError for it in every
    later test.  Swap ``owner.<name>`` for an overlay instead, so the shared
    mock is never touched; patches on the same name stack.
    """
    monkeypatch.setattr(owner, name, _MockOverlay(getattr(owner, name), **{attr: value}))


# ---------------------------------------------------------------------------
# Session-scoped QApplication
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def qapp():
    """
    One QApplication for the entire test session.

    pytest-qt provides its own qapp fixture, but we avoid that dependency here.
    QT_QPA_PLATFORM=offscreen must be set before this fixture is used (done by
    CI via the workflow env block, or locally by the developer).
    """
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication(sys.argv[:1])
    yield app


# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def cleanup_native_windows(qapp):
    """Delete each test's native widgets before a later event loop can see them."""
    from PySide6.QtCore import QCoreApplication, QEvent
    from shiboken6 import isValid

    existing = set(qapp.topLevelWidgets())
    yield
    for widget in qapp.topLevelWidgets():
        if widget not in existing and isValid(widget):
            widget.hide()
            widget.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


# ---------------------------------------------------------------------------
# Registry helper (mirrors tests/conftest.py::visible_py_plugins)
# ---------------------------------------------------------------------------
