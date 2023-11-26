from automation_entities.context import Context, Subcontext
from typing import List
from .emitters import Emitter, LogLevel


class TraverseContext(Context):
    """
    :class:`automation_entities.context.Context` that supports multiple
    :class:`Emitter`\s.
    """

    emitters: List[Emitter]

    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)

        self.emitters = []

    def add_emitter(self, emitter: Emitter) -> None:
        """
        Add the given *emitter* to the :attr:`emitters` list.
        """
        self.emitters.append(emitter)

    def subcontext(
        self, message: str, log_level: LogLevel = LogLevel.INFO
    ) -> "TraverseSubcontext":
        """
        subcontext implementation that creates a :class:`TraverseSubcontext`
        subcontext rather than the original.
        """
        for emitter in self.emitters:
            emitter.log_message(log_level, message)

        return TraverseSubcontext(self)

    def pop_subcontext(self, context_level: int) -> None:
        """
        Pop all emitters back to the given *context_level*.
        """
        for emitter in self.emitters:
            emitter.pop_subcontext(context_level)


class TraverseSubcontext(Subcontext):
    """
    :class:`automation_entities.context.Subcontext` that supports multiple
    :class:`automation_traverse.emitters.Emitter`\s.
    """

    context: "TraverseContext"

    def __enter__(self):
        super().__enter__()

        for emitter in self.context.emitters:
            emitter.subcontext()

    def __exit__(self, *args, **kwds):
        super().__exit__(*args, **kwds)

        self.context.pop_subcontext(self.context.log_position)
