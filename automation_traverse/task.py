"""
module pertaining to individual tasks
"""

import ast
import collections
import datetime
import pdb
import traceback
from typing import Any, Callable, Dict, List, Mapping, Set, Union

from automation_entities.context import patch_dict

from .asserter import DictAsserter
from .context import TraverseContext
from .emitters import Emitter, LogLevel

RUN_SKIP = LogLevel.SKIP
RUN_SUCCESS = LogLevel.SUCCESS
RUN_FAIL = LogLevel.FAIL
RUN_ERROR = LogLevel.ERROR
RUN_CATASTROPHIC = LogLevel.CATASTROPHIC


class gather_debug:
    """
    descriptor/decorator used to denote a method that is necessary to run
    before teardown in the event the run fails
    """

    def __init__(self, fcn):
        self.fcn = fcn

    def __get__(self, obj, type_=None):
        if obj is None:
            return self

        return self.fcn.__get__(obj, type_)

    def __call__(self, obj, *args, **kwds):
        return self.fcn.__get__(obj, type(obj))(*args, **kwds)


class TaskSkip(Exception):
    """
    exception to raise to skip a task
    """


class TaskMeta(type):
    """
    metaclass for :class:`Task` that preprocesses them to include
    information from their superclasses
    """

    def __new__(cls, name, bases, attrs):
        debug_fcns = set()
        parents = []
        arguments = {}
        config_defaults = {}
        presented_attrs = set()
        if name != "Task":
            for base in bases:
                if not issubclass(base, Task):
                    continue

                parents.append(base)
                patch_dict(arguments, base.ARGUMENTS)
                patch_dict(config_defaults, base.CONFIG_DEFAULTS)
                presented_attrs |= set(base.PRESENTED_ATTRS)
                debug_fcns |= set(base.DEBUG_FCNS)

        patch_dict(arguments, attrs.get("ARGUMENTS", {}))
        patch_dict(config_defaults, attrs.get("CONFIG_DEFAULTS", {}))
        presented_attrs |= set(attrs.get("PRESENTED_ATTRS", []))

        for attr in attrs.values():
            if isinstance(attr, gather_debug):
                debug_fcns.add(attr)

        attrs["DEBUG_FCNS"] = debug_fcns
        attrs["PARENTS"] = parents
        attrs["ARGUMENTS"] = arguments
        attrs["CONFIG_DEFAULTS"] = config_defaults
        attrs["PRESENTED_ATTRS"] = sorted(presented_attrs)
        attrs["SETUP_DEFINED"] = "setup" in attrs
        attrs["RUN_DEFINED"] = "run" in attrs

        for attr in presented_attrs:
            if attr not in attrs:
                attrs[attr] = None

        return type.__new__(cls, name, bases, attrs)


class Task(object, metaclass=TaskMeta):
    """
    Task is the base class of all tasks cases using the traverse task engine.
    When defining a Task, you can optionally define any of the following:

    .. autoattribute:: DISCOVER
    .. autoattribute:: ARGUMENTS
    .. autoattribute:: CONFIG_DEFAULTS
    .. autoattribute:: PRESENTED_ATTRS

    For the :attr:`DISCOVER` attribute, this value should be set to ``True``
    if the task should be discovered as runnable. Base classes that merely
    provide setup to use an entity should have this value set to ``False``.

    The :attr:`ARGUMENTS` attribute should be a flat ``dict`` mapping argument
    keys to argument types. Each value should only be a numerical, boolean,
    string, or None type.

    The :attr:`CONFIG_DEFAULTS` attribute defines configuration values that
    are required to run this task with their associated default values. This
    ``dict`` will have the loaded configuration patched on top of it.

    The :attr:`PRESENTED_ATTRS` attribute defines attributes created during
    the :meth:`setup` method. When running tasks as a graph, each parent node
    will be run in turn, and its presented attributes will be transferred to
    its child nodes. In this way, we can retain the work done by the parent
    node during its setup.

    .. attribute:: args

        ``dict`` arguments for task

    .. attribute:: teardown_stack

        :class:`collections.deque` stack representing all teardowns

    .. automethod:: get_config
    .. automethod:: set_config_filepath
    .. automethod:: assert_dict
    .. automethod:: setup
    .. automethod:: run
    .. automethod:: teardown
    .. automethod:: add_teardown
    .. automethod:: teardown_to_function
    .. automethod:: add_emitter
    .. automethod:: patch_attrs
    .. automethod:: execute_run
    .. automethod:: execute_teardown
    .. automethod:: execute
    .. automethod:: clone
    """

    #: whether or not this task should be discoverable and runnable
    DISCOVER: bool = False

    #: arguments that this task takes unique from any of its parents
    ARGUMENTS: Dict[str, Union[int, float, bool, str, None]] = {}

    #: default configuration to be applied to this task unique from any of its parents
    CONFIG_DEFAULTS: Mapping[str, Any] = {}

    #: attributes presented to subclasses (anything created during setup)
    PRESENTED_ATTRS: List[str] = []

    # These values are set by TaskMeta and should not be overwritten by the
    # user.
    SETUP_DEFINED = False
    RUN_DEFINED = False
    PARENTS: List[type] = []
    DEBUG_FCNS: Set[gather_debug] = set()

    def __init__(self, *args, **kwds):
        self.args = None
        if args:
            self.args = args[0]

        else:
            self.args = kwds

        self.teardown_stack = collections.deque()
        self.context = TraverseContext(config_defaults=self.CONFIG_DEFAULTS)
        self.start_time = None
        self.time_taken = datetime.timedelta()
        self.error = None
        self.error_text = None
        self.status = None
        self.config = None

    def get_config(self, key: str, skip_empty: bool = True) -> Any:
        """
        get the given configuration *key*, which is a dot-separated list
        of the path to the desired configuration field (eg. val1.val2.val3)
        """
        toks = key.split(".")
        parent = self.config
        for tok in toks:
            if tok not in parent:
                if skip_empty:
                    raise TaskSkip(f"config value {key} not found")

                return None

            parent = parent[tok]
            if parent is None:
                if skip_empty:
                    raise TaskSkip(f"config value {key} not found")

                return None

        return parent

    def set_config_filepath(self, filepath: str) -> None:
        """
        set config file to the given *filepath*
        """
        self.context.set_config_file(filepath)
        self.config = self.context.config

    def assert_dict(self, val: dict) -> DictAsserter:
        """
        wrap the given *val* with a :class:`DictAsserter`
        """
        return DictAsserter(self.context, val)

    def setup(self) -> None:
        """
        set up the task
        """
        pass

    def run(self) -> None:
        """
        execute the task
        """
        pass

    def teardown(self) -> None:
        """
        teardown the task
        """
        while self.teardown_stack:
            self.teardown_stack.pop()()

    def add_teardown(self, fcn) -> None:
        """
        add a teardown to run; to add arguments to the callback, use
        :class:`functools.partial`
        """
        self.teardown_stack.append(fcn)
        return fcn

    def teardown_to_function(self, fcn: Callable) -> None:
        """
        teardown to the given function
        """
        while self.teardown_stack:
            curr_fcn = self.teardown_stack.pop()
            curr_fcn()

            if curr_fcn == fcn:
                return

        raise AssertionError(f"function {fcn} not found")

    def add_emitter(self, emitter: Emitter) -> None:
        """
        add a new *emitter* to the context
        """
        self.context.add_emitter(emitter)

    def patch_attrs(self, new_attrs) -> None:
        """
        patch instance's attrs with *new_attrs*
        """
        for name, attr in new_attrs.items():
            if hasattr(attr, "context"):
                attr.__setattr__("context", self.context)

            self.__setattr__(name, attr)

    def execute_run(self, debug: bool = False) -> None:
        """
        execute the task's setup and run only
        """
        self.start_time = datetime.datetime.now()
        try:
            if self.SETUP_DEFINED:
                with self.context.subcontext(
                    f"setup {self}", log_level=LogLevel.PROCEDURE
                ):
                    self.setup()

            if self.RUN_DEFINED:
                with self.context.subcontext(
                    f"run {self}", log_level=LogLevel.PROCEDURE
                ):
                    self.run()

        except TaskSkip as err:
            self.status = RUN_SKIP
            self.error = err
            self.error_text = traceback.format_exc()
            self.context.log_skip(self.error_text)

        except AssertionError as err:
            self.status = RUN_FAIL
            self.error = err
            self.error_text = traceback.format_exc()
            self.context.log_fail(self.error_text)

            if debug:
                pdb.post_mortem()

        except Exception as err:
            self.status = RUN_ERROR
            self.error = err
            self.error_text = traceback.format_exc()
            self.context.log_error(self.error_text)

            if debug:
                pdb.post_mortem()

        if self.DEBUG_FCNS and self.status is not None:
            try:
                for fcn in self.DEBUG_FCNS:
                    with self.context.subcontext(
                        f"gather_debug {self} {fcn.fcn.__qualname__}",
                        log_level=LogLevel.PROCEDURE,
                    ):
                        fcn(self)

            except Exception as err:
                self.context.log_error(traceback.format_exc())
                if debug:
                    pdb.post_mortem()

        self.time_taken += datetime.datetime.now() - self.start_time

    def execute_teardown(self, debug=False):
        """
        execute the tests's teardown only
        """
        start_time = datetime.datetime.now()
        try:
            if self.teardown_stack:
                with self.context.subcontext(
                    f"teardown {self}", log_level=LogLevel.PROCEDURE
                ):
                    self.teardown()

        except Exception as err:
            self.status = RUN_CATASTROPHIC
            self.error = err
            self.error_text = traceback.format_exc()
            self.context.log_catastrophic(self.error_text)

            if debug:
                pdb.post_mortem()

        if self.status is None:
            self.status = RUN_SUCCESS

        self.context.log_procedure(f"finished {self} - {self.status}")
        self.time_taken += datetime.datetime.now() - start_time

    def execute(self, debug=False):
        """
        Execute the test. If *debug* is set, drop into pdb post-mortem shell
        on failure.
        """
        self.execute_run(debug=debug)
        self.execute_teardown(debug=debug)
        return self.status

    def clone(self):
        """
        clone this instance
        """
        return self.__class__(self.args)

    def __str__(self):
        arg_str = ",".join(f"{k}={repr(v)}" for k, v in self.args.items())
        return f"{self.__class__.__name__}({arg_str})"

    def __repr__(self):
        return self.__str__()


def args_from_str(string):
    """
    Generate a ``dict`` of arguments from the given string.
    """
    args = {}
    if string:
        for pair in string.split(","):
            toks = pair.split("=", 1)
            if len(toks) != 2:
                return None

            args[toks[0]] = ast.literal_eval(toks[1])

    return args
