import collections
import os
from enum import Enum
from typing import Any, Generic, List, TypeVar


class LogLevel(Enum):
    """
    Enum indicating the different valid log levels when logging messages to an
    emitter.

    .. autoattribute:: DEBUG
    .. autoattribute:: PROCEDURE
    .. autoattribute:: INFO
    .. autoattribute:: SKIP
    .. autoattribute:: SUCCESS
    .. autoattribute:: ERROR
    .. autoattribute:: FAIL
    .. autoattribute:: CATASTROPHIC
    """

    #: Messages meant to provide deeper insight that isn't always necessary
    DEBUG = "debug"

    #: Messages pertaining to the traversal procedure
    PROCEDURE = "procedure"

    #: Informational messages about what's happening in the task
    INFO = "info"

    #: Message indicating text related to a task skip
    SKIP = "skip"

    #: Message indicating some level of success
    SUCCESS = "success"

    #: Something unexpected happened which may not be recoverable
    ERROR = "error"

    #: A specific condition in the task has failed and is likely recoverable
    FAIL = "fail"

    #: Something unrecoverrable happened that requires human attention
    CATASTROPHIC = "catastrophic"


T = TypeVar("T")


class Emitter(Generic[T]):
    """
    An emitter is an abstraction that exists to determine how various debug
    information is to be passed on to the user. This is done through the
    various hooks that are required to be implememented.

    .. attribute:: tasks

        :var:`T`\\s run under this emitter

    .. attribute:: context_level

        `int` context level starting from 0

    .. automethod:: subcontext
    .. automethod:: pop_subcontext
    .. automethod:: log_message
    .. automethod:: log_file
    .. automethod:: finalize
    """

    tasks: collections.OrderedDict[T, None]

    #: Context level starting from 0
    context_level: int

    def __init__(self):
        self.context_level = 0

    def start_task(self, instance: T) -> None:
        """
        Hook that exists to inject some behavior in event of a new test
        *instance* starting.
        """
        self.tasks[instance] = None

    def end_task(self, instance: T) -> None:
        """
        Hook that exists to inject some behavior in event of a new test
        *instance* ending.
        """

    def subcontext(self) -> None:
        """
        Enter into a new subcontext. The idea behind this method is to allow
        emitters to nest output inside of other output in an effort to be able
        to collapse and expand text information.

        If overridden by a subclass, be sure to call this original method
        to retain the default functionality.
        """
        self.context_level += 1

    def pop_subcontext(self, context_level: int) -> None:
        """
        Pop subcontext to the given *context_level*, which starts from 0 before
        the first :meth:`subcontext` call.

        If overridden by a subclass, be sure to call this original method
        to retain the default functionality.
        """
        self.context_level = context_level

    def log_message(self, log_level: LogLevel, message: str, end: str = "\n") -> None:
        """
        Log the given *message* at the given *log_level*. If a multi-line
        message is given, it's expected to be handled appropriately by the
        emitter.
        """

    def log_file(self, description: str, extension: str, mode: str = "w") -> Any:
        """
        Create a file object with the given *description* and file *extension*.
        This object will be used by the caller. It's up to the caller to close
        it when done.
        """
        return open(os.devnull, mode)

    def finalize(self):
        """
        Hook for finalizing the emitter in case there's something that needs to
        be cleaned up.
        """
