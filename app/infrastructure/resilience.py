# app/infrastructure/resilience.py
"""
Production-grade error resilience for the HET IT Control System.
Features:
- Retry logic with exponential backoff
- Circuit breaker pattern
- Timeout management
- Job execution resilience
- Network operation resilience
"""

import time
import threading
import random
from typing import Callable, Any, Optional, Dict, List, Type, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import functools
import logging

from app.config.settings import get_config
from app.infrastructure.logger import get_logger
from app.infrastructure.exceptions import ResilienceError

logger = get_logger("resilience")


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"         # Failing, requests rejected
    HALF_OPEN = "half_open"  # Testing if service recovered


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    backoff_factor: float = 2.0
    jitter: bool = True
    retry_on: List[Type[Exception]] = field(default_factory=lambda: [Exception])


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5
    recovery_timeout: float = 60.0
    expected_exception: List[Type[Exception]] = field(default_factory=lambda: [Exception])


@dataclass
class TimeoutConfig:
    """Configuration for timeouts."""
    default_timeout: float = 30.0
    network_timeout: float = 10.0
    database_timeout: float = 5.0
    job_timeout: float = 300.0  # 5 minutes


class CircuitBreaker:
    """Circuit breaker implementation."""

    def __init__(self, name: str, config: CircuitBreakerConfig):
        """
        Initialize circuit breaker.

        Args:
            name: Circuit breaker name
            config: Circuit breaker configuration
        """
        self.name = name
        self.config = config
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self._lock = threading.RLock()

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function through circuit breaker.

        Args:
            func: Function to execute
            args: Positional arguments
            kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            ResilienceError: If circuit is open
        """
        with self._lock:
            if self.state == CircuitBreakerState.OPEN:
                if self._should_attempt_reset():
                    self.state = CircuitBreakerState.HALF_OPEN
                    logger.info(f"Circuit breaker {self.name} entering half-open state")
                else:
                    raise ResilienceError(f"Circuit breaker {self.name} is OPEN")

            try:
                result = func(*args, **kwargs)

                # Success - reset failure count
                if self.state == CircuitBreakerState.HALF_OPEN:
                    self._reset()
                    logger.info(f"Circuit breaker {self.name} reset to CLOSED")
                elif self.failure_count > 0:
                    self.failure_count = 0
                    logger.debug(f"Circuit breaker {self.name} failure count reset")

                return result

            except Exception as e:
                self._record_failure(e)
                raise

    def _record_failure(self, exception: Exception) -> None:
        """Record a failure."""
        if not self._is_expected_exception(exception):
            return

        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.config.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            logger.warning(f"Circuit breaker {self.name} opened after {self.failure_count} failures")

    def _should_attempt_reset(self) -> bool:
        """Check if we should attempt to reset the circuit."""
        if self.last_failure_time is None:
            return True

        elapsed = (datetime.now() - self.last_failure_time).total_seconds()
        return elapsed >= self.config.recovery_timeout

    def _reset(self) -> None:
        """Reset the circuit breaker."""
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None

    def _is_expected_exception(self, exception: Exception) -> bool:
        """Check if exception is expected."""
        return any(isinstance(exception, exc_type) for exc_type in self.config.expected_exception)

    def get_status(self) -> Dict[str, Any]:
        """Get circuit breaker status."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "last_failure": self.last_failure_time.isoformat() if self.last_failure_time else None
        }


class ResilienceManager:
    """Central manager for resilience features."""

    def __init__(self, config: Optional[Any] = None):
        """
        Initialize resilience manager.

        Args:
            config: Resilience configuration
        """
        self.config = config or get_config().resilience
        self.logger = get_logger("resilience")

        # Circuit breakers registry
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._cb_lock = threading.RLock()

        # Default configurations
        self.retry_config = RetryConfig(
            max_attempts=self.config.max_retries,
            initial_delay=self.config.retry_delay,
            max_delay=self.config.max_retry_delay,
            backoff_factor=self.config.backoff_factor,
            retry_on=[Exception]  # Can be customized per operation
        )

        self.timeout_config = TimeoutConfig(
            default_timeout=self.config.default_timeout,
            network_timeout=self.config.network_timeout,
            database_timeout=self.config.database_timeout,
            job_timeout=self.config.job_timeout
        )

    def get_circuit_breaker(self, name: str) -> CircuitBreaker:
        """
        Get or create a circuit breaker.

        Args:
            name: Circuit breaker name

        Returns:
            Circuit breaker instance
        """
        with self._cb_lock:
            if name not in self._circuit_breakers:
                cb_config = CircuitBreakerConfig(
                    failure_threshold=self.config.circuit_breaker_failure_threshold,
                    recovery_timeout=self.config.circuit_breaker_recovery_timeout
                )
                self._circuit_breakers[name] = CircuitBreaker(name, cb_config)

            return self._circuit_breakers[name]

    def retry(self, func: Callable, config: Optional[RetryConfig] = None,
              *args, **kwargs) -> Any:
        """
        Execute function with retry logic.

        Args:
            func: Function to execute
            config: Retry configuration
            args: Positional arguments
            kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            ResilienceError: If all retries exhausted
        """
        retry_config = config or self.retry_config
        last_exception = None

        for attempt in range(retry_config.max_attempts):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_exception = e

                # Check if we should retry this exception
                if not any(isinstance(e, exc_type) for exc_type in retry_config.retry_on):
                    logger.debug(f"Not retrying exception {type(e).__name__} (not in retry_on list)")
                    raise

                if attempt < retry_config.max_attempts - 1:
                    delay = self._calculate_delay(attempt, retry_config)
                    logger.warning(f"Attempt {attempt + 1} failed, retrying in {delay:.2f}s: {e}")
                    time.sleep(delay)
                else:
                    logger.error(f"All {retry_config.max_attempts} attempts failed: {e}")

        raise ResilienceError(f"Operation failed after {retry_config.max_attempts} attempts") from last_exception

    def with_timeout(self, func: Callable, timeout: Optional[float] = None,
                    *args, **kwargs) -> Any:
        """
        Execute function with timeout.

        Args:
            func: Function to execute
            timeout: Timeout in seconds
            args: Positional arguments
            kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            TimeoutError: If operation times out
        """
        if timeout is None:
            timeout = self.timeout_config.default_timeout

        result = [None]
        exception = [None]
        completed = threading.Event()

        def wrapper():
            try:
                result[0] = func(*args, **kwargs)
                completed.set()
            except Exception as e:
                exception[0] = e
                completed.set()

        thread = threading.Thread(target=wrapper, daemon=True)
        thread.start()

        if completed.wait(timeout):
            if exception[0]:
                raise exception[0]
            return result[0]
        else:
            logger.warning(f"Operation timed out after {timeout}s")
            raise TimeoutError(f"Operation timed out after {timeout} seconds")

    def resilient_call(self, func: Callable, name: str = None,
                      retry_config: Optional[RetryConfig] = None,
                      timeout: Optional[float] = None,
                      *args, **kwargs) -> Any:
        """
        Execute function with full resilience (circuit breaker, retry, timeout).

        Args:
            func: Function to execute
            name: Operation name for circuit breaker
            retry_config: Retry configuration
            timeout: Timeout in seconds
            args: Positional arguments
            kwargs: Keyword arguments

        Returns:
            Function result
        """
        operation_name = name or f"{func.__module__}.{func.__name__}"

        # Get circuit breaker
        circuit_breaker = self.get_circuit_breaker(operation_name)

        # Execute with circuit breaker protection
        return circuit_breaker.call(
            lambda: self.retry(
                lambda: self.with_timeout(func, timeout, *args, **kwargs),
                retry_config
            )
        )

    def _calculate_delay(self, attempt: int, config: RetryConfig) -> float:
        """Calculate delay for retry attempt."""
        delay = config.initial_delay * (config.backoff_factor ** attempt)
        delay = min(delay, config.max_delay)

        if config.jitter:
            # Add random jitter to prevent thundering herd
            delay = delay * (0.5 + random.random() * 0.5)

        return delay

    def get_status(self) -> Dict[str, Any]:
        """Get resilience system status."""
        return {
            "circuit_breakers": {
                name: cb.get_status() for name, cb in self._circuit_breakers.items()
            },
            "retry_config": {
                "max_attempts": self.retry_config.max_attempts,
                "initial_delay": self.retry_config.initial_delay,
                "max_delay": self.retry_config.max_delay,
                "backoff_factor": self.retry_config.backoff_factor
            },
            "timeout_config": {
                "default_timeout": self.timeout_config.default_timeout,
                "network_timeout": self.timeout_config.network_timeout,
                "database_timeout": self.timeout_config.database_timeout,
                "job_timeout": self.timeout_config.job_timeout
            }
        }


# Decorators for easy application
def with_retry(config: Optional[RetryConfig] = None):
    """
    Decorator to add retry logic to a function.

    Args:
        config: Retry configuration

    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            manager = get_resilience_manager()
            return manager.retry(func, config, *args, **kwargs)
        return wrapper
    return decorator


def with_timeout(timeout: Optional[float] = None):
    """
    Decorator to add timeout to a function.

    Args:
        timeout: Timeout in seconds

    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            manager = get_resilience_manager()
            return manager.with_timeout(func, timeout, *args, **kwargs)
        return wrapper
    return decorator


def with_resilience(name: Optional[str] = None, retry_config: Optional[RetryConfig] = None,
                   timeout: Optional[float] = None):
    """
    Decorator to add full resilience to a function.

    Args:
        name: Operation name for circuit breaker
        retry_config: Retry configuration
        timeout: Timeout in seconds

    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            manager = get_resilience_manager()
            operation_name = name or f"{func.__module__}.{func.__name__}"
            return manager.resilient_call(func, operation_name, retry_config, timeout, *args, **kwargs)
        return wrapper
    return decorator


# Global instance
_resilience_manager = None

def get_resilience_manager() -> ResilienceManager:
    """Get the global resilience manager instance."""
    global _resilience_manager
    if _resilience_manager is None:
        _resilience_manager = ResilienceManager()
    return _resilience_manager


# Convenience functions
def retry_operation(func: Callable, *args, **kwargs) -> Any:
    """
    Retry an operation with default configuration.

    Args:
        func: Function to execute
        args: Positional arguments
        kwargs: Keyword arguments

    Returns:
        Function result
    """
    manager = get_resilience_manager()
    return manager.retry(func, *args, **kwargs)


def call_with_timeout(func: Callable, timeout: float, *args, **kwargs) -> Any:
    """
    Call function with timeout.

    Args:
        func: Function to execute
        timeout: Timeout in seconds
        args: Positional arguments
        kwargs: Keyword arguments

    Returns:
        Function result
    """
    manager = get_resilience_manager()
    return manager.with_timeout(func, timeout, *args, **kwargs)


def resilient_operation(func: Callable, name: str = None, *args, **kwargs) -> Any:
    """
    Execute operation with full resilience.

    Args:
        func: Function to execute
        name: Operation name
        args: Positional arguments
        kwargs: Keyword arguments

    Returns:
        Function result
    """
    manager = get_resilience_manager()
    operation_name = name or f"{func.__module__}.{func.__name__}"
    return manager.resilient_call(func, operation_name, None, None, *args, **kwargs)