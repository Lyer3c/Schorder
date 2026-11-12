"""主键生成：UUIDv7。

为什么不用自增整数：
- 不泄露业务量（订单号 1001 说明你只有 1000 单）
- 分库/换库时不需要重新分配 ID

为什么是 v7 而不是 v4：
- v7 前 48 位是毫秒时间戳，天然有序
- 作为主键写入时，索引局部性好得多（B-tree 不会随机跳）

Python 3.13 标准库还没有 uuid7()，这里手写一个。
"""

from __future__ import annotations

import os
import time
import uuid


def uuid7() -> str:
    """生成 UUIDv7 字符串。

    位布局（RFC 9562）：
        48 位毫秒时间戳 | 4 位版本号(7) | 12 位随机 | 2 位变体(10) | 62 位随机
    """
    timestamp_ms = int(time.time() * 1000) & 0xFFFFFFFFFFFF
    rand_a = int.from_bytes(os.urandom(2), "big") & 0x0FFF
    rand_b = int.from_bytes(os.urandom(8), "big") & 0x3FFFFFFFFFFFFFFF

    value = timestamp_ms << 80
    value |= 0x7 << 76
    value |= rand_a << 64
    value |= 0b10 << 62
    value |= rand_b

    return str(uuid.UUID(int=value))
