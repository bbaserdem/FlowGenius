"""
Test utilities for deterministic synchronization in concurrent tests.

This module provides synchronization primitives to replace time.sleep() calls
in tests, ensuring deterministic behavior and faster test execution.
"""

import threading
from typing import List, Callable, Any


class ThreadSynchronizer:
    """
    A helper class for synchronizing multiple threads in tests.
    
    This replaces time.sleep() with deterministic synchronization,
    ensuring all threads reach certain points before proceeding.
    """
    
    def __init__(self, num_threads: int):
        """
        Initialize synchronizer for a specific number of threads.
        
        Args:
            num_threads: Number of threads to synchronize
        """
        self.num_threads = num_threads
        self.start_barrier = threading.Barrier(num_threads)
        self.ready_event = threading.Event()
        self.completion_events = [threading.Event() for _ in range(num_threads)]
        
    def wait_for_start(self) -> None:
        """
        Wait for all threads to be ready to start.
        Called by each thread before starting work.
        """
        self.start_barrier.wait()
        
    def signal_ready(self) -> None:
        """
        Signal that setup is complete and threads can start.
        Called by the main thread after all threads are created.
        """
        self.ready_event.set()
        
    def wait_until_ready(self) -> None:
        """
        Wait until the main thread signals ready.
        Called by worker threads.
        """
        self.ready_event.wait()
        
    def signal_completion(self, thread_index: int) -> None:
        """
        Signal that a specific thread has completed its work.
        
        Args:
            thread_index: Index of the completing thread
        """
        self.completion_events[thread_index].set()
        
    def wait_for_completion(self, thread_index: int) -> None:
        """
        Wait for a specific thread to complete.
        
        Args:
            thread_index: Index of the thread to wait for
        """
        self.completion_events[thread_index].wait()
        
    def wait_for_all_completions(self) -> None:
        """
        Wait for all threads to complete their work.
        """
        for event in self.completion_events:
            event.wait()


def run_concurrent_operations(operations: List[Callable[[], Any]], 
                            synchronized: bool = True) -> List[Any]:
    """
    Run multiple operations concurrently with optional synchronization.
    
    Args:
        operations: List of callable operations to run concurrently
        synchronized: If True, ensures all threads start simultaneously
        
    Returns:
        List of results from each operation
    """
    num_operations = len(operations)
    results = [None] * num_operations
    exceptions = [None] * num_operations
    
    if synchronized:
        sync = ThreadSynchronizer(num_operations)
    
    def run_operation(index: int, operation: Callable[[], Any]) -> None:
        """Run a single operation with synchronization."""
        try:
            if synchronized:
                sync.wait_for_start()
                sync.wait_until_ready()
            
            results[index] = operation()
            
        except Exception as e:
            exceptions[index] = e
        finally:
            if synchronized:
                sync.signal_completion(index)
    
    # Create and start threads
    threads = []
    for i, op in enumerate(operations):
        thread = threading.Thread(target=run_operation, args=(i, op))
        threads.append(thread)
        thread.start()
    
    # Signal that all threads can proceed
    if synchronized:
        sync.signal_ready()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    # Check for exceptions
    for i, exc in enumerate(exceptions):
        if exc:
            raise RuntimeError(f"Operation {i} failed: {exc}") from exc
    
    return results


class OrderedExecutor:
    """
    Ensures operations execute in a specific order in concurrent tests.
    
    This is useful when testing race conditions or ensuring specific
    execution patterns without relying on time.sleep().
    """
    
    def __init__(self):
        """Initialize the ordered executor."""
        self.step = 0
        self.step_lock = threading.Lock()
        self.step_conditions = {}
        
    def wait_for_step(self, step: int) -> None:
        """
        Wait until the executor reaches a specific step.
        
        Args:
            step: The step number to wait for
        """
        with self.step_lock:
            if step not in self.step_conditions:
                self.step_conditions[step] = threading.Condition(self.step_lock)
            
            while self.step < step:
                self.step_conditions[step].wait()
                
    def advance_to_step(self, step: int) -> None:
        """
        Advance the executor to a specific step.
        
        Args:
            step: The step number to advance to
        """
        with self.step_lock:
            self.step = step
            
            # Notify all threads waiting for this step or earlier
            for s, condition in self.step_conditions.items():
                if s <= step:
                    condition.notify_all() 