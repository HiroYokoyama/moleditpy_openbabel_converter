# Licensing and process boundary

## First-party grant

Copyright (C) 2026 Hiromichi Yokoyama / HiroYokoyama and the contributors
identified in the source history and notices.

The first-party plugin runtime and its tests in this repository are offered under
the GNU General Public License, **version 2 or (at your option) any later version**
(`GPL-2.0-or-later`). See [LICENSE](LICENSE). This grant applies from the external
package's 2026.11.02 release. Historical collection releases retain their original grants.
The source originates from the owner's `moleditpy-plugins` Conversion Tool; the
new grant covers the owner's rights and does not relicense upstream dependencies.

The unchanged shared maintenance helper `scripts/release_common.py` retains
upstream **LGPL-3.0-or-later** terms. `scripts/LICENSE`, `scripts/COPYING`, and
`scripts/common-tools.lock.json` preserve its license and pinned provenance.
This development/release helper is not part of the installed runtime ZIP.

## Third-party terms and version choices

Open Babel's official library documentation requires GPLv2 for Python bindings
as well as C++ users. Its package metadata identifies **GPL-2.0-only**. Treat the
supported `openbabel>=3.2.1,<3.3` engine under those terms. This repository does
not grant permission to use Open Babel under GPLv3.

When conveying the standalone worker with Open Babel, choose **GPLv2** for the
worker's first-party code. For the GUI program using PySide6 under LGPLv3,
choose **GPLv3** (or another compatible permitted version) for the GUI code.
GPL-2.0-only and GPLv3 are not compatible licenses for one combined program;
the later-version option on our own code does not change Open Babel's terms.

PySide6, RDKit and MoleditPy keep their own terms. No Open Babel binary or source
is bundled by our package; the user installs the engine separately. Installing
dependencies separately does not itself remove their license obligations.

## Actual boundary and intended treatment

`openbabel_converter/__init__.py` is the GUI plugin. Its only native engine
interaction is to launch a fresh Python interpreter using `QProcess`. Worker
source is read from the adjacent standalone files and passed to `python -c`.
It is never evaluated or imported in the GUI interpreter.

- `_formats_worker.py`: receives an output path; writes JSON maps of supported
  format names and descriptions.
- `_conversion_worker.py`: receives mode, format, input path and output path.
  Import reads a chemical file and writes JSON records containing title, formula
  and MOL text. Export reads MOL text and writes the selected chemical format.
- Both workers import only Python's standard library and Open Babel. They can
  run as ordinary scripts without the GUI package, Qt, RDKit, or MoleditPy.
- No address, native handle, Qt object, `OBMol`, or shared Python object crosses
  the boundary. No editor module is imported by a worker. The engine is not
  linked into or bundled with the editor.

These facts support treating the GUI and the chemical conversion workers as
separate programs distributed together, with an ordinary data interface. The
tests verify these technical properties. GNU's guidance also considers the
semantics of communication: separate processes, JSON, a ZIP, or a repository
boundary alone are not conclusive. This is the project's documented licensing
approach, not a legal ruling or blanket clearance for other combinations.
Changes that introduce shared internal data structures, in-process imports or
native library bundling require a fresh review of the combined work.

## Distribution

The plugin ZIP includes both standalone worker sources, the GUI source, LICENSE,
this document and README inside the package directory. Retain applicable source,
copyright notices and license texts. Conveying compiled or bundled engines also
requires compliance with their corresponding-source and other obligations; this
project's source-only plugin release does not fulfill those obligations for an
engine you add yourself. Do not present the whole Open Babel/Qt combination as
a single GPLv3 program.

## Sources

- [Open Babel library licensing, including Python](https://openbabel.org/docs/UseTheLibrary/intro.html)
- [Open Babel package metadata](https://pypi.org/pypi/openbabel/3.2.1/json)
- [GNU: GPLv2/GPLv3 compatibility](https://www.gnu.org/licenses/gpl-faq.en.html#v2v3Compatibility)
- [GNU: separate programs and communication semantics](https://www.gnu.org/licenses/gpl-faq.en.html#MereAggregation)
- [Qt for Python licensing](https://doc.qt.io/qtforpython-6.10/)
