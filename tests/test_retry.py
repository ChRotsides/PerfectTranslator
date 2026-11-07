import pytest
from conftest import FakeClient, auth_error, connection_error, rate_limit_error, server_error

from perfect_translator.core import TranslationError, call_with_retry, translate_chunk


def make_flaky(*outcomes):
    outcomes = list(outcomes)
    calls = []

    def fn():
        calls.append(1)
        item = outcomes.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    return fn, calls


def test_success_needs_no_retry(no_sleep):
    sleep, delays = no_sleep
    fn, calls = make_flaky("fine")
    assert call_with_retry(fn, sleep=sleep) == "fine"
    assert len(calls) == 1 and delays == []


@pytest.mark.parametrize("make_error", [rate_limit_error, server_error, connection_error])
def test_transient_errors_are_retried(make_error, no_sleep):
    sleep, delays = no_sleep
    fn, calls = make_flaky(make_error(), make_error(), "recovered")
    assert call_with_retry(fn, max_retries=3, base_delay=1.0, sleep=sleep) == "recovered"
    assert len(calls) == 3
    assert len(delays) == 2


def test_backoff_grows_exponentially_and_is_capped(no_sleep):
    sleep, delays = no_sleep
    fn, _ = make_flaky(*[rate_limit_error() for _ in range(5)], "ok")
    call_with_retry(fn, max_retries=5, base_delay=1.0, max_delay=6.0, sleep=sleep)
    # base delays 1, 2, 4, 6 (capped), 6 (capped); jitter adds at most 25%
    for actual, base in zip(delays, [1, 2, 4, 6, 6], strict=True):
        assert base <= actual <= base * 1.25


def test_gives_up_after_max_retries(no_sleep):
    sleep, delays = no_sleep
    fn, calls = make_flaky(*[rate_limit_error() for _ in range(10)])
    with pytest.raises(TranslationError) as info:
        call_with_retry(fn, max_retries=2, sleep=sleep)
    assert len(calls) == 3  # first try + 2 retries
    assert info.value.__cause__ is not None


def test_non_transient_errors_are_not_retried(no_sleep):
    sleep, delays = no_sleep
    fn, calls = make_flaky(auth_error(), "never reached")
    with pytest.raises(TranslationError):
        call_with_retry(fn, sleep=sleep)
    assert len(calls) == 1 and delays == []


def test_translate_chunk_retries_through_the_client(no_sleep):
    sleep, delays = no_sleep
    client = FakeClient([rate_limit_error(), "Γεια σου"])
    out = translate_chunk("Hello", "English", "Greek", client, "m", sleep=sleep)
    assert out == "Γεια σου"
    assert len(client.calls) == 2 and len(delays) == 1
