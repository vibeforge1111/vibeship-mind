"""Temporal worker for the Gardener service.

The Gardener is responsible for memory lifecycle management:
- Promotion: Moving memories to higher temporal levels
- Expiration: Marking memories as no longer valid
- Decay: Gradually reducing salience of unused memories
- Consolidation: Merging similar memories

Run this worker with:
    python -m mind.workers.gardener.worker

Or use the CLI:
    mind worker gardener
"""

import asyncio
import signal
from typing import Any

from temporalio.worker import Worker
import structlog

from mind.infrastructure.temporal.client import get_temporal_client
from mind.workers.gardener.workflows import (
    MemoryPromotionWorkflow,
    ScheduledGardenerWorkflow,
)
from mind.workers.gardener.activities import (
    find_promotion_candidates,
    promote_memory,
    notify_promotion,
)

logger = structlog.get_logger()

TASK_QUEUE = "gardener"


async def run_worker() -> None:
    """Run the Gardener worker.

    This starts a Temporal worker that processes gardening tasks.
    The worker runs until interrupted (SIGINT/SIGTERM).
    """
    logger.info("gardener_starting", task_queue=TASK_QUEUE)

    client = await get_temporal_client()

    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=[
            MemoryPromotionWorkflow,
            ScheduledGardenerWorkflow,
        ],
        activities=[
            find_promotion_candidates,
            promote_memory,
            notify_promotion,
        ],
    )

    # Handle graceful shutdown
    shutdown_event = asyncio.Event()

    def handle_shutdown(sig: Any) -> None:
        logger.info("gardener_shutdown_requested", signal=sig)
        shutdown_event.set()

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, handle_shutdown, sig)
        except NotImplementedError:
            # Windows doesn't support add_signal_handler
            pass

    logger.info("gardener_running", task_queue=TASK_QUEUE)

    # Run worker until shutdown
    async with worker:
        await shutdown_event.wait()

    logger.info("gardener_stopped")


def main() -> None:
    """Entry point for running the worker."""
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
