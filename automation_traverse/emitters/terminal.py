import sys
from typing import Any, Optional

from .simple_log import SimpleLogEmitter


class TerminalEmitter(SimpleLogEmitter):
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
    fobj: Any

    def __init__(
        self,
        use_color: bool = True,
        flush: bool = True,
        fobj: Optional[Any] = None,
        context_level_spaces: Optional[int] = None,
    ):
        super().__init__(
            use_color=use_color,
            context_level_spaces=context_level_spaces,
        )

        self.flush = flush
        self.fobj = fobj or sys.stdout

    def emit(self, message: str) -> None:
        """
        Implementation of :meth:`SimpleLogEmitter.emit` that emits the given
        *message* text to the configured :attr:`fobj`.
        """
        self.fobj.write(message)
        if self.flush:
            self.fobj.flush()
