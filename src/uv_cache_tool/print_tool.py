####################################################################################################
#
# A uv tool to show package size on disk
#   https://github.com/astral-sh/uv/issues/17884
#
# Copyright (C) 2026 Fabrice SALVAIRE
# SPDX-License-Identifier: AGPL-3.0-or-later
#
####################################################################################################

__all__ = ['console', 'human_size']

####################################################################################################

from rich.console import Console

####################################################################################################

console = Console()

####################################################################################################

def human_size(size: int, min_suffix: str = 'M') -> str:
    SUFFIXES = (' ', 'k', 'M', 'G', 'T')
    suffix_index = 0
    _: float = size
    while _ > 1024:
        _ /= 1024
        suffix_index += 1
    if suffix_index >= SUFFIXES.index(min_suffix):
        suffix = SUFFIXES[suffix_index]
        return f'{_:.1f} {suffix}B'
    else:
        suffix = SUFFIXES[suffix_index + 1]
        return f'< {suffix}B'
