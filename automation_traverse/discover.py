"""
module for discovering objects in Python
"""

import importlib.util
import os
from types import ModuleType
from typing import Any, Dict, Iterator, Tuple, Type

from .task import Task

ImportedModuleKey = Tuple[str, str]

imported_modules: Dict[ImportedModuleKey, ModuleType] = {}


def import_module(pypath: str, filepath: str) -> ModuleType:
    """
    Import and return the module at the given *pypath* and *filepath*
    """
    key = (pypath, filepath)
    if key not in imported_modules:
        spec = importlib.util.spec_from_file_location(pypath, filepath)
        if spec is None or spec.loader is None:
            raise ValueError(f"module {key} not found")

        new_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(new_module)
        imported_modules[key] = new_module

    return imported_modules[key]


def walk_modules(start_point: str) -> Iterator[Tuple[str, ModuleType]]:
    """
    walk over all modules from the given *start_point*
    """
    start_point = os.path.abspath(start_point)
    for root, _, files in os.walk(start_point):
        relpath = os.path.relpath(root, os.path.dirname(start_point))
        module_path = tuple(relpath.split(os.path.sep))

        for fname in files:
            if fname == "__init__.py":
                filepath = os.path.join(root, fname)
                pypath = ".".join(module_path)
                new_module = import_module(pypath, filepath)
                yield pypath, new_module

            elif fname.endswith("__.py"):
                continue

            elif fname.endswith(".py"):
                filepath = os.path.join(root, fname)
                pypath = ".".join(module_path + (fname[:-3],))
                new_module = import_module(pypath, filepath)
                yield pypath, new_module


def walk_object(obj: Any) -> Iterator[Any]:
    """
    Walk over the given object for its members
    """
    for attr in dir(obj):
        yield attr, obj.__getattribute__(attr)


def walk_tasks(
    start_point: str,
    discover_all: bool = False,
) -> Iterator[Tuple[str, str, Type[Task]]]:
    """
    Walk over a module and return its tasks

    :param bool discover_all: whether or not to discover tasks not marked
        as discoverable
    """
    for modulepath, module in walk_modules(start_point):
        for objname, obj in walk_object(module):
            if (
                isinstance(obj, type)
                and issubclass(obj, Task)
                and (discover_all or obj.DISCOVER)
            ):
                yield modulepath, objname, obj
