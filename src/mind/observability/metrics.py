"""Prometheus metrics for Mind v5."""

import time
from typing import Callable

from fastapi import Request, Response
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse


class MindMetrics:
    """Prometheus metrics for Mind v5."""

    def __init__(self):
        # HTTP metrics
        self.http_requests_total = Counter(
            "mind_http_requests_total",
            "Total HTTP requests",
            ["method", "endpoint", "status"],
        )

        self.http_request_duration_seconds = Histogram(
            "mind_http_request_duration_seconds",
            "HTTP request duration in seconds",
            ["method", "endpoint"],
            buckets=[0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0],
        )

        # Memory retrieval metrics
        self.retrieval_latency_seconds = Histogram(
            "mind_retrieval_latency_seconds",
            "Memory retrieval latency in seconds",
            ["source"],  # vector, keyword, salience, recency, fusion
            buckets=[0.01, 0.02, 0.05, 0.1, 0.2, 0.5, 1.0],
        )

        self.retrieval_results_total = Counter(
            "mind_retrieval_results_total",
            "Total memories retrieved",
            ["temporal_level"],
        )

        self.retrieval_sources_used = Counter(
            "mind_retrieval_sources_used_total",
            "Retrieval sources used",
            ["source"],
        )

        # Decision tracking metrics
        self.decisions_tracked_total = Counter(
            "mind_decisions_tracked_total",
            "Total decisions tracked",
            ["decision_type"],
        )

        self.outcomes_observed_total = Counter(
            "mind_outcomes_observed_total",
            "Total outcomes observed",
            ["quality"],  # positive, negative, neutral
        )

        self.salience_adjustments_total = Counter(
            "mind_salience_adjustments_total",
            "Total salience adjustments",
            ["direction"],  # increase, decrease
        )

        # Memory metrics
        self.memories_created_total = Counter(
            "mind_memories_created_total",
            "Total memories created",
            ["temporal_level", "content_type"],
        )

        self.memories_promoted_total = Counter(
            "mind_memories_promoted_total",
            "Total memories promoted",
            ["from_level", "to_level"],
        )

        # Event metrics
        self.events_published_total = Counter(
            "mind_events_published_total",
            "Total events published",
            ["event_type"],
        )

        self.events_consumed_total = Counter(
            "mind_events_consumed_total",
            "Total events consumed",
            ["event_type", "consumer"],
        )

        # Embedding metrics
        self.embeddings_generated_total = Counter(
            "mind_embeddings_generated_total",
            "Total embeddings generated",
        )

        self.embedding_latency_seconds = Histogram(
            "mind_embedding_latency_seconds",
            "Embedding generation latency",
            buckets=[0.05, 0.1, 0.2, 0.5, 1.0, 2.0],
        )

        # Connection pool metrics
        self.db_pool_size = Gauge(
            "mind_db_pool_size",
            "Database connection pool size",
        )

        self.db_pool_checked_out = Gauge(
            "mind_db_pool_checked_out",
            "Database connections currently checked out",
        )

    def observe_retrieval(
        self,
        latency_seconds: float,
        sources_used: list[str],
        result_count: int,
    ) -> None:
        """Record retrieval metrics."""
        self.retrieval_latency_seconds.labels(source="fusion").observe(latency_seconds)
        for source in sources_used:
            self.retrieval_sources_used.labels(source=source).inc()

    def observe_outcome(self, quality: float) -> None:
        """Record outcome observation."""
        if quality > 0:
            label = "positive"
        elif quality < 0:
            label = "negative"
        else:
            label = "neutral"
        self.outcomes_observed_total.labels(quality=label).inc()


# Global metrics instance
metrics = MindMetrics()


class MetricsMiddleware(BaseHTTPMiddleware):
    """Middleware to record HTTP metrics."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        # Skip metrics endpoint to avoid recursion
        if request.url.path == "/metrics":
            return await call_next(request)

        start_time = time.perf_counter()

        response = await call_next(request)

        duration = time.perf_counter() - start_time

        # Extract endpoint (remove path parameters)
        endpoint = request.url.path
        for key, value in request.path_params.items():
            endpoint = endpoint.replace(str(value), f"{{{key}}}")

        metrics.http_requests_total.labels(
            method=request.method,
            endpoint=endpoint,
            status=response.status_code,
        ).inc()

        metrics.http_request_duration_seconds.labels(
            method=request.method,
            endpoint=endpoint,
        ).observe(duration)

        return response


async def metrics_endpoint(request: Request) -> StarletteResponse:
    """Prometheus metrics endpoint."""
    return StarletteResponse(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
