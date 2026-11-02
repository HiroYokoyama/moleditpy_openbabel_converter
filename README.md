# OpenBabel Conversion Tool for MoleditPy

[![CI](https://github.com/HiroYokoyama/moleditpy_openbabel_converter/actions/workflows/test.yml/badge.svg)](https://github.com/HiroYokoyama/moleditpy_openbabel_converter/actions/workflows/test.yml)
[![GitHub tag](https://img.shields.io/github/v/tag/HiroYokoyama/moleditpy_openbabel_converter?label=version)](https://github.com/HiroYokoyama/moleditpy_openbabel_converter/tags)
[![License: GPL v2 or later](https://img.shields.io/badge/License-GPLv2%2B-blue.svg)](LICENSE)

Import and export chemical file formats with Open Babel in **MoleditPy 5**.
Includes drag and drop, a molecule selector for multi-molecule files, and export
of the current structure. Native parsing and format discovery run in disposable
Python processes; Open Babel is never imported into the editor process.

This is the external package successor to the collection's single-file
**OpenBabel Conversion Tool**. It keeps the existing plugin name and behavior.

## Install

Use a Python-installed MoleditPy with Python 3.10–3.14. Install the official engine
in that same interpreter:

```sh
python -m pip install "openbabel>=3.2.1,<3.3"
```

Install the release ZIP with MoleditPy's Plugin Manager. The ZIP contains the
`openbabel_converter/` package, both workers, and the legal notices. There are no
companion files to download separately. For manual installation, extract that
folder into `~/.moleditpy/plugins/` (`%USERPROFILE%\.moleditpy\plugins\` on Windows).

**Upgrading from the old single-file plugin:** disable or remove
`openbabel_conversion_tool.py` from your user plugin directory before restarting,
so the old and new copies do not both register their actions. Existing files and
editor projects are unaffected. Do not install both variants together.

If replacing `openbabel-wheel`, uninstall it before installing official
`openbabel`; the distributions share an import namespace.

Frozen/portable editor bundles are unsupported: their executable cannot run the
Python workers. Install MoleditPy and Open Babel in a regular Python environment.

## Behavior and limits

- Import supported formats through the registered file/drop handlers.
- Export the current structure through the OpenBabel export action.
- MoleditPy's own multi-molecule SDF selector takes precedence when available.
- Parsing runs with cancellation and a 30-second timeout.
- Import is limited to 32 MiB, 500 molecules, and 10,000 atoms per molecule.
- Format discovery is cached against the interpreter and installed engine files.

The GUI uses PySide6 and RDKit supplied by the editor. Workers use Open Babel and
Python's standard library, and do not load Qt, RDKit, or MoleditPy.

## License and process boundary

First-party runtime code is **GPL-2.0-or-later**. Open Babel retains its own
**GPL-2.0-only** terms. The GUI and worker communicate using files containing
MOL structures and JSON metadata; no native objects or Python object references
cross the process boundary.

[LICENSING.md](LICENSING.md) records the intended separate-program treatment,
the version choices, upstream sources, and redistribution requirements. A separate
repository or process alone does not establish legal independence.

## Development

```sh
python -m pip install -e ".[engine,test]"
python -m pytest -q
python scripts/release_common.py verify --version 1.0.0
python scripts/release_common.py package --version 1.0.0
```

Set `QT_QPA_PLATFORM=offscreen` and `PYTEST_QT_API=pyside6` for headless testing.
Tests migrated from the collection cover UI flows, failure handling and actual
Open Babel conversion. Distribution tests check notices and standalone workers.

The release workflow builds a ZIP, publishes a GitHub release and requests a
registry update when `REGISTRY_PAT` is configured. Otherwise use the collection's
registration issue form. Never change the registry to an unpublished asset.
