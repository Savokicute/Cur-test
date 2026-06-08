# coding=utf-8
"""
Ensure `import crawl4ai` resolves to the inner package
`{repo}/crawl4ai/crawl4ai`, not a broken implicit namespace on `{repo}/crawl4ai`.

Editable installs in a monorepo can register the project root; reload fixes imports.
"""

from __future__ import annotations

import sys
from pathlib import Path


def fix_crawl4ai_import_path() -> None:
    bridge_dir = Path(__file__).resolve().parent
    repo_root = bridge_dir.parent
    c4_repo = repo_root / "crawl4ai"
    inner = c4_repo / "crawl4ai" / "__init__.py"
    if not inner.is_file():
        return
    key = str(c4_repo.resolve())
    # Drop duplicate / wrong ordering
    sys.path[:] = [p for p in sys.path if Path(p).resolve() != Path(key)]
    if key not in sys.path:
        sys.path.insert(0, key)
    if "crawl4ai" in sys.modules:
        mod = sys.modules["crawl4ai"]
        if getattr(mod, "__file__", None) is None:
            del sys.modules["crawl4ai"]
            for name in list(sys.modules):
                if name.startswith("crawl4ai."):
                    del sys.modules[name]
    # 设置 crawl4ai 使用项目内的目录作为基础目录
    import os
    c4_data_dir = repo_root / ".crawl4ai"
    os.makedirs(c4_data_dir, exist_ok=True)
    os.environ["CRAWL4_AI_BASE_DIRECTORY"] = str(c4_data_dir)


fix_crawl4ai_import_path()
