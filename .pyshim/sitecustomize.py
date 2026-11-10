"""Windows 沙箱兼容垫片（仅本地开发使用，不进入产物）。

背景：本机 DSH workspace-write 沙箱下，用 mode 0o700 创建的目录**不可写、不可读**，
事后 os.chmod 也会被拒绝（WinError 5）。而 `tempfile.mkdtemp()`、`pytest` 的
tmp_path 都用 0700 建目录，于是 pip 解包、pytest 临时目录都会失败。

处理：
1. 重新实现 mkdtemp，用 os.makedirs 默认 0777 建目录
2. 把 os.mkdir / os.makedirs 的 0700 请求放宽到 0777（仅本机开发）

用法：把本文件所在目录加入 PYTHONPATH，解释器启动时自动导入。
生产环境不要带这个目录。
"""

from __future__ import annotations

import os
import tempfile

_real_mkdir = os.mkdir
_real_makedirs = os.makedirs


def _widen(mode: int) -> int:
    # 只处理 0700 这一种：它是 Python 标准库建临时目录时的惯用权限
    return 0o777 if mode == 0o700 else mode


def _permissive_mkdir(path, mode=0o777, *, dir_fd=None):  # type: ignore[no-untyped-def]
    return _real_mkdir(path, _widen(mode), dir_fd=dir_fd)


def _permissive_makedirs(name, mode=0o777, exist_ok=False):  # type: ignore[no-untyped-def]
    return _real_makedirs(name, _widen(mode), exist_ok=exist_ok)


def _permissive_mkdtemp(suffix=None, prefix=None, dir=None):  # type: ignore[no-untyped-def]
    base = dir if dir is not None else tempfile.gettempdir()
    suffix = suffix or ""
    prefix = prefix or tempfile.gettempprefix()
    names = tempfile._get_candidate_names()  # noqa: SLF001 - 本地垫片，允许使用私有 API
    for _ in range(1000):
        path = os.path.join(base, prefix + next(names) + suffix)
        try:
            _real_makedirs(path, 0o777, exist_ok=False)
        except FileExistsError:
            continue
        return path
    raise FileExistsError("could not create a unique temporary directory")


os.mkdir = _permissive_mkdir  # type: ignore[assignment]
os.makedirs = _permissive_makedirs  # type: ignore[assignment]
tempfile.mkdtemp = _permissive_mkdtemp  # type: ignore[assignment]