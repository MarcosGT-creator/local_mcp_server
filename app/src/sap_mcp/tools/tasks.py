"""
Background Task Tools

Tools that demonstrate FastMCP background task capabilities with progress reporting.
These tools run asynchronously and report progress back to clients.

Requires: pip install "fastmcp[tasks]>=3.0.0b1"
"""

import asyncio
from pydantic import Field
from fastmcp.tools import tool as _tool
from fastmcp.dependencies import Progress
from typing import Callable, Any

tool: Callable[..., Any] = _tool  # type: ignore[assignment]


# @tool(task=True)
async def long_running_computation(
    items: int = Field(
        default=5,
        description="Number of items to process (1-100)",
        ge=1,
        le=100,
    ),
    delay_per_item: float = Field(
        default=2.0,
        description="Simulated processing time per item in seconds (0.5-10)",
        ge=0.5,
        le=10.0,
    ),
    progress: Progress = Progress(),
) -> dict:
    """
    Simulate a long-running computation that processes multiple items.
    
    This tool demonstrates background task execution with structured output:
    - Processes items sequentially with progress updates
    - Returns detailed results for each processed item
    - Useful for testing task behavior with varying workloads
    
    **Use Cases:**
    - Simulating batch processing scenarios
    - Testing task cancellation and recovery
    - Validating progress reporting with different item counts
    
    **Example:**
        >>> # Process 5 items with 2-second delay each
        >>> result = long_running_computation(items=5, delay_per_item=2.0)
        >>> # Total time: ~10 seconds
        >>> # Returns: {"items_processed": 5, "total_time": 10.0, "results": [...]}
    
    **Returns:**
        Dictionary with processing results and statistics
    """
    import time
    
    start_time = time.time()
    results = []
    
    await progress.set_total(items)
    
    for i in range(1, items + 1):
        await progress.set_message(f"Processing item {i} of {items}")
        
        # Simulate processing work
        item_start = time.time()
        await asyncio.sleep(delay_per_item)
        item_duration = time.time() - item_start
        
        results.append({
            "item_number": i,
            "status": "completed",
            "processing_time": round(item_duration, 2),
        })
        
        await progress.increment()
    
    total_time = time.time() - start_time
    
    return {
        "items_processed": items,
        "total_time_seconds": round(total_time, 2),
        "average_time_per_item": round(total_time / items, 2),
        "results": results,
    }
