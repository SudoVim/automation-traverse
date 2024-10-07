from typing import IO, Any, Dict, Generic, List, Optional, Type

from automation_entities.context import Context, Subcontext
from typing_extensions import override

from .emitters import Emitter, LogLevel, T


class TraverseContext(Context, Generic[T]):
    """
    :class:`automation_entities.context.Context` that supports multiple
    :class:`Emitter` s.
    """

    emitters: List[Emitter[T]]

    def __init__(
        self,
        config_defaults: Optional[  # pyright: ignore[reportUnknownParameterType]
            dict  # pyright: ignore[reportMissingTypeArgument]
        ] = None,
        subcontext_class: Optional[Type[Subcontext]] = None,
    ):
        super().__init__(  # pyright: ignore[reportUnknownMemberType]
            config_defaults, subcontext_class
        )

        self.emitters = []

    def add_emitter(self, emitter: Emitter[T]) -> None:
        """
        Add the given *emitter* to the :attr:`emitters` list.
        """
        self.emitters.append(emitter)

    @override
    def subcontext(
        self, message: str, log_level: LogLevel = LogLevel.INFO
    ) -> "TraverseSubcontext[T]":
        """
        subcontext implementation that creates a :class:`TraverseSubcontext`
        subcontext rather than the original.
        """
        for emitter in self.emitters:
            emitter.log_message(log_level, message)

        return TraverseSubcontext(self, self)

    def pop_subcontext(self, context_level: int) -> None:
        """
        Pop all emitters back to the given *context_level*.
        """
        for emitter in self.emitters:
            emitter.pop_subcontext(context_level)

    @override
    def log(self, message: str) -> None:
        """
        Log the given *message* as info.
        """
        self.log_info(message)

    def log_file(
        self, description: str, extension: str, mode: str = "w"
    ) -> "TraverseFile":
        """
        Log the given *description* and create a file of the given *extension*
        and *mode*.
        """
        return TraverseFile(
            [e.log_file(description, extension, mode) for e in self.emitters],
        )

    def log_message(self, log_level: LogLevel, message: str) -> None:
        """
        Log the given *message* at the given *log_level* to all configured
        emitters. For more information on *log_level*, see
        :meth:`emitters.Emitter.log_message`.
        """
        for emitter in self.emitters:
            emitter.log_message(log_level, message)

    def log_debug(self, message: str) -> None:
        """
        log the given *message* at debug level.
        """
        self.log_message(LogLevel.DEBUG, message)

    def log_procedure(self, message: str) -> None:
        """
        log the given *message* at procedure level.
        """
        self.log_message(LogLevel.PROCEDURE, message)

    def log_info(self, message: str) -> None:
        """
        log the given *message* at info level.
        """
        self.log_message(LogLevel.INFO, message)

    def log_skip(self, message: str) -> None:
        """
        log the given *message* at skip level.
        """
        self.log_message(LogLevel.SKIP, message)

    def log_success(self, message: str) -> None:
        """
        log the given *message* at success level.
        """
        self.log_message(LogLevel.SUCCESS, message)

    def log_error(self, message: str) -> None:
        """
        log the given *message* at error level.
        """
        self.log_message(LogLevel.ERROR, message)

    def log_fail(self, message: str) -> None:
        """
        log the given *message* at fail level.
        """
        self.log_message(LogLevel.FAIL, message)

    def log_catastrophic(self, message: str) -> None:
        """
        log the given *message* at catastrophic level.
        """
        self.log_message(LogLevel.CATASTROPHIC, message)

    def log_response(self, task: T, response: Dict[str, Any]) -> None:
        """
        log the given *response* for the given *task*
        """
        for emitter in self.emitters:
            emitter.log_response(task, response)


class TraverseSubcontext(Subcontext, Generic[T]):
    """
    :class:`automation_entities.context.Subcontext` that supports multiple
    :class:`automation_traverse.emitters.Emitter` s.
    """

    tranverse_context: "TraverseContext[T]"

    def __init__(self, context: "Context", tranverse_context: "TraverseContext[T]"):
        super().__init__(context)

        self.tranverse_context = tranverse_context

    @override
    def __enter__(self) -> "TraverseSubcontext[T]":
        _ = super().__enter__()

        for emitter in self.tranverse_context.emitters:
            emitter.subcontext()

        return self

    @override
    def __exit__(self, *args: Any, **kwds: Any) -> None:
        super().__exit__(*args, **kwds)  # pyright: ignore[reportUnknownMemberType]

        self.tranverse_context.pop_subcontext(self.tranverse_context.log_position)


class TraverseFile:
    """
    File-like object that multiplexes multiple file-like objects into one
    object.

    .. autoattribute:: fobjs
    """

    #: file objects wrapped by this class
    fobjs: List[IO[str]]

    def __init__(self, fobjs: List[IO[str]]) -> None:
        self.fobjs = fobjs

    def __enter__(self) -> "TraverseFile":
        return self

    def __exit__(self, *args: Any, **kwds: Any) -> None:
        self.close()

    def write(self, data: str) -> int:
        """
        Write *data* to all :attr:`fobjs`
        """
        if not self.fobjs:
            return len(data)

        return min(fobj.write(data) for fobj in self.fobjs)

    def close(self) -> None:
        """
        Close all :attr:`fobjs`
        """
        for fobj in self.fobjs:
            fobj.close()
