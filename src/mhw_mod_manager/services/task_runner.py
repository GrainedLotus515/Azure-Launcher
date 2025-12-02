"""Background task execution service."""

import logging
from typing import Any, Callable, Optional

from PySide6.QtCore import QObject, QRunnable, Qt, QThreadPool, Signal, Slot

logger = logging.getLogger(__name__)


class TaskSignals(QObject):
    """Signals for task execution.

    This object must be kept alive until signals are delivered.
    """

    started = Signal()
    finished = Signal(object)
    error = Signal(Exception)
    progress = Signal(int, str)  # percent, message


class Task(QRunnable):
    """Runnable task for background execution."""

    def __init__(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Initialize the task.

        Args:
            func: Function to execute.
            *args: Positional arguments for function.
            **kwargs: Keyword arguments for function.
        """
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self.signals = TaskSignals()
        # Don't auto-delete - we manage lifecycle manually to prevent segfaults
        self.setAutoDelete(False)

    @Slot()
    def run(self) -> None:
        """Execute the task."""
        try:
            self.signals.started.emit()
            result = self.func(*self.args, **self.kwargs)
            self.signals.finished.emit(result)
        except Exception as e:
            logger.error(f"Task error: {e}", exc_info=True)
            self.signals.error.emit(e)


class TaskRunner(QObject):
    """Manages background task execution.

    Inherits from QObject to properly participate in Qt's object lifecycle
    and ensure signals are delivered correctly.
    """

    def __init__(self, max_threads: int = 4, parent: Optional[QObject] = None) -> None:
        """Initialize the task runner.

        Args:
            max_threads: Maximum number of concurrent threads.
            parent: Parent QObject.
        """
        super().__init__(parent)
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(max_threads)
        # Keep references to active tasks to prevent premature deletion
        self._active_tasks: list[Task] = []
        logger.info(f"TaskRunner initialized with {max_threads} threads")

    def run(
        self,
        func: Callable[..., Any],
        *args: Any,
        on_finished: Optional[Callable[[Any], None]] = None,
        on_error: Optional[Callable[[Exception], None]] = None,
        on_started: Optional[Callable[[], None]] = None,
        **kwargs: Any,
    ) -> Task:
        """Run a function in the background.

        Args:
            func: Function to execute.
            *args: Positional arguments for function.
            on_finished: Callback when task completes successfully.
            on_error: Callback when task raises an exception.
            on_started: Callback when task starts.
            **kwargs: Keyword arguments for function.

        Returns:
            Task instance.
        """
        task = Task(func, *args, **kwargs)

        # Keep reference to prevent deletion before signals delivered
        self._active_tasks.append(task)

        # Use queued connections to ensure callbacks run on the main thread
        # after the signal is fully delivered
        if on_started:
            task.signals.started.connect(on_started, Qt.ConnectionType.QueuedConnection)

        if on_finished:

            def _on_finished(result: Any) -> None:
                try:
                    on_finished(result)
                finally:
                    self._cleanup_task(task)

            task.signals.finished.connect(_on_finished, Qt.ConnectionType.QueuedConnection)
        else:
            # Still need to clean up even without callback
            task.signals.finished.connect(
                lambda _: self._cleanup_task(task),
                Qt.ConnectionType.QueuedConnection,
            )

        if on_error:

            def _on_error(e: Exception) -> None:
                try:
                    on_error(e)
                finally:
                    self._cleanup_task(task)

            task.signals.error.connect(_on_error, Qt.ConnectionType.QueuedConnection)
        else:
            # Still need to clean up even without callback
            task.signals.error.connect(
                lambda _: self._cleanup_task(task),
                Qt.ConnectionType.QueuedConnection,
            )

        self.thread_pool.start(task)
        return task

    def _cleanup_task(self, task: Task) -> None:
        """Remove task from active list after completion.

        Args:
            task: Task to clean up.
        """
        try:
            if task in self._active_tasks:
                self._active_tasks.remove(task)
        except (ValueError, RuntimeError):
            # Task already removed or list modified during iteration
            pass

    def wait_for_done(self, timeout_ms: int = -1) -> bool:
        """Wait for all tasks to complete.

        Args:
            timeout_ms: Timeout in milliseconds. -1 for no timeout.

        Returns:
            True if all tasks completed, False if timeout.
        """
        return self.thread_pool.waitForDone(timeout_ms)

    def active_thread_count(self) -> int:
        """Get number of active threads.

        Returns:
            Number of active threads.
        """
        return self.thread_pool.activeThreadCount()

    def pending_task_count(self) -> int:
        """Get number of tasks still being tracked.

        Returns:
            Number of pending tasks.
        """
        return len(self._active_tasks)
