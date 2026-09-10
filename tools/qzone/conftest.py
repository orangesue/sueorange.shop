"""让测试可以直接 import qz_archive。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

