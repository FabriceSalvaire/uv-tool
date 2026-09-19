####################################################################################################
#
# A uv tool to show package size on disk
#   https://github.com/astral-sh/uv/issues/17884
#
# Copyright (C) 2026 Fabrice SALVAIRE
# SPDX-License-Identifier: AGPL-3.0-or-later
#
####################################################################################################

__all__ = ['main']

####################################################################################################

import argparse
import re
import subprocess
from pathlib import Path

from .uv_cache import UvCache
from .venv import VenvFinder

####################################################################################################

CACHE_DIR = Path.home().joinpath('.cache', 'uv')

####################################################################################################

def list_command() -> None:
    uv_cache = UvCache(CACHE_DIR)
    uv_cache.list()

####################################################################################################

def cache_size_command(prune: bool, min_size: int) -> None:
    # use shell to find uv
    if prune:
        subprocess.check_call('uv cache prune', shell=True)

    uv_cache = UvCache(CACHE_DIR)
    uv_cache.compute_size(min_size)

####################################################################################################

def find_venv_command(path: Path | str, max_py: int) -> None:
    path = Path(path)
    _finder = VenvFinder(path, max_py)
    # finder.save_paths('venv-list.json')

####################################################################################################

def main() -> None:
    parser = argparse.ArgumentParser(
        prog='uv-cache-tool',
        description='',
        epilog='',
    )
    parser.add_argument(
        '--list',
        action='store_true',
    )
    parser.add_argument(
        '--cache-size',
        action='store_true',
    )
    parser.add_argument(
        '--find-venv',
    )
    parser.add_argument(
        '--min-size',
        default=None,
        type=str,
    )
    parser.add_argument(
        '--max-py',
        default=400,
        type=int,
    )
    args = parser.parse_args()

    ####################################################################################################

    # Fixme: better ?
    if args.list:
        list_command()
    elif args.cache_size:
        min_size_str = args.min_size
        if min_size_str is None:
            min_size = 0
        else:
            re_match = re.match(r'(\d+)(MB|GB)', min_size_str)
            if re_match:
                value = int(re_match.group(1))
                match re_match.group(2):
                    case 'MB':
                        min_size = value * 1024**2
                    case 'GB':
                        min_size = value * 1024**3
            else:
                raise ValueError(f"invalid value {min_size_str}")
        cache_size_command(prune=False, min_size=min_size)
    elif args.find_venv:
        find_venv_command(args.find_venv, args.max_py)
    else:
        parser.print_help()
