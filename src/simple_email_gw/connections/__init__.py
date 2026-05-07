"""Connection pooling for IMAP and SMTP."""

from simple_email_gw.connections.pool import ConnectionPool, RateLimitError, get_pool

__all__ = ["ConnectionPool", "RateLimitError", "get_pool"]
