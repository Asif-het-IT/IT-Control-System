# app/infrastructure/exceptions.py
"""
Production-grade exception handling for the HET IT Control System.
Features:
- Custom exception hierarchy
- Global exception handling with GUI popups
- Error recovery mechanisms
- Structured error logging
- User-friendly error messages
"""
import sys
import traceback
import threading
from typing import Optional, Callable, Any
from contextlib import contextmanager

from PySide6.QtWidgets import QMessageBox, QApplication
from PySide6.QtCore import QTimer, Qt

from app.infrastructure.logger import get_logger

logger = get_logger("exceptions")


class HETError(Exception):
    """Base exception for HET IT Control System."""

    def __init__(self, message: str, user_message: Optional[str] = None,
                 recovery_action: Optional[str] = None, error_code: Optional[str] = None):
        super().__init__(message)
        self.user_message = user_message or message
        self.recovery_action = recovery_action
        self.error_code = error_code or self.__class__.__name__


class ConfigurationError(HETError):
    """Configuration related errors."""
    pass


class JobError(HETError):
    """Job execution related errors."""
    pass


class ValidationError(JobError):
    """Job validation errors."""
    pass


class NetworkError(HETError):
    """Network related errors."""
    pass


class DatabaseError(HETError):
    """Database related errors."""
    pass


class FileSystemError(HETError):
    """File system related errors."""
    pass


class AuthenticationError(HETError):
    """Authentication related errors."""
    pass


class BranchError(HETError):
    """Branch related errors."""
    pass


class ResilienceError(HETError):
    """Resilience and retry related errors."""
    pass


class MonitoringError(HETError):
    """Monitoring and alerting related errors."""
    pass


class AlertingError(HETError):
    """Alert management and delivery related errors."""
    pass


class GUIErrorHandler:
    """Global GUI error handler for displaying user-friendly error messages."""

    def __init__(self):
        self._main_window = None
        self._error_queue = []
        self._timer = None

    def set_main_window(self, main_window):
        """Set the main window reference for error dialogs."""
        self._main_window = main_window

    def show_error_dialog(self, title: str, message: str, details: Optional[str] = None,
                         recovery_action: Optional[str] = None):
        """
        Show an error dialog to the user.

        Args:
            title: Dialog title
            message: User-friendly error message
            details: Technical details (shown in expandable section)
            recovery_action: Suggested recovery action
        """
        def _show_dialog():
            if not QApplication.instance():
                return

            # Create message box
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Critical)
            msg_box.setWindowTitle(title)
            msg_box.setText(message)

            if details or recovery_action:
                detailed_text = ""
                if details:
                    detailed_text += f"Technical Details:\n{details}\n\n"
                if recovery_action:
                    detailed_text += f"Suggested Action:\n{recovery_action}"

                msg_box.setDetailedText(detailed_text)
                msg_box.setStandardButtons(QMessageBox.Ok)

            # Show dialog
            if self._main_window:
                msg_box.setParent(self._main_window)
                msg_box.setWindowModality(Qt.WindowModal)

            msg_box.exec()

        # Queue the dialog to be shown on the main thread
        if threading.current_thread() is threading.main_thread():
            _show_dialog()
        else:
            # Queue for main thread
            self._error_queue.append(_show_dialog)
            if self._timer is None:
                self._timer = QTimer()
                self._timer.timeout.connect(self._process_error_queue)
                self._timer.setSingleShot(True)
                self._timer.start(100)  # Process after 100ms

    def _process_error_queue(self):
        """Process queued error dialogs on the main thread."""
        while self._error_queue:
            dialog_func = self._error_queue.pop(0)
            dialog_func()
        self._timer = None


class GlobalExceptionHandler:
    """Global exception handler for the application."""

    def __init__(self):
        self._original_excepthook = sys.excepthook
        self._gui_handler = GUIErrorHandler()
        self._error_callbacks = []
        self._recovery_strategies = {}

    def set_gui_handler(self, gui_handler: GUIErrorHandler):
        """Set the GUI error handler."""
        self._gui_handler = gui_handler

    def add_error_callback(self, callback: Callable[[Exception, str], None]):
        """
        Add a callback to be called when an error occurs.

        Args:
            callback: Function that takes (exception, context) parameters
        """
        self._error_callbacks.append(callback)

    def register_recovery_strategy(self, exception_type: type, strategy: Callable[[Exception], Any]):
        """
        Register a recovery strategy for a specific exception type.

        Args:
            exception_type: The exception class to handle
            strategy: Function that takes the exception and returns recovery result
        """
        self._recovery_strategies[exception_type] = strategy

    def handle_exception(self, exc_type: type, exc_value: Exception, exc_traceback, context: str = "application"):
        """
        Handle an exception with logging, GUI display, and recovery attempts.

        Args:
            exc_type: Exception type
            exc_value: Exception instance
            exc_traceback: Traceback object
            context: Context where the exception occurred
        """
        # Skip keyboard interrupts
        if issubclass(exc_type, KeyboardInterrupt):
            self._original_excepthook(exc_type, exc_value, exc_traceback)
            return

        # Get error details
        error_message = str(exc_value)
        error_details = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))

        # Log the error
        logger.critical(f"Uncaught exception in {context}: {error_message}",
                       exc_info=(exc_type, exc_value, exc_traceback),
                       extra={
                           "context": context,
                           "error_type": exc_type.__name__,
                           "error_message": error_message,
                           "traceback": error_details
                       })

        # Call error callbacks
        for callback in self._error_callbacks:
            try:
                callback(exc_value, context)
            except Exception as callback_error:
                logger.error(f"Error in exception callback: {callback_error}")

        # Try recovery strategy
        recovery_result = None
        for exception_base in exc_type.__mro__:
            if exception_base in self._recovery_strategies:
                try:
                    recovery_result = self._recovery_strategies[exception_base](exc_value)
                    logger.info(f"Recovery strategy succeeded for {exception_base.__name__}")
                    break
                except Exception as recovery_error:
                    logger.error(f"Recovery strategy failed: {recovery_error}")

        # Prepare user-friendly message
        if isinstance(exc_value, HETError):
            user_message = exc_value.user_message
            recovery_action = exc_value.recovery_action
            title = f"{exc_value.error_code} Error"
        else:
            user_message = f"An unexpected error occurred in the {context}."
            recovery_action = "Please check the logs for more details and restart the application if necessary."
            title = "Application Error"

        # Show GUI error dialog
        if self._gui_handler:
            self._gui_handler.show_error_dialog(
                title=title,
                message=user_message,
                details=error_details,
                recovery_action=recovery_action
            )

        # If recovery failed or no recovery attempted, call original handler
        if recovery_result is None:
            self._original_excepthook(exc_type, exc_value, exc_traceback)

    def install(self):
        """Install the global exception handler."""
        sys.excepthook = self._handle_uncaught_exception

    def uninstall(self):
        """Uninstall the global exception handler."""
        sys.excepthook = self._original_excepthook

    def _handle_uncaught_exception(self, exc_type: type, exc_value: Exception, exc_traceback):
        """Handle uncaught exceptions."""
        self.handle_exception(exc_type, exc_value, exc_traceback, "application")


# Global instances
_gui_error_handler = GUIErrorHandler()
_global_exception_handler = GlobalExceptionHandler()

def get_gui_error_handler() -> GUIErrorHandler:
    """Get the global GUI error handler."""
    return _gui_error_handler


def get_global_exception_handler() -> GlobalExceptionHandler:
    """Get the global exception handler."""
    return _global_exception_handler


@contextmanager
def error_context(context: str):
    """
    Context manager for providing error context.

    Usage:
        with error_context("database_operation"):
            # code that might raise exceptions
            pass
    """
    try:
        yield
    except Exception as e:
        # Re-raise with context
        if not isinstance(e, HETError):
            # Wrap non-HET errors
            raise HETError(f"Error in {context}: {str(e)}",
                          user_message=f"An error occurred during {context.replace('_', ' ')}.",
                          recovery_action="Please check the application logs for more details.") from e
        else:
            # Re-raise HET errors as-is
            raise


def safe_call(func: Callable, *args, context: str = "operation", **kwargs) -> Any:
    """
    Safely call a function with error handling.

    Args:
        func: Function to call
        args: Positional arguments
        context: Context for error reporting
        kwargs: Keyword arguments

    Returns:
        Function result or None if error occurred
    """
    try:
        with error_context(context):
            return func(*args, **kwargs)
    except Exception as e:
        logger.error(f"Safe call failed in {context}: {e}")
        return None


# Install global exception handler on import
_global_exception_handler.set_gui_handler(_gui_error_handler)
_global_exception_handler.install()