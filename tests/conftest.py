"""Mock dependencies for the migrated converter regression tests."""

from __future__ import annotations

import ast
import contextlib
import importlib.abc
import importlib.machinery
import importlib.util
import sys
import textwrap
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock

ROOT = Path(__file__).resolve().parents[1]

# ---------------------------------------------------------------------------
# Packages whose imports are replaced with MagicMock
# ---------------------------------------------------------------------------

BLOCKED_TOPS: frozenset[str] = frozenset(
    {
        "PySide6",
        "shiboken6",
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
# MetaPathFinder / Loader
# ---------------------------------------------------------------------------


class _MagicLoader(importlib.abc.Loader):
    def create_module(self, spec: importlib.machinery.ModuleSpec) -> MagicMock:
        m = MagicMock()
        m.__name__ = spec.name
        m.__spec__ = spec
        m.__path__ = []
        m.__package__ = spec.name.split(".")[0]
        return m  # type: ignore[return-value]

    def exec_module(self, module: object) -> None:
        pass


class _MagicFinder(importlib.abc.MetaPathFinder):
    _loader = _MagicLoader()

    def find_spec(
        self,
        fullname: str,
        path: object,
        target: object = None,
    ) -> importlib.machinery.ModuleSpec | None:
        if fullname.split(".")[0] in BLOCKED_TOPS:
            return importlib.machinery.ModuleSpec(fullname, self._loader)
        return None


@contextlib.contextmanager
def mock_optional_imports() -> Generator[None, None, None]:
    """
    Context manager that stubs all optional/heavy imports with MagicMock.

    Any module whose top-level package is in ``BLOCKED_TOPS`` is intercepted
    by a custom ``MetaPathFinder`` and replaced with a ``MagicMock`` for the
    duration of the block.  Previously-loaded real copies are restored on exit.
    """
    removed = {
        k: sys.modules.pop(k)
        for k in list(sys.modules)
        if k.split(".")[0] in BLOCKED_TOPS
    }
    finder = _MagicFinder()
    sys.meta_path.insert(0, finder)
    try:
        yield
    finally:
        sys.meta_path.remove(finder)
        sys.modules.update(removed)
        for k in list(sys.modules):
            if k.split(".")[0] in BLOCKED_TOPS and k not in removed:
                del sys.modules[k]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_plugin(path: Path) -> object:
    """
    Load *path* as an isolated module.  Must be called inside
    a ``mock_optional_imports()`` block.
    """
    mod_name = f"_smoke_{path.stem}_{abs(hash(path))}"
    spec = importlib.util.spec_from_file_location(mod_name, path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def make_context() -> MagicMock:
    """
    Return a stub PluginContext with a non-None main window.

    Plugins may assume ``get_main_window()`` is non-None at initialize() time
    (the host app is fully started before plugins load).
    """
    ctx = MagicMock()
    ctx.get_main_window.return_value = MagicMock()
    return ctx


def extract_function(
    path: Path,
    class_name: str | None,
    fn_name: str,
    extra_globals: dict | None = None,
):
    """
    Extract a function or method from source via AST and exec it standalone.

    Needed for methods of Qt-derived classes: the mocked Qt bases make the
    class object a MagicMock, so methods can't be reached via the class.

    ``class_name=None`` extracts a module-level function instead of a method.
    """
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    scope = tree
    if class_name is not None:
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                scope = node
                break
        else:
            raise AssertionError(f"class {class_name} not found in {path}")
    for node in scope.body:
        if isinstance(node, ast.FunctionDef) and node.name == fn_name:
            segment = ast.get_source_segment(source, node)
            ns = {"MagicMock": MagicMock}
            ns.update(extra_globals or {})
            exec(textwrap.dedent(segment), ns)  # noqa: S102
            return ns[fn_name]
    raise AssertionError(f"function {fn_name} not found in {path}")

