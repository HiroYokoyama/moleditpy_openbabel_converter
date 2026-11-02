"""Standalone Open Babel worker.

Copyright (C) 2026 Hiromichi Yokoyama / HiroYokoyama.
SPDX-License-Identifier: GPL-2.0-or-later

This program is free software: you can redistribute it and/or modify it under
the terms of the GNU General Public License as published by the Free Software
Foundation, either version 2 of the License, or (at your option) any later version.
This program is distributed WITHOUT ANY WARRANTY; without even the implied
warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See LICENSE.
"""

import json
import sys
from openbabel import pybel
with open(sys.argv[1], 'w', encoding='utf-8') as handle:
    json.dump({'informats': pybel.informats, 'outformats': pybel.outformats}, handle)
