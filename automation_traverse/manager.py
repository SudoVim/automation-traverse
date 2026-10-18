import uuid
from asyncio import Queue, QueueEmpty
from typing import Dict, Optional

from automation_traverse.runner import RunnerGraph, RunOptions
from automation_traverse.task import Task


class TaskManager(RunnerGraph):
    """
    :class:`RunnerGraph` that kicks off its run asynchronously and can add
    tasks while existing ones are running.

    .. autoattribute:: trackers

    .. automethod:: queue
    """

    #: mapping of tracker UUID to its tracking object
    trackers: Dict[uuid.UUID, "TaskTracker"]
    queue: Queue[Task]

    def __init__(self) -> None:
        super().__init__([])

        self.trackers = {}
        self.queue = Queue[Task]()

    def queue_task(self, task: Task) -> "TaskTracker":
        """
        Add the given *task* to the runner.
        """
        task_uuid = uuid.uuid4()
        tracker = TaskTracker(task_uuid, task)
        self.trackers[task_uuid] = tracker

        return tracker

    async def find_task(self) -> None:
        """
        Find a task to run.
        """
        self.prune_tasks()

        task = await self.queue.get()
        _ = self.add_task(task)

        self.find_available_tasks()

        # TODO: Clean up the graph?

    def between_tasks(self) -> None:
        """
        Function that's run between tasks being executed by the graph.
        """
        self.prune_tasks()
        self.find_available_tasks()

    def find_available_tasks(self) -> None:
        """
        Find all readily available tasks to run.
        """
        while True:
            try:
                task = self.queue.get_nowait()

            except QueueEmpty:
                break

            _ = self.add_task(task)

        # TODO: Clean up the graph?

    def prune_tasks(self) -> None:
        """
        Prune tasks that have completed and return status.
        """
        self.queue.task_done()

    async def start_runner(self, opts: Optional[RunOptions] = None) -> None:
        """
        Start the runner running.
        """
        opts = opts or RunOptions()
        opts.between_tasks = self.between_tasks
        while True:
            while not self.root:
                await self.find_task()

            assert self.root is not None

            _ = self.root.execute(opts=opts)


class TaskTracker:
    """ """

    task_uuid: uuid.UUID
    task: Task

    def __init__(self, task_uuid: uuid.UUID, task: Task) -> None:
        self.task_uuid = task_uuid
        self.task = task
