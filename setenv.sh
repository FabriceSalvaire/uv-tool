# PYTHONPYCACHEPREFIX
#   If this is set, Python will write .pyc files in a mirror directory tree at this path,
#   instead of in __pycache__ directories within the source tree.
#   This is equivalent to specifying the -X pycache_prefix=PATH option.
export PYTHONPYCACHEPREFIX=$PWD/.pycache

source .venv/bin/activate

append_to_python_path_if_not $PWD/src
