"""Temporal workflows for memory lifecycle management.

Workflows are the durable, long-running orchestrators that
coordinate activities. They handle retries, timeouts, and
maintain state across failures.
"""

from dataclasses import dataclass
from datetime import timedelta
from uuid import UUID

from temporalio import workflow
from temporalio.common import RetryPolicy

# Import activity stubs (not the actual implementations)
with workflow.unsafe.imports_passed_through():
    from mind.workers.gardener.activities import (
        PromotionCandidate,
        PromotionResult,
        find_promotion_candidates,
        promote_memory,
        notify_promotion,
    )


@dataclass
class PromotionWorkflowInput:
    """Input for the memory promotion workflow."""

    user_id: UUID
    batch_size: int = 100
    max_promotions_per_run: int = 50


@dataclass
class PromotionWorkflowResult:
    """Result of the memory promotion workflow."""

    candidates_found: int
    promotions_attempted: int
    promotions_succeeded: int
    promotions_failed: int
    errors: list[str]


@workflow.defn
class MemoryPromotionWorkflow:
    """Workflow that promotes memories to higher temporal levels.

    This workflow runs periodically (via a scheduled workflow or cron)
    to evaluate and promote memories that have proven stable and valuable.

    The workflow:
    1. Finds candidate memories for promotion
    2. Promotes each candidate (with retries)
    3. Publishes events for successful promotions
    4. Returns summary of actions taken

    Example usage:
        # Start a single run
        handle = await client.start_workflow(
            MemoryPromotionWorkflow.run,
            PromotionWorkflowInput(user_id=user_id),
            id=f"promote-{user_id}",
            task_queue="gardener",
        )

        # Or schedule recurring runs
        await client.start_workflow(
            MemoryPromotionWorkflow.run,
            PromotionWorkflowInput(user_id=user_id),
            id=f"promote-scheduled-{user_id}",
            task_queue="gardener",
            cron_schedule="0 3 * * *",  # Daily at 3 AM
        )
    """

    @workflow.run
    async def run(self, input: PromotionWorkflowInput) -> PromotionWorkflowResult:
        """Execute the memory promotion workflow."""

        workflow.logger.info(
            f"Starting memory promotion for user {input.user_id}, "
            f"batch_size={input.batch_size}"
        )

        errors = []

        # Step 1: Find candidates
        try:
            candidates = await workflow.execute_activity(
                find_promotion_candidates,
                args=[input.user_id, input.batch_size],
                start_to_close_timeout=timedelta(minutes=5),
                retry_policy=RetryPolicy(
                    initial_interval=timedelta(seconds=1),
                    maximum_interval=timedelta(minutes=1),
                    maximum_attempts=3,
                ),
            )
        except Exception as e:
            workflow.logger.error(f"Failed to find candidates: {e}")
            return PromotionWorkflowResult(
                candidates_found=0,
                promotions_attempted=0,
                promotions_succeeded=0,
                promotions_failed=0,
                errors=[f"Failed to find candidates: {str(e)}"],
            )

        candidates_found = len(candidates)
        workflow.logger.info(f"Found {candidates_found} promotion candidates")

        if candidates_found == 0:
            return PromotionWorkflowResult(
                candidates_found=0,
                promotions_attempted=0,
                promotions_succeeded=0,
                promotions_failed=0,
                errors=[],
            )

        # Limit number of promotions per run
        candidates_to_process = candidates[:input.max_promotions_per_run]

        # Step 2: Promote each candidate
        promotions_attempted = 0
        promotions_succeeded = 0
        promotions_failed = 0

        for candidate in candidates_to_process:
            promotions_attempted += 1

            try:
                result: PromotionResult = await workflow.execute_activity(
                    promote_memory,
                    args=[candidate],
                    start_to_close_timeout=timedelta(minutes=2),
                    retry_policy=RetryPolicy(
                        initial_interval=timedelta(seconds=1),
                        maximum_interval=timedelta(seconds=30),
                        maximum_attempts=3,
                    ),
                )

                if result.success:
                    promotions_succeeded += 1

                    # Step 3: Publish promotion event
                    try:
                        await workflow.execute_activity(
                            notify_promotion,
                            args=[result, input.user_id],
                            start_to_close_timeout=timedelta(seconds=30),
                            retry_policy=RetryPolicy(
                                initial_interval=timedelta(seconds=1),
                                maximum_interval=timedelta(seconds=10),
                                maximum_attempts=2,
                            ),
                        )
                    except Exception as e:
                        # Don't fail the workflow for notification failures
                        workflow.logger.warning(
                            f"Failed to notify promotion for {candidate.memory_id}: {e}"
                        )

                else:
                    promotions_failed += 1
                    errors.append(f"Memory {candidate.memory_id}: {result.error}")

            except Exception as e:
                promotions_failed += 1
                errors.append(f"Memory {candidate.memory_id}: {str(e)}")
                workflow.logger.error(f"Failed to promote {candidate.memory_id}: {e}")

        workflow.logger.info(
            f"Promotion complete: {promotions_succeeded}/{promotions_attempted} succeeded"
        )

        return PromotionWorkflowResult(
            candidates_found=candidates_found,
            promotions_attempted=promotions_attempted,
            promotions_succeeded=promotions_succeeded,
            promotions_failed=promotions_failed,
            errors=errors,
        )


@workflow.defn
class ScheduledGardenerWorkflow:
    """Parent workflow that runs gardening tasks on a schedule.

    This workflow is designed to run continuously with a cron schedule.
    It coordinates multiple gardening tasks:
    - Memory promotion
    - Memory expiration (future)
    - Salience decay (future)
    - Pattern extraction (future)
    """

    @workflow.run
    async def run(self, user_ids: list[UUID]) -> dict[str, int]:
        """Run gardening tasks for all specified users.

        Args:
            user_ids: List of user IDs to process

        Returns:
            Summary of actions taken per user
        """
        workflow.logger.info(f"Starting scheduled gardening for {len(user_ids)} users")

        results = {}

        for user_id in user_ids:
            try:
                # Run promotion as a child workflow
                result = await workflow.execute_child_workflow(
                    MemoryPromotionWorkflow.run,
                    args=[PromotionWorkflowInput(user_id=user_id)],
                    id=f"promote-child-{user_id}-{workflow.info().workflow_id}",
                )

                results[str(user_id)] = result.promotions_succeeded

            except Exception as e:
                workflow.logger.error(f"Failed gardening for user {user_id}: {e}")
                results[str(user_id)] = -1  # Indicate failure

        return results
