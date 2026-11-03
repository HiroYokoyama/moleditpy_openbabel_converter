"""Verify the actual plugin ZIP and its standalone native process boundary."""

import ast
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]


def test_zip_contains_standalone_workers_and_notices(tmp_path):
    spec = importlib.util.spec_from_file_location(
        "release_common", ROOT / "scripts/release_common.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    config = json.loads((ROOT / "scripts/release-config.json").read_text())
    config["archive"] = str(tmp_path / "converter.zip")
    # The shared helper constrains output to its root. Use a temporary staged
    # repository so this test never modifies the checkout or release artifact.
    import shutil

    staged = tmp_path / "repo"
    staged.mkdir()
    shutil.copytree(ROOT / "openbabel_converter", staged / "openbabel_converter")
    for name in config["include"]:
        shutil.copy2(ROOT / name, staged / name)
    config["archive"] = "converter.zip"
    tree = ast.parse((ROOT / config["source"]).read_text(encoding="utf-8"))
    version = next(
        ast.literal_eval(node.value)
        for node in tree.body
        if isinstance(node, ast.Assign)
        and any(isinstance(target, ast.Name) and target.id == "PLUGIN_VERSION"
                for target in node.targets)
    )
    archive = module.package(staged, config, version)
    with ZipFile(archive) as zipped:
        names = set(zipped.namelist())
        for name in ["__init__.py", "_formats_worker.py", "_conversion_worker.py",
                     "LICENSE", "LICENSING.md", "README.md"]:
            assert f"openbabel_converter/{name}" in names
        assert not any("__pycache__" in name or name.endswith(".pyc") for name in names)
        assert zipped.read("openbabel_converter/LICENSE") == (ROOT / "LICENSE").read_bytes()
        assert b"Version 2, June 1991" in zipped.read("openbabel_converter/LICENSE")
        assert b'PLUGIN_LICENSE = "GPL-2.0-or-later"' in zipped.read("openbabel_converter/__init__.py")
        zipped.extractall(tmp_path / "installed")

    # Execute a worker from the extracted ZIP outside the source tree, forbidding
    # imports of the editor and GUI libraries in that interpreter.
    worker = tmp_path / "installed/openbabel_converter/_formats_worker.py"
    output = tmp_path / "formats.json"
    runner = '''
import importlib.abc, runpy, sys
class ForbidGUI(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'PySide6', 'shiboken6', 'rdkit', 'moleditpy', 'moleditpy_linux'}:
            raise AssertionError('Worker imported GUI/editor code: ' + fullname)
sys.meta_path.insert(0, ForbidGUI())
worker, output = sys.argv[1:]
sys.argv = [worker, output]
runpy.run_path(worker, run_name='__main__')
'''
    result = subprocess.run(
        [os.environ.get("OPENBABEL_TEST_PYTHON", sys.executable), "-I", "-c", runner,
         str(worker), str(output)],
        cwd=tmp_path, capture_output=True, text=True, timeout=30,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    formats = json.loads(output.read_text())
    assert "smi" in formats["informats"]
    assert "mol" in formats["outformats"]


def test_workers_import_only_standard_library_and_engine():
    for filename in ["_formats_worker.py", "_conversion_worker.py"]:
        source = (ROOT / "openbabel_converter" / filename).read_text(encoding="utf-8")
        tree = ast.parse(source)
        imports = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(name.name.split(".")[0] for name in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports.add(node.module.split(".")[0])
        assert imports <= sys.stdlib_module_names | {"openbabel", "pybel"}
        assert "SPDX-License-Identifier: GPL-2.0-or-later" in source
