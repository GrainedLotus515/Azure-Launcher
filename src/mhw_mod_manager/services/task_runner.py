"""Background task execution service."""

import logging
from typing import Any, Callable, Optional

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal, Slot

logger = logging.getLogger(__name__)


class TaskSignals(QObject):
    """Signals for task execution."""

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
        self.setAutoDelete(True)

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


class TaskRunner:
    """Manages background task execution."""

    def __init__(self, max_threads: int = 4) -> None:
        """Initialize the task runner.

        Args:
            max_threads: Maximum number of concurrent threads.
        """
        self.thread_pool = QThreadPool()
        self.thread_pool.setMaxThreadCount(max_threads)
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

        if on_finished:
            task.signals.finished.connect(on_finished)
        if on_error:
            task.signals.error.connect(on_error)
        if on_started:
            task.signals.started.connect(on_started)

        self.thread_pool.start(task)
        return task

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
