"""Core runtime module for logging.
Provides shared runtime primitives such as config, auth, DB, and logging.
"""
import logging


def configure_logging() -> None:
    """Configure process-wide logging format and level."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
