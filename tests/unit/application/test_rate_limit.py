import pytest

from chathce.application.rate_limit import RateLimitConfig, RateLimiter
from chathce.domain.errors import RateLimited

pytestmark = pytest.mark.unit


class Clock:
    def __init__(self):
        self.t = 1000.0

    def __call__(self):
        return self.t


def test_burst_and_lockout_per_user():
    clock = Clock()
    limiter = RateLimiter(RateLimitConfig(per_minute=10, burst=2, burst_window_s=10, lockout_s=30), clock=clock)
    limiter.check("u1")
    limiter.check("u1")
    with pytest.raises(RateLimited) as exc:
        limiter.check("u1")
    assert exc.value.retry_after_s == 30
    limiter.check("u2")  # otro usuario no se ve afectado
    clock.t += 31
    limiter.check("u1")
    assert limiter.usage("u1")["last_minute"] == 3


def test_message_length_validation():
    limiter = RateLimiter(RateLimitConfig(max_message_length=10))
    limiter.validate_message_length("corto")
    with pytest.raises(ValueError):
        limiter.validate_message_length("x" * 11)
