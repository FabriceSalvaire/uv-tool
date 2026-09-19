####################################################################################################
#
# A uv tool to show package size on disk
#   https://github.com/astral-sh/uv/issues/17884
#
# Copyright (C) 2026 Fabrice SALVAIRE
# SPDX-License-Identifier: AGPL-3.0-or-later
#
####################################################################################################

__all__ = ['UvCache']

####################################################################################################

import re
from collections.abc import Iterator
from pathlib import Path
from typing import cast

from .path import PathInode, disk_size
from .print_tool import console as C
from .print_tool import human_size

####################################################################################################

CACHE_DIR = Path.home().joinpath('.cache', 'uv')

####################################################################################################

class DirectorySizeMixin:

    ##############################################

    def __init__(self, path: Path) -> None:
        # print(f"Path {path}")
        self.path = path
        self._size: int | None = None  # lazy

    ##############################################

    @property
    def size(self) -> int:
        if self._size is None:
            with C.status(f"Computing {self.path} size..."):
                self._size = disk_size(self.path)
        return self._size

####################################################################################################

class UvCache(DirectorySizeMixin):

    ##############################################

    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.directories: dict[str, UvCacheDirectory] = {}
        for subdir_path in self.yield_subirectories():
            name, _version = self.get_directory_version(subdir_path)
            match name:
                case '.' | '..':
                    pass
                case 'sdists':
                    directory = SDistDirectory(self, subdir_path)
                case 'archive':
                    directory = ArchiveDirectory(self, subdir_path)
                case _:
                    directory = UvCacheDirectory(self, subdir_path)
            self.directories[name] = directory

    ##############################################

    def yield_subirectories(self) -> Iterator[Path]:
        for _ in self.path.iterdir():
            if _.is_dir():
                yield _.relative_to(self.path)

    def get_directory_version(self, path: Path) -> tuple[str, int]:
        name = path.name
        re_match = re.match(r'^([a-z]+)-v(\d+)$', name)
        if re_match is not None:
            name, _ = re_match.groups()
            return name, int(_)
        raise ValueError(f"Invalid directory name {name}")

    ##############################################

    @property
    def sdists_directory(self) -> SDistDirectory:
        return cast(SDistDirectory, self.directories['sdists'])

    @property
    def archive_directory(self) -> ArchiveDirectory:
        return cast(ArchiveDirectory, self.directories['archive'])

    ##############################################

    def list(self) -> None:
        def print_directory(directory: Bucket) -> None:
            for package in directory:
                C.print(f"[blue]{package.name}")
                for version in package:
                    path = str(version.path.relative_to(CACHE_DIR))
                    nlink = version.nlink if isinstance(version, ArchivePackage) else '---'
                    C.print(f"  v{version.version:<24} @{version.py_version}   {path:<30}  #{nlink}")

        C.rule()
        C.print("[red]SDist Packages")
        print_directory(self.sdists_directory)
        C.rule()
        C.print("[red]Packages")
        print_directory(self.archive_directory)

    ##############################################

    def compute_size(self, min_size: int = 0) -> None:
        C.print(f"UV Cache is: {CACHE_DIR}   {human_size(self.size)}")
        for _ in self.directories.values():
            C.print(f"  {_.path.name:16} {human_size(_.size):>10}")

        def sort_key_by_name(_: Package) -> str:
            return _.name

        def sort_key_by_size(_: Package) -> int:
            return _.size

        def print_directory(directory: Bucket) -> None:
            sort_key = sort_key_by_size
            packages = sorted(directory, key=sort_key)
            for package in packages:
                size = package.size
                if size < min_size:
                    continue
                C.print(f"[blue]{package.name:<28} {human_size(size):>10}")
                for package_version in cast(Iterator[SdistPackage], package):
                    version = package_version.version
                    py_version = str(package_version.py_version)
                    size = package_version.size
                    path = package_version.path.relative_to(CACHE_DIR)
                    C.print(f"  v{version:<12} @{py_version:<8} {human_size(size):>13}   {path}")

        C.rule()
        C.print("[red]SDist Packages")
        print_directory(self.sdists_directory)
        C.rule()
        C.print("[red]Packages")
        print_directory(self.archive_directory)

####################################################################################################

class UvCacheDirectory(DirectorySizeMixin):

    ##############################################

    def __init__(self, uv_cache: UvCache, path: Path | str) -> None:
        self.uv_cache = uv_cache
        super().__init__(self.uv_cache.path / path)

    ##############################################

    @property
    def name(self) -> str:
        return self.path.name

####################################################################################################

class Bucket(UvCacheDirectory):

    ##############################################

    def __init__(self, uv_cache: UvCache, path: Path | str) -> None:
        super().__init__(uv_cache, path)
        self.packages: dict[str, Package] = {}
        self._scan()

    ##############################################

    def _scan(self) -> None:
        with C.status(f"Scanning {self.path}..."):
            for package in self._get_packages():
                self.packages.setdefault(package.name, Package(package.name)).add_version(package)

    ##############################################

    def _get_packages(self) -> list[PackageVersion]:
        raise NotImplementedError

    ##############################################

    def __iter__(self) -> Iterator[Package]:
        return iter(sorted(self.packages.values(), key=lambda _: _.name))

####################################################################################################

class ArchiveDirectory(Bucket):

    ##############################################

    def _get_packages(self) -> list[PackageVersion]:
        return [ArchivePackage(_) for _ in self.path.iterdir() if _.is_dir()]

####################################################################################################

class SDistDirectory(Bucket):

    ##############################################

    def _get_packages(self) -> list[PackageVersion]:
        # Fixme: bucket: editable git path
        return [
            SdistPackage(version)
            for package in (self.path / 'pypi').iterdir()
            for version in package.iterdir()
        ]

####################################################################################################

class PackageVersion(DirectorySizeMixin):

    ##############################################

    def __init__(self, path: Path, name: str, version: str) -> None:
        super().__init__(path)
        self.name = name
        self.version = version
        self.py_version: str | None = self._get_py_version()

    ##############################################

    def _get_py_version(self) -> str | None:
        return None

####################################################################################################

class Package:

    ##############################################

    def __init__(self, name: str) -> None:
        self.name = name
        self._versions: list[PackageVersion] = []

    ##############################################

    def __len_(self) -> int:
        return len(self._versions)

    def __iter__(self) -> Iterator[PackageVersion]:
        return iter(sorted(self._versions, key=lambda _: f'{_.version}-{_.py_version}'))

    ##############################################

    def add_version(self, version: PackageVersion) -> None:
        self._versions.append(version)

    ##############################################

    @property
    def versions(self) -> list[str]:
        return [_.version for _ in self]

    @property
    def versions_count(self) -> list[tuple[str, int]]:
        versions = self.versions
        return [(_, versions.count(_)) for _ in set(versions)]

    @property
    def size(self) -> int:
        return sum(_.size for _ in self._versions)

####################################################################################################

class ArchivePackage(PackageVersion):
    """Implements a Python Package"""

    # archive-v0/uuid/
    #   package/
    #   package-version.data/
    #   package-version.dist-info/

    ##############################################

    @classmethod
    def _get_name_version(cls, path: Path) -> tuple[str, str]:
        # Get package name and version from name-version.dist-info filename
        # Fixme:
        name = ''
        version = ''
        name_version = None
        SUFFIX = '.dist-info'
        for _ in path.iterdir():
            name = _.name
            if name.endswith(SUFFIX):
                name_version = name[:-len(SUFFIX)]
        if name_version is not None:
            i = name_version.rfind('-')
            if i != -1:
                name = name_version[:i]
                version = name_version[i + 1:]
            else:
                C.print(f"[red]WARNING: unsupported version for {path}")
        else:
            # Fixme:
            #   /home/fabrice/.cache/uv/archive-v0/jnmE0T_XlOGz8rOhVrFja/bin/python3.13
            C.print(f"[red]WARNING: dist-info not found for {path}")
        if not (name and version):
            raise ValueError(f"Cannot retrieve name and version for {path}")
        return name, version

    ##############################################

    def __init__(self, path: Path) -> None:
        # get version and name
        # Register to VERSION_MAP
        name, version = self._get_name_version(path)
        super().__init__(path, name, version)
        self._nlink: int | None = None  # lazy

    ##############################################

    def _get_py_version(self) -> str | None:
        SUFFIX = '.so'
        so_file = None
        for _root, _dirnames, filenames in self.path.walk():
            for filename in filenames:
                if filename.endswith(SUFFIX):
                    so_file = filename
                    break
        if so_file is not None:
            match = re.match(r'^.*\.cpython-(\d\d\d)-', so_file)
            if match:
                _ = match.group(1)
                return f'{_[0]}.{_[1:3]}'
        return None

    ##############################################

    # hardlink_count
    @property
    def nlink(self) -> int:
        if self._nlink is None:
            path = self.path / (self.name + '.py')
            if not path.exists():
                path = self.path / self.name / '__init__.py'
            if not path.exists():
                path = self.path / f'{self.name}-{self.version}.dist-info/METADATA'
            return PathInode(path).nlink
        return self._nlink

    ##############################################

    def __repr__(self) -> str:
        return f"Archive Package {self.name} - {self.version}"

####################################################################################################

class SdistPackage(PackageVersion):
    """Implements a Python Package"""

    # /package_name/version/uuid/
    #   package-version-cp315-cp315-linux_x86_64 symlink to archive-v0/uuid
    #   package-version-cp315-cp315-linux_x86_64.whl
    #   src

    ##############################################

    def __init__(self, path: Path) -> None:
        name = path.parent.name
        version = path.name
        super().__init__(path, name, version)

    ##############################################

    def _get_py_version(self) -> str | None:
        SUFFIX = '.whl'
        wheel = None
        for _root, _dirnames, filenames in self.path.walk():
            for filename in filenames:
                if filename.endswith(SUFFIX):
                    wheel = filename
                    break
        if wheel is not None:
            match = re.match(r'^.*-cp(\d\d\d)-', wheel)
            if match:
                _ = match.group(1)
                return f'{_[0]}.{_[1:3]}'
        return None

    ##############################################

    def __repr__(self) -> str:
        return f"Sdist Package {self.name} - {self.version} - {self.py_version}"
