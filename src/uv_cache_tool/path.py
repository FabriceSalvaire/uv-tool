####################################################################################################
#
# A uv tool to show package size on disk
#   https://github.com/astral-sh/uv/issues/17884
#
# Copyright (C) 2026 Fabrice SALVAIRE
# SPDX-License-Identifier: AGPL-3.0-or-later
#
####################################################################################################

__all__ = ['PathInode', 'disk_size']

####################################################################################################

import os
from pathlib import Path

####################################################################################################

class PathInode:
    """Convenient class to information like disk usage for a path."""

    ##############################################

    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        self._stat: os.stat_result | None = None  # lazy

    ##############################################

    def __str__(self) -> str:
        return str(self._path)

    ##############################################

    @property
    def stat(self) -> os.stat_result:
        if self._stat is None:
            # self._stat = self._path.stat(follow_symlinks=False)
            self._stat = os.lstat(str(self._path))
        return self._stat

    ##############################################

    @property
    def inode(self) -> int:
        return self.stat.st_ino

    ##############################################

    @property
    def nlink(self) -> int:
        return self.stat.st_nlink

    @property
    def is_hardlink(self) -> bool:
        return self.nlink > 1

    ##############################################

    @property
    def disk_size(self) -> int:
        # size += _.stat().st_size
        # allocated
        return self.stat.st_blocks * 512

####################################################################################################

def disk_size(path: Path) -> int:
    """Return the disk size of path in bytes.

    Hardlinked inodes are counted once.

   """
    size = 0
    inodes: set[int] = set()

    def accumulate(path: Path) -> None:
        file = PathInode(path)
        inode = file.inode
        if inode not in inodes:
            nonlocal size
            size += file.disk_size
        # else:
        #     C.print(f"hardlink duplicate {file}")
        inodes.add(inode)

    accumulate(path)
    for root, dirnames, filenames in path.walk():
        for item in (dirnames, filenames):
            for _ in item:
                accumulate(root / _)
    return size
