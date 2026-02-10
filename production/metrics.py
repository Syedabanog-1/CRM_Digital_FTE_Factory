"""Custom Prometheus metrics for the CRM Digital FTE.

Defines 4 application-level metrics:
- fte_tickets_created_total: Counter by channel and category
- fte_escalations_total: Counter by reason
- fte_messages_processed_total: Counter by channel
- fte_processing_duration_seconds: Histogram of message processing time
"""

try:
    from prometheus_client import Counter, Histogram

    TICKETS_CREATED = Counter(
        "fte_tickets_created_total",
        "Total tickets created",
        ["channel", "category"],
    )

    ESCALATIONS = Counter(
        "fte_escalations_total",
        "Total escalations to human agents",
        ["reason"],
    )

    MESSAGES_PROCESSED = Counter(
        "fte_messages_processed_total",
        "Total messages processed by the worker",
        ["channel"],
    )

    PROCESSING_DURATION = Histogram(
        "fte_processing_duration_seconds",
        "Message processing duration in seconds",
        buckets=(0.1, 0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 10.0, 30.0),
    )

    METRICS_AVAILABLE = True

except ImportError:
    METRICS_AVAILABLE = False
    TICKETS_CREATED = None
    ESCALATIONS = None
    MESSAGES_PROCESSED = None
    PROCESSING_DURATION = None
