import io
import pprint
import sys
from typing import Any, Dict, Optional, TextIO, Union

from typing_extensions import override

from .emitter import LogLevel, T
from .simple_log import SimpleLogEmitter


class TerminalEmitter(SimpleLogEmitter[T]):
    """
    :class:`SimpleLogEmitter` implementation that logs output to the terminal
    or to the given *fobj*.

    :param bool use_color: whether or not to output in color (default
        ``True``)
    :param bool flush: whether or not to flush to the file after every
        message
    :param fobj: file-like object to log to (default :data:`sys.stdout`)
    :param int context_level_spaces: number of spaces per context level
        (default 4)
    """

    flush: bool
    fobj: Union[io.IOBase, TextIO]

    def __init__(
        self,
        use_color: bool = True,
        flush: bool = True,
        fobj: Optional[io.IOBase] = None,
        context_level_spaces: Optional[int] = None,
    ):
        super().__init__(
            use_color=use_color,
            context_level_spaces=context_level_spaces,
        )

        self.flush = flush
        self.fobj = fobj or sys.stdout

    @override
    def emit(self, message: str) -> None:
        """
        Implementation of :meth:`SimpleLogEmitter.emit` that emits the given
        *message* text to the configured :attr:`fobj`.
        """
        _ = self.fobj.write(message)
        if self.flush:
            self.fobj.flush()

    @override
    def log_response(self, task: T, response: Dict[str, Any]) -> None:
        """
        Log the given *response* for a task.
        """
        self.log_message(
            LogLevel.PROCEDURE,
            "\n".join(
                [
                    "Response for task:",
                    pprint.pformat(response),
                ]
            ),
        )
