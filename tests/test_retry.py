from unittest.mock import MagicMock

import time

import pytest
from reretry.api import retry, retry_call


def test_retry(monkeypatch):
    mock_sleep_time = [0]

    def mock_sleep(seconds):
        mock_sleep_time[0] += seconds

    monkeypatch.setattr(time, "sleep", mock_sleep)

    hit = [0]

    tries = 5
    delay = 1
    backoff = 2

    @retry(tries=tries, delay=delay, backoff=backoff)
    def f():
        hit[0] += 1
        raise RuntimeError

    with pytest.raises(RuntimeError):
        f()
    assert hit[0] == tries
    assert mock_sleep_time[0] == sum(delay * backoff**i for i in range(tries - 1))


def test_tries_inf():
    hit = [0]
    target = 10

    @retry(tries=float("inf"))
    def f():
        hit[0] += 1
        if hit[0] == target:
            return target

        raise ValueError

    assert f() == target


def test_tries_minus1():
    hit = [0]
    target = 10

    @retry(tries=-1)
    def f():
        hit[0] += 1
        if hit[0] == target:
            return target

        raise ValueError

    assert f() == target


def test_max_delay(monkeypatch):
    mock_sleep_time = [0]

    def mock_sleep(seconds):
        mock_sleep_time[0] += seconds

    monkeypatch.setattr(time, "sleep", mock_sleep)

    hit = [0]

    tries = 5
    delay = 1
    backoff = 2
    max_delay = delay  # Never increase delay

    @retry(tries=tries, delay=delay, max_delay=max_delay, backoff=backoff)
    def f():
        hit[0] += 1
        raise RuntimeError

    with pytest.raises(RuntimeError):
        f()
    assert hit[0] == tries
    assert mock_sleep_time[0] == delay * (tries - 1)


def test_fixed_jitter(monkeypatch):
    mock_sleep_time = [0]

    def mock_sleep(seconds):
        mock_sleep_time[0] += seconds

    monkeypatch.setattr(time, "sleep", mock_sleep)

    hit = [0]

    tries = 10
    jitter = 1

    @retry(tries=tries, jitter=jitter)
    def f():
        hit[0] += 1
        raise RuntimeError

    with pytest.raises(RuntimeError):
        f()
    assert hit[0] == tries
    assert mock_sleep_time[0] == sum(range(tries - 1))


def test_retry_call():
    f_mock = MagicMock(side_effect=RuntimeError)
    tries = 2
    try:
        retry_call(f_mock, exceptions=RuntimeError, tries=tries)
    except RuntimeError:
        pass

    assert f_mock.call_count == tries


def test_retry_call_2():
    side_effect = [RuntimeError, RuntimeError, 3]
    f_mock = MagicMock(side_effect=side_effect)
    tries = 5
    result = None
    try:
        result = retry_call(f_mock, exceptions=RuntimeError, tries=tries)
    except RuntimeError:
        pass

    assert result == 3
    assert f_mock.call_count == len(side_effect)


def test_retry_call_with_args():
    def f(value=0):
        if value < 0:
            return value

        raise RuntimeError

    return_value = -1
    result = None
    f_mock = MagicMock(spec=f, return_value=return_value)
    try:
        result = retry_call(f_mock, fargs=[return_value])
    except RuntimeError:
        pass

    assert result == return_value
    assert f_mock.call_count == 1


def test_retry_call_with_kwargs():
    def f(value=0):
        if value < 0:
            return value

        raise RuntimeError

    kwargs = {"value": -1}
    result = None
    f_mock = MagicMock(spec=f, return_value=kwargs["value"])
    try:
        result = retry_call(f_mock, fkwargs=kwargs)
    except RuntimeError:
        pass

    assert result == kwargs["value"]
    assert f_mock.call_count == 1


def test_retry_call_with_fail_callback():
    def f():
        raise RuntimeError

    def cb(error):
        pass

    callback_mock = MagicMock(spec=cb)
    try:
        retry_call(f, fail_callback=callback_mock, tries=2)
    except RuntimeError:
        pass

    assert callback_mock.called


def test_show_traceback():
    logger = MagicMock()
    logger.warning = MagicMock()

    def f():
        raise RuntimeError

    try:
        retry_call(f, show_traceback=True, logger=logger, tries=2)
    except RuntimeError:
        pass

    assert logger.warning.called


def test_save_spec():
    try:
        # currently works only if `decorator` package is installed
        import decorator

        @retry(tries=2)
        def decorated(x, y, *, a: str = "a"):
            pass

        def undecorated(x, y, *, a: str = "a"):
            pass

        from inspect import getfullargspec

        assert getfullargspec(decorated) == getfullargspec(undecorated)

    except ImportError:
        pass
