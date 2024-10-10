"""
module for running tasks
"""

import collections
import random
from typing import Any, Callable, Deque, Dict, Iterator, List, Optional, Set

from automation_entities.context import (
    patch_dict,  # pyright: ignore[reportUnknownVariableType]
)
from typing_extensions import override

from automation_traverse.emitters.emitter import Emitter

from .task import RUN_CATASTROPHIC, RUN_SKIP, RUN_SUCCESS, Task


class RunOptions:
    """
    Options describing a run

    .. autoattribute:: random_order
    .. autoattribute:: config_filepath
    .. autoattribute:: emitters
    .. autoattribute:: debug
    .. autoattribute:: failfast
    .. autoattribute:: rerun_failures
    .. autoattribute:: between_tasks
    """

    #: whether to execute dependent tasks in a random order
    random_order: bool

    #: path to where the config file is
    config_filepath: Optional[str]

    #: optional ``list`` of :class:`Emitter`\s for logging information
    emitters: Optional[List[Emitter[Task]]]

    #: whether or not to print debug information
    debug: bool

    #: whether to fail the run immediately if one of the tasks fails
    failfast: bool

    #: how many times to rerun tasks that failed
    rerun_failures: Optional[int]

    #: function to call whenever a task completes execution
    between_tasks: Optional[Callable[[], None]]

    def __init__(self) -> None:
        self.random_order = False
        self.config_filepath = None
        self.emitters = None
        self.debug = False
        self.failfast = False
        self.rerun_failures = None
        self.between_tasks = None


class StopRun(Exception):
    """
    exeption for immediately stopping a task run
    """


class FinishRun(Exception):
    """
    exeption for signaling to finish a task run
    """


class RunnerGraph:
    """
    Object for organizing tasks into a graph.

    .. autoattribute:: tasks
    .. autoattribute:: root
    .. autoattribute:: all_nodes

    .. automethod:: add_task
    .. automethod:: reset
    """

    #: the root task
    root: Optional["RunnerNode"]

    #: mapping of all task nodes
    all_nodes: Dict[str, "RunnerNode"]

    def __init__(self, tasks: List[Task]) -> None:
        self.root = None
        self.all_nodes = {}

        for task in tasks:
            _ = self.add_task(task)

    def add_task(self, task: Task, allow_duplicate: bool = False) -> "RunnerNode":
        """
        Add given *task* to the *graph*
        """
        key = RunnerNode.generate_key(task)
        if key in self.all_nodes:
            node = self.all_nodes[key]

            return self.all_nodes[key]

        parent_nodes: List["RunnerNode"] = []
        for parent in task.PARENTS:
            parent_args = {k: v for k, v in task.args.items() if k in parent.ARGUMENTS}
            parent_nodes.append(self.add_task(parent(parent_args)))

        node = RunnerNode(task, parent_nodes)
        if not allow_duplicate:
            self.all_nodes[key] = node

        if self.root is None:
            self.root = node

        for parent_node in parent_nodes:
            parent_node.children.append(node)

        return node

    def clean_graph(self) -> List["RunnerNode"]:
        """
        Clean the graph of tasks that have finished running.
        """
        if not self.root:
            return []

        remove_nodes: List[RunnerNode] = []
        remove_set: Set[RunnerNode] = set()
        for node in self.root:
            if node.complete:
                remove_nodes.append(node)
                remove_set.add(node)

        for node in reversed(remove_nodes):
            key = RunnerNode.generate_key(node.task)
            if key in self.all_nodes:
                del self.all_nodes[key]

            for parent in node.parents:
                parent.children = collections.deque(
                    [n for n in parent.children if n not in remove_set]
                )

        if self.root in remove_set:
            self.root = None

        return remove_nodes

    def reset(self) -> None:
        """
        Reset the graph so that it can be run again
        """
        if self.root is not None:
            self.root.reset(recursive=True)

    def run(self, opts: Optional["RunOptions"] = None) -> bool:
        opts = opts or RunOptions()
        success = True
        if self.root is not None:
            failure_iters: int = opts.rerun_failures or 0
            while True:
                try:
                    _ = self.root.execute(opts=opts)
                    if self.root:
                        self.root.teardown_all(opts)

                except FinishRun:
                    if self.root:
                        self.root.teardown_all(opts)

                    success = False
                    break

                except StopRun:
                    success = False
                    break

                if not self.root:
                    break

                for node in self.root:
                    if node.task.status not in [RUN_SKIP, RUN_SUCCESS]:
                        success = False

                if opts.rerun_failures is not None and failure_iters > 0:
                    rerun_nodes: List["RunnerNode"] = []
                    for node in self.root:
                        if node.task.status not in [RUN_SKIP, RUN_SUCCESS]:
                            rerun_nodes.append(node)

                    if rerun_nodes:
                        success = True
                        for node in rerun_nodes:
                            node.reset(recursive=True)
                            for p in list(node.reversed())[1:]:
                                p.reset()

                        failure_iters -= 1
                        continue

                if self.root.complete:
                    break

            self.finalize()

        return success

    def finalize(self, opts: Optional["RunOptions"] = None):
        opts = opts or RunOptions()
        for emitter in opts.emitters or []:
            emitter.finalize()


class RunnerNode:
    """
    A single node in the runner graph

    .. autoattribute:: task
    .. autoattribute:: parents
    .. autoattribute:: children
    .. autoattribute:: run_complete
    .. autoattribute:: run_attrs
    .. autoattribute:: children_complete
    .. autoattribute:: complete

    .. automethod:: generate_key
    .. automethod:: reset
    """

    #: task represented by this ndoe
    task: Task

    #: parent nodes of this node
    parents: List["RunnerNode"]

    #: children of this node
    children: Deque["RunnerNode"]

    #: whether or not this node has been run but not yet torn down
    run_complete: bool

    #: attrs that need to be patched to the :attr:`task`
    run_attrs: Dict[str, Any]

    #: whether or not any remaining child nodes no longer need running
    children_complete: bool

    #: whether this node and all of its children have been run and torn down
    complete: bool

    @staticmethod
    def generate_key(task: Task) -> str:
        """
        Generate key representing this node
        """
        return f"{task.__class__.__module__}.{task}"

    def __init__(self, task: Task, parents: List["RunnerNode"]) -> None:
        self.task = task
        self.parents = parents
        self.children = collections.deque()

        self.run_complete = False
        self.run_attrs = {}
        self.children_complete = False
        self.complete = False

    def reset(
        self, recursive: bool = False, visited: Optional[Set["RunnerNode"]] = None
    ) -> None:
        """
        Reset this node so it can be run again, then recurse to children
        """
        visited = visited or set()
        if self in visited:
            return

        visited.add(self)
        self.task = self.task.clone()
        self.run_complete = False
        self.run_attrs = {}
        self.children_complete = False
        self.complete = False

        if recursive:
            for child in self.children:
                child.reset(recursive=True, visited=visited)

    def __iter__(self) -> Iterator["RunnerNode"]:
        """
        iterate over all nodes in this graph
        """
        return self.forwards()

    def forwards(
        self, visited: Optional[Set["RunnerNode"]] = None
    ) -> Iterator["RunnerNode"]:
        """
        Iterate over this node and all children in a forwards direction.
        """
        visited = visited if visited is not None else set()
        if self in visited:
            return

        # Yield our node first and mark it as visited
        yield self
        visited.add(self)

        # Recurse to child nodes and ensure we don't loop around to any node
        # that we've already visited.
        for child in self.children:
            for n in child.forwards(visited=visited):
                yield n

    def reversed(
        self, visited: Optional[Set["RunnerNode"]] = None
    ) -> Iterator["RunnerNode"]:
        """
        Iterate over this node, then all parents in a reverse direction.
        """
        visited = visited if visited is not None else set()
        if self in visited:
            return

        # Yield our node first and mark it as visited
        yield self
        visited.add(self)

        # Recurse to parent nodes and ensure we don't loop around to any node
        # that we've already visited.
        for parent in self.parents:
            for n in parent.reversed(visited=visited):
                yield n

    def teardown_all(self, opts: Optional["RunOptions"] = None) -> None:
        """
        Recursively tear down all nodes that have been run but haven't yet
        been torn down.
        """
        opts = opts or RunOptions()
        if not self.run_complete:
            return

        for child in self.children:
            child.teardown_all(opts)

        self.execute_teardown(opts)

    def find_outstanding_nodes(
        self,
        path: Optional[Set["RunnerNode"]] = None,
        outstanding: Optional[Set["RunnerNode"]] = None,
    ) -> Set["RunnerNode"]:
        """
        Traverse the graph and find outstanding nodes.
        """
        outstanding = set() if outstanding is None else outstanding
        for parent in self.parents:
            if path is not None and parent in path:
                continue

            if parent.run_complete:
                outstanding.add(parent)

            else:
                _ = parent.find_outstanding_nodes(path=path, outstanding=outstanding)

        return outstanding

    def teardown_outstanding(
        self,
        outstanding_nodes: Set["RunnerNode"],
        wrt: "RunnerNode",
        opts: Optional["RunOptions"] = None,
    ) -> Set["RunnerNode"]:
        """
        Teardown all outstanding nodes with respect to the given node. The
        purpose here is to ensure that the runlevel is only what the given
        node expects, nothing more.
        """
        opts = opts or RunOptions()
        all_ancestors = set(wrt.reversed())

        # Set of the "highest" nodes in the graph that can be considered
        # outstanding.
        teardown_nodes: Set["RunnerNode"] = set() | set(outstanding_nodes)
        while teardown_nodes:
            teardown_node = None
            if opts.random_order:
                teardown_node = random.choice(list(teardown_nodes))

            else:
                teardown_node = teardown_nodes.__iter__().__next__()

            teardown_nodes.remove(teardown_node)

            # This node needs to be torn down as we aren't related to it.
            if teardown_node not in all_ancestors:
                teardown_node.execute_teardown(opts)
                teardown_nodes |= set(teardown_node.parents)

        return teardown_nodes

    def execute_run(
        self,
        outstanding_nodes: Optional[Set["RunnerNode"]] = None,
        path: Optional[Set["RunnerNode"]] = None,
        opts: Optional["RunOptions"] = None,
    ) -> Set["RunnerNode"]:
        """
        run this task only
        """
        opts = opts or RunOptions()

        # Take a hatchet to the outstanding nodes of the previous task. The
        # remaining nodes are all our ancestors.
        if outstanding_nodes:
            _ = self.teardown_outstanding(outstanding_nodes, self, opts=opts)

        for parent in self.parents:
            if not parent.run_complete:
                _ = parent.execute_run(path=path, opts=opts)

                # For some reason, our parent could not run. This means we can't
                # run either.
                if not parent.run_complete:
                    return self.find_outstanding_nodes(path=path)

                # They've already modified us and tore themselves down. Just
                # return. We're going to have to recalculate our outstanding
                # nodes, however, because we're left in a wonky state.
                if parent.task.status is not None:
                    return self.find_outstanding_nodes(path=path)

            patch_dict(self.run_attrs, parent.run_attrs)

        outstanding_nodes = self.find_outstanding_nodes(path=path)

        if not self.check_can_run():
            return outstanding_nodes

        ########################################################################
        # At this point, we're going to run this task.
        ########################################################################

        # There's really nothing to execute with the base class. Save us some
        # spam by skipping it.
        if self.task.__class__ != Task:
            if opts.config_filepath is not None:
                self.task.set_config_filepath(opts.config_filepath)

            for emitter in opts.emitters or []:
                self.task.add_emitter(emitter)

            for emitter in opts.emitters or []:
                emitter.start_task(self.task)

            self.task.patch_attrs(self.run_attrs)
            self.task.execute_run(debug=opts.debug)

        self.update_status()
        patch_dict(
            self.run_attrs,
            {
                attr: self.task.__getattribute__(attr)
                for attr in self.task.PRESENTED_ATTRS
            },
        )
        return outstanding_nodes

    def save_the_children(
        self,
        path: Optional[Set["RunnerNode"]] = None,
        opts: Optional["RunOptions"] = None,
    ) -> None:
        """
        Run child test cases. I just didn't want to call it
        ``execute_children``
        """
        # We've hinted at ourselves to not run our children.
        if not self.run_complete or self.children_complete:
            return

        opts = opts or RunOptions()
        outstanding_nodes: Optional[Set["RunnerNode"]] = None
        last_leftover_children: Set["RunnerNode"] = set()
        while True:
            available_children = [c for c in self.children if not c.check_complete()]
            if opts.random_order:
                random.shuffle(available_children)

            available_children = collections.deque(available_children)
            leftover_children: Set["RunnerNode"] = set()
            finished_children: Set["RunnerNode"] = set()
            while available_children:
                child = available_children.popleft()
                if not child.check_can_run():
                    leftover_children.add(child)
                    continue

                outstanding_nodes = child.execute(
                    outstanding_nodes=outstanding_nodes,
                    path=path,
                    opts=opts,
                )
                if not child.check_complete():
                    leftover_children.add(child)

                else:
                    finished_children.add(child)

            # We're done!
            if not leftover_children:
                break

            # We aren't able to run any of our currently available children
            # twice in a row (or we could only attempt to run one of them this
            # iteration.) Just give up for now.
            elif (
                leftover_children == last_leftover_children
                or len(leftover_children | finished_children) == 1
            ):
                break

            else:
                last_leftover_children = leftover_children

        if outstanding_nodes:
            _ = self.teardown_outstanding(outstanding_nodes, self, opts=opts)

        if not last_leftover_children:
            self.children_complete = True

    def execute_teardown(self, opts: Optional["RunOptions"] = None) -> None:
        """
        Execute the teardown stage
        """
        opts = opts or RunOptions()
        try:
            # There's really nothing to execute with the base class. Save us
            # some spam by skipping it.
            if self.task.__class__ != Task:
                for emitter in opts.emitters or []:
                    emitter.start_task(self.task)

                # Patch our attrs back so we get our context back.
                self.task.patch_attrs(self.run_attrs)
                self.task.execute_teardown(debug=opts.debug)
                for emitter in opts.emitters or []:
                    emitter.end_task(self.task)

                if self.task.status == RUN_CATASTROPHIC:
                    self.run_complete = False
                    for node in self.reversed():
                        node.finish_node(opts)

                    raise StopRun

            else:
                self.task.status = RUN_SUCCESS

            # We're now officially out of this node's runlevel, so mark it as
            # such.
            self.run_complete = False
            self.finish_node(opts)

        except Exception:
            if self.task.__class__ != Task:
                for emitter in opts.emitters or []:
                    emitter.end_task(self.task)

            raise

    def execute(
        self,
        outstanding_nodes: Optional[Set["RunnerNode"]] = None,
        path: Optional[Set["RunnerNode"]] = None,
        opts: Optional["RunOptions"] = None,
    ) -> Set["RunnerNode"]:
        """
        Execute this node to completion
        """
        path = path or set()

        outstanding_nodes = self.execute_run(
            outstanding_nodes=outstanding_nodes,
            path=path,
            opts=opts,
        )

        # There was a short-circuit, and we shouldn't continue with this node's
        # children.
        if not self.run_complete:
            return outstanding_nodes

        path.add(self)

        opts = opts or RunOptions()
        if opts.between_tasks:
            opts.between_tasks()

        # Keep running node's children until it stops getting more to run.
        child_set = set(self.children)
        while True:
            self.save_the_children(path=path, opts=opts)
            after_child_set = set(self.children)
            if child_set == after_child_set:
                break

            self.children_complete = False
            child_set = after_child_set

        path.remove(self)

        self.execute_teardown(opts)

        return outstanding_nodes

    def check_can_run(self) -> bool:
        """
        Check if this node can be run at this point.
        """
        if self.check_complete():
            return False

        return True

    def check_complete(self) -> bool:
        """
        Check if this node is complete.
        """
        if self.complete:
            return True

        return False

    def update_status(self, opts: Optional["RunOptions"] = None) -> None:
        """
        Update status after completing a testinstance run.
        """
        opts = opts or RunOptions()
        self.run_complete = True
        if (
            opts.failfast
            and self.task.status is not None
            and self.task.status != RUN_SKIP
        ):
            self.execute_teardown(opts)
            raise FinishRun

        if self.task.status is None:
            return

        # For bad statuses, propagate to all of our children as we can't run
        # them anyway.
        self.children_complete = True
        for child in self:
            if child == self:
                continue

            child.children_complete = True
            child.complete = True

            child.task.status = self.task.status
            child.task.error = self.task.error
            child.task.error_text = self.task.error_text

    def finish_node(self, opts: Optional["RunOptions"]) -> None:
        """
        Finish this node after a teardown.
        """
        opts = opts or RunOptions()
        self.children_complete = all(c.check_complete() for c in self.children)
        if not self.children_complete:
            self.reset()
            return

        # If it's visited, mark it complete.
        self.complete = True

        if opts.between_tasks:
            opts.between_tasks()

    @override
    def __str__(self) -> str:
        return f"RunnerNode({self.task})"

    @override
    def __repr__(self) -> str:
        return self.__str__()
