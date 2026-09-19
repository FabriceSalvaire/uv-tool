####################################################################################################
#
# A uv tool to show package size on disk
#   https://github.com/astral-sh/uv/issues/17884
#
# Copyright (C) 2026 Fabrice SALVAIRE
# SPDX-License-Identifier: AGPL-3.0-or-later
#
####################################################################################################

__all__ = ['VenvFinder', 'Project', 'Dependency']

####################################################################################################

import json
import subprocess
from pathlib import Path

from .print_tool import console as C

# from .print_tool import human_size

####################################################################################################


TO_UPDATE = [
    'invoke',
    'ipython',
    'pyyaml',
    'rassumfrassum',
    'rich',
    'ruff',
    'ty',
    'uv_build',
    'requests',
]

####################################################################################################

class VenvFinder:

    ##############################################

    def __init__(self, path: Path | str, max_py: int) -> None:
        path = Path(path)
        self._max_py = max_py
        self._paths: list[Path] = []
        if path.is_dir():
            self._find(path)
        else:
            self.load_paths(path)
            for _ in self._paths:
                self.on_venv(_)

    ##############################################

    def save_paths(self, path: Path | str) -> None:
        path = Path(path)
        data = {
            'paths': sorted([str(_) for _ in self._paths])
        }
        path.write_text(json.dumps(data, indent=True))

    ##############################################

    def load_paths(self, path: Path | str) -> None:
        path = Path(path)
        C.print(f"Load {path}")
        data = json.loads(path.read_text())
        self._paths = [Path(_) for _ in data['paths']]

    ##############################################

    def _find(self, path: Path) -> None:
        with C.status(f"Searching .venv in {path}..."):
            for root, dirnames, _filenames in path.walk():
                match root.name:
                    case '.pycache':
                        dirnames.clear()
                    case '.venv':
                        _ = root.parent
                        self._paths.append(_)
                        self.on_venv(_)
                    case _:
                        if root.name.startswith('.pycache'):
                            dirnames.clear()
            dirnames.sort()  # Fixme: unicode

    ##############################################

    def on_venv(self, path: Path) -> None:
        # self._paths.append(path)
        project = Project(path)
        if project.py_version_int <= self._max_py:
            C.rule()
            C.print(path)
            C.print(f"  Python version is {project.py_version}")
            for dependency in sorted(project.dependencies, key=lambda _: _.name):
                C.print(f"  {dependency}")
                if dependency.latest is not None and dependency.name in TO_UPDATE:
                    dependency.update_to_latest()

####################################################################################################

class Dependency:

    ##############################################

    def __init__(self, project: Project, name: str, version: str, tail: str) -> None:
        self.project = project
        self.name = name
        self.version = version
        self.tail = tail

        self.latest: str | None = None
        self.group: str | None = None
        if tail:
            parts = [
                _.replace('(', '').replace(')', '')
                for _ in tail.split(') (')
            ]
            for part in parts:
                if ':' in part:
                    key, value = part.split(': ')
                    setattr(self, key, value)

    ##############################################

    def __repr__(self) -> str:
        color = 'red' if self.latest is not None else 'green'
        return f"[{color}]{self.name}[/] - {self.version} - {self.tail}"

    ##############################################

    def update_to_latest(self) -> None:
        C.print(f"    [red]update[/] {self.name}")
        # uv sync --upgrade-package
        group = '--dev' if self.group == 'dev' else ''
        cmd = f'uv add {group} {self.name}=={self.latest}'
        # f'uv tree -P {self.name}',
        # f'uv sync --upgrade-package {self.name}',
        C.print(f"    {cmd}")
        # try:
        process = subprocess.run(
            cmd,
            shell=True,
            cwd=self.project.path,
            # check=True,
            capture_output=True,
        )
        for _ in (process.stdout, process.stderr):
            C.print(_.decode('utf8'))
        # except subprocess.CalledProcessError:
        #     pass

####################################################################################################

class Project:

    ##############################################

    def __init__(self, path: Path) -> None:
        self.path = path
        self.dependencies: list[Dependency] = []

        try:
            _ = (path / '.python-version').read_text().strip()
            pattern = '/python'
            i = _.find(pattern)
            if i != -1:
                _ = _[i + len(pattern):]
            self.py_version = _
        except FileNotFoundError:
            self.py_version = None

        # 'uv.lock'
        process = subprocess.run(
            'uv tree --outdated',
            shell=True,
            cwd=path,
            check=True,
            capture_output=True,
        )
        stdout = process.stdout.decode('utf8')
        for line in stdout.splitlines():
            if line[0] in '├└─':
                _, name, version, *tail = line.split(' ')
                _ = Dependency(self, name, version, ' '.join(tail))
                self.dependencies.append(_)

    ##############################################

    @property
    def py_version_int(self) -> int:
        _ = self.py_version
        if _:
            return int(_[0] + _[2:])
        else:  # Fixme:
            return 0
