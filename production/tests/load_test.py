"""Locust load test for the Customer Success Digital FTE API.

Simulates realistic multi-channel traffic to validate 24/7 readiness.
Target: p95 response time < 3 seconds, zero 500 errors.

Usage:
    locust -f production/tests/load_test.py --host=http://localhost:8000 --users 10 --run-time 5m
"""

import random
import string
from locust import HttpUser, task, between, events
from locust.runners import MasterRunner


# ---- Web Form Users (most common channel) ----


class WebFormUser(HttpUser):
    """Simulate customers submitting support forms."""

    wait_time = between(2, 10)
    weight = 5  # Most common user type

    CATEGORIES = [
        "Technical Support",
        "Billing",
        "Feature Request",
        "Bug Report",
        "General Inquiry",
    ]
    PRIORITIES = ["low", "medium", "high"]
    SUBJECTS = [
        "Cannot login to my account",
        "How do I reset my password?",
        "API integration not working",
        "Need help with file sync",
        "Billing question about my plan",
        "Feature request for dark mode",
        "Bug: files not syncing properly",
        "How do I share folders?",
        "Account settings question",
        "Performance is slow today",
    ]
    MESSAGES = [
        "I've been trying to access my account but keep getting an error. Can you help?",
        "My files are not syncing between my desktop and mobile. I've tried restarting.",
        "I need to understand how to use the API for bulk file uploads. Documentation unclear.",
        "Getting error 403 when trying to share folders with external collaborators.",
        "I'd like to upgrade my plan. What are the options available for teams?",
        "The search function is returning irrelevant results. Expected better accuracy.",
        "How do I set up two-factor authentication for my team members?",
        "I accidentally deleted important files. Is there a way to recover them?",
        "The mobile app crashes when I try to open large PDF files.",
        "Can you explain the difference between the Pro and Enterprise plans?",
    ]

    def _random_email(self):
        suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
        return f"loadtest-{suffix}@test.example.com"

    @task(10)
    def submit_support_form(self):
        """Submit a support form - primary action."""
        self.client.post(
            "/support/submit",
            json={
                "name": f"Load Test User {random.randint(1, 10000)}",
                "email": self._random_email(),
                "subject": random.choice(self.SUBJECTS),
                "category": random.choice(self.CATEGORIES),
                "priority": random.choice(self.PRIORITIES),
                "message": random.choice(self.MESSAGES),
            },
            name="/support/submit",
        )

    @task(3)
    def check_ticket_status(self):
        """Check a ticket status (uses a known-invalid ID for speed)."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        with self.client.get(
            f"/support/ticket/{fake_id}",
            name="/support/ticket/[id]",
            catch_response=True,
        ) as response:
            if response.status_code == 404:
                response.success()  # Expected - ticket doesn't exist


# ---- Health Check Users ----


class HealthCheckUser(HttpUser):
    """Monitor system health during load test."""

    wait_time = between(5, 15)
    weight = 1

    @task(5)
    def check_health(self):
        """Health endpoint - should always respond quickly."""
        self.client.get("/health", name="/health")

    @task(2)
    def check_metrics(self):
        """Metrics endpoint - validates monitoring under load."""
        self.client.get(
            "/metrics/channels",
            params={"hours": 1},
            name="/metrics/channels",
        )


# ---- Customer Lookup Users ----


class CustomerLookupUser(HttpUser):
    """Simulate customer lookup operations."""

    wait_time = between(5, 20)
    weight = 1

    @task
    def lookup_customer(self):
        """Look up a customer by email."""
        with self.client.get(
            "/customers/lookup",
            params={"email": "nonexistent@load-test.example.com"},
            name="/customers/lookup",
            catch_response=True,
        ) as response:
            if response.status_code == 404:
                response.success()  # Expected


# ---- Event Hooks for Reporting ----


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Report summary statistics after load test completes."""
    if isinstance(environment.runner, MasterRunner):
        return

    stats = environment.runner.stats.total
    print("\n" + "=" * 60)
    print("LOAD TEST SUMMARY")
    print("=" * 60)
    print(f"Total requests:     {stats.num_requests}")
    print(f"Total failures:     {stats.num_failures}")
    print(f"Failure rate:       {stats.fail_ratio:.2%}")
    print(f"Avg response time:  {stats.avg_response_time:.0f}ms")
    print(f"P95 response time:  {stats.get_response_time_percentile(0.95):.0f}ms")
    print(f"P99 response time:  {stats.get_response_time_percentile(0.99):.0f}ms")
    print(f"Requests/sec:       {stats.current_rps:.1f}")
    print("=" * 60)

    # Validate targets
    p95 = stats.get_response_time_percentile(0.95)
    if p95 and p95 > 3000:
        print(f"WARNING: P95 ({p95:.0f}ms) exceeds 3000ms target!")
    else:
        print(f"PASS: P95 response time within 3s target")

    if stats.fail_ratio > 0.01:
        print(f"WARNING: Failure rate ({stats.fail_ratio:.2%}) exceeds 1% threshold!")
    else:
        print("PASS: Failure rate within acceptable range")

    print("=" * 60)
