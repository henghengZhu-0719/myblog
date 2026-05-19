"""
查看工作记忆的内容。

注意：工作记忆是纯内存的，只有在 agent 运行期间才能看到。
程序退出后数据自动清空。
"""

import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from memory.base import MemoryConfig
from memory.types.working import WorkingMemory


def inspect(memory_path: str = "./memory_data"):
    config = MemoryConfig(storage_path=Path(memory_path))
    wm = WorkingMemory(config=config, storage_backend=None)

    items = wm.get_all()

    if not items:
        print("📭 工作记忆中没有任何内容。")
        print("   提示：启动 main.py 后用 remember 工具保存，")
        print("   然后在不退出的情况下查看。")
        return

    print(f"📝 工作记忆：共 {len(items)} 条\n")
    for i, item in enumerate(items, 1):
        print(f"  [{i}] ID:        {item.id}")
        print(f"      内容:      {item.content}")
        print(f"      重要性:    {item.importance:.2f}")
        print(f"      时间:      {item.timestamp}")
        print()

    stats = wm.get_stats()
    print(f"统计: {stats['count']} 条 / {stats['current_tokens']} tokens")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "./memory_data"
    inspect(path)
