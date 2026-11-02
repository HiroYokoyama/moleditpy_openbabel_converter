"""Standalone Open Babel worker.

Copyright (C) 2026 Hiromichi Yokoyama / HiroYokoyama.
SPDX-License-Identifier: GPL-2.0-or-later

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 2 of the License, or (at your option) any later version.
This program is distributed WITHOUT ANY WARRANTY; without even the implied
warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See LICENSE.
"""

import sys
import json
try:
    from openbabel import pybel
except ImportError:
    import pybel
mode, fmt, source, output = sys.argv[1:5]
if mode == 'import':
    records = []
    size = 0
    for mol in pybel.readfile(fmt, source):
        if len(records) >= 500:
            raise ValueError('File contains more than 500 molecules; split it first.')
        if mol.OBMol.NumAtoms() > 10000:
            raise ValueError('Molecule exceeds 10000 atoms.')
        block = mol.write('mol')
        size += len(block.encode('utf-8'))
        if size > 32 * 1024 * 1024:
            raise ValueError('Converted structures exceed 32 MiB; split the file first.')
        records.append(dict(title=mol.title[:256], formula=mol.formula[:256], block=block))
    with open(output, 'w', encoding='utf-8') as handle:
        json.dump(records, handle)
else:
    with open(source, encoding='utf-8') as handle:
        mol = pybel.readstring('mol', handle.read())
    mol.write(fmt, output, overwrite=True)
