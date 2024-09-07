import collections
from typing import Optional

import colorama
from typing_extensions import override

from .emitter import Emitter, LogLevel, T


class SimpleLogEmitter(Emitter[T]):
    """
    The SimpleLogEmitter is an abstract :class:`Emitter` implementation that
    allows for subclasses to simply implement a single :meth:`emit` method
    to determine where the data goes. The *use_color* argument defaults to
    ``True`` and determines whether or not log messages should be emitted
    with color encoding.

    :param bool use_color: whether or not to output in color (default
        ``True``)
    :param int context_level_spaces: number of spaces per context level
        (default 4)

    .. automethod:: emit
    """

    use_color: bool
    context_level_spaces: int

    DEFAULT_CONTEXT_LEVEL_SPACES = 4

    LOG_LEVEL_COLORS = collections.defaultdict(
        lambda: colorama.Style.RESET_ALL,
        {
            LogLevel.DEBUG: colorama.Fore.WHITE + colorama.Style.DIM,
            LogLevel.PROCEDURE: colorama.Fore.BLUE,
            LogLevel.INFO: colorama.Fore.WHITE,
            LogLevel.SKIP: colorama.Fore.MAGENTA + colorama.Style.BRIGHT,
            LogLevel.SUCCESS: colorama.Fore.GREEN,
            LogLevel.ERROR: colorama.Fore.RED + colorama.Style.BRIGHT,
            LogLevel.FAIL: colorama.Fore.RED,
            LogLevel.CATASTROPHIC: colorama.Fore.CYAN + colorama.Style.BRIGHT,
        },
    )

    def __init__(
        self,
        use_color: bool = True,
        context_level_spaces: Optional[int] = None,
    ):
        super().__init__()

        self.use_color = use_color
        self.context_level_spaces = (
            context_level_spaces or self.DEFAULT_CONTEXT_LEVEL_SPACES
        )

    @override
    def log_message(self, log_level: LogLevel, message: str, end: str = "\n") -> None:
        """
        Specific information of :meth:`Emitter.log_message` that calls
        :meth:`emit` with color-encoded text.
        """
        spaces = " " * (self.context_level * self.context_level_spaces)
        color_pre_tag = ""
        color_post_tag = ""
        if self.use_color:
            color_pre_tag = self.LOG_LEVEL_COLORS[log_level]
            color_post_tag = colorama.Style.RESET_ALL

        for line in message.splitlines() if end == "\n" else message.split(end):
            line = line.rstrip()
            self.emit(f"{spaces}{color_pre_tag}{line}{color_post_tag}{end}")

    def emit(self, message: str) -> None:  # pyright: ignore[reportUnusedParameter]
        """
        Emit the given *message*. This should be implemented by sub-class
        implementations.
        """
