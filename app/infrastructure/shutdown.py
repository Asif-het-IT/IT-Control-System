# app/infrastructure/shutdown.py
"""
Production-grade graceful shutdown management for the HET IT Control System.
Features:
- Coordinated shutdown of all system components
- Signal handling (SIGTERM, SIGINT)
- Resource cleanup with timeouts
- Shutdown hooks and callbacks
- Force shutdown protection
"""
import signal
import threading
import time
import atexit
from typing import Callable, List, Optional
from enum import Enum
from contextlib import contextmanager

from app.infrastructure.logger import get_logger

logger = get_logger("shutdown")


class ShutdownPhase(Enum):
    """Shutdown phases in order of execution."""
    PRE_SHUTDOWN = "pre_shutdown"
    STOP_SERVICES = "stop_services"
    CLOSE_CONNECTIONS = "close_connections"
    CLEANUP_RESOURCES = "cleanup_resources"
    FINALIZE = "finalize"


class ShutdownManager:
    """Centralized shutdown management system."""

    def __init__(self, shutdown_timeout: float = 30.0, force_timeout: float = 5.0):
        """
        Initialize shutdown manager.

        Args:
            shutdown_timeout: Maximum time to wait for graceful shutdown
            force_timeout: Time to wait before force shutdown after graceful timeout
        """
        self.shutdown_timeout = shutdown_timeout
        self.force_timeout = force_timeout
        self._shutdown_event = threading.Event()
        self._shutdown_in_progress = False
        self._shutdown_callbacks = {phase: [] for phase in ShutdownPhase}
        self._shutdown_lock = threading.RLock()
        self._signal_handlers_installed = False

        # Register cleanup on normal exit
        atexit.register(self._atexit_handler)

    def register_callback(self, phase: ShutdownPhase, callback: Callable[[], None],
                         priority: int = 0) -> None:
        """
        Register a shutdown callback for a specific phase.

        Args:
            phase: Shutdown phase to register for
            callback: Function to call during shutdown
            priority: Higher priority callbacks run first (0-100)
        """
        with self._shutdown_lock:
            self._shutdown_callbacks[phase].append((priority, callback))
            # Sort by priority (higher first)
            self._shutdown_callbacks[phase].sort(key=lambda x: x[0], reverse=True)

    def unregister_callback(self, phase: ShutdownPhase, callback: Callable[[], None]) -> None:
        """
        Unregister a shutdown callback.

        Args:
            phase: Shutdown phase
            callback: Callback to remove
        """
        with self._shutdown_lock:
            self._shutdown_callbacks[phase] = [
                (p, c) for p, c in self._shutdown_callbacks[phase] if c != callback
            ]

    def install_signal_handlers(self) -> None:
        """Install signal handlers for graceful shutdown."""
        if self._signal_handlers_installed:
            return

        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, initiating graceful shutdown")
            self.initiate_shutdown()

        # Handle common termination signals
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)

        # Handle SIGHUP on Unix-like systems
        try:
            signal.signal(signal.SIGHUP, signal_handler)
        except (OSError, ValueError):
            pass  # SIGHUP not available on Windows

        self._signal_handlers_installed = True
        logger.debug("Signal handlers installed for graceful shutdown")

    def initiate_shutdown(self, reason: str = "user_request") -> None:
        """
        Initiate graceful shutdown.

        Args:
            reason: Reason for shutdown
        """
        with self._shutdown_lock:
            if self._shutdown_in_progress:
                logger.warning("Shutdown already in progress")
                return

            self._shutdown_in_progress = True
            logger.info(f"Initiating graceful shutdown (reason: {reason})")

            # Start shutdown in background thread to avoid blocking
            shutdown_thread = threading.Thread(
                target=self._execute_shutdown,
                name="shutdown",
                daemon=True
            )
            shutdown_thread.start()

    def wait_for_shutdown(self, timeout: Optional[float] = None) -> bool:
        """
        Wait for shutdown to complete.

        Args:
            timeout: Maximum time to wait

        Returns:
            True if shutdown completed, False if timeout
        """
        return self._shutdown_event.wait(timeout)

    def is_shutdown_in_progress(self) -> bool:
        """Check if shutdown is currently in progress."""
        return self._shutdown_in_progress

    def _execute_shutdown(self) -> None:
        """Execute the shutdown sequence."""
        try:
            start_time = time.time()

            # Execute shutdown phases in order
            phases = [
                ShutdownPhase.PRE_SHUTDOWN,
                ShutdownPhase.STOP_SERVICES,
                ShutdownPhase.CLOSE_CONNECTIONS,
                ShutdownPhase.CLEANUP_RESOURCES,
                ShutdownPhase.FINALIZE
            ]

            for phase in phases:
                if not self._execute_phase(phase):
                    logger.warning(f"Shutdown phase {phase.value} failed or timed out")

            elapsed = time.time() - start_time
            logger.info(f"Graceful shutdown completed in {elapsed:.2f}s")

        except Exception as e:
            logger.error(f"Error during shutdown: {e}", exc_info=True)
        finally:
            self._shutdown_event.set()

    def _execute_phase(self, phase: ShutdownPhase) -> bool:
        """
        Execute a shutdown phase.

        Args:
            phase: Phase to execute

        Returns:
            True if phase completed successfully
        """
        logger.debug(f"Executing shutdown phase: {phase.value}")

        callbacks = self._shutdown_callbacks[phase]
        if not callbacks:
            logger.debug(f"No callbacks registered for phase {phase.value}")
            return True

        # Execute callbacks with individual timeouts
        phase_start = time.time()
        success_count = 0

        for priority, callback in callbacks:
            try:
                callback_timeout = min(5.0, self.shutdown_timeout / len(callbacks))  # Distribute timeout
                self._execute_callback_with_timeout(callback, callback_timeout)
                success_count += 1
            except Exception as e:
                logger.error(f"Shutdown callback failed in phase {phase.value}: {e}")

        phase_elapsed = time.time() - phase_start
        logger.debug(f"Phase {phase.value} completed: {success_count}/{len(callbacks)} callbacks successful in {phase_elapsed:.2f}s")

        return success_count > 0  # Consider successful if at least one callback succeeded

    def _execute_callback_with_timeout(self, callback: Callable[[], None], timeout: float) -> None:
        """Execute a callback with timeout protection."""
        result = [None]
        exception = [None]

        def wrapper():
            try:
                callback()
                result[0] = True
            except Exception as e:
                exception[0] = e
                result[0] = False

        thread = threading.Thread(target=wrapper, daemon=True)
        thread.start()
        thread.join(timeout)

        if thread.is_alive():
            logger.warning(f"Shutdown callback timed out after {timeout}s")
            # Note: Cannot terminate thread in Python, callback may still be running
        elif exception[0]:
            raise exception[0]

    def _atexit_handler(self) -> None:
        """Handle cleanup on normal Python exit."""
        if not self._shutdown_in_progress:
            logger.info("Application exit detected, performing cleanup")
            self._execute_shutdown()

    def force_shutdown(self) -> None:
        """Force immediate shutdown (use only as last resort)."""
        logger.warning("Force shutdown initiated")
        self._shutdown_event.set()
        # Note: In a real implementation, you might want to use os._exit() here
        # but that prevents cleanup. This is just a marker.


# Global shutdown manager instance
_shutdown_manager = None

def get_shutdown_manager() -> ShutdownManager:
    """Get the global shutdown manager instance."""
    global _shutdown_manager
    if _shutdown_manager is None:
        _shutdown_manager = ShutdownManager()
    return _shutdown_manager


@contextmanager
def shutdown_context():
    """
    Context manager that ensures shutdown on context exit.

    Usage:
        with shutdown_context():
            # application code
            pass
        # shutdown will be initiated automatically
    """
    manager = get_shutdown_manager()
    try:
        yield manager
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received, initiating shutdown")
        manager.initiate_shutdown("keyboard_interrupt")
    except Exception as e:
        logger.error(f"Unexpected error, initiating shutdown: {e}")
        manager.initiate_shutdown("unexpected_error")
    finally:
        manager.wait_for_shutdown(timeout=manager.shutdown_timeout + manager.force_timeout)


def register_shutdown_callback(phase: ShutdownPhase, callback: Callable[[], None],
                              priority: int = 0) -> None:
    """
    Register a shutdown callback globally.

    Args:
        phase: Shutdown phase
        callback: Callback function
        priority: Callback priority (higher = runs first)
    """
    get_shutdown_manager().register_callback(phase, callback, priority)


# Initialize shutdown manager on import
_shutdown_manager = ShutdownManager()
_shutdown_manager.install_signal_handlers()