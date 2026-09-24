import logging
from unittest.mock import Mock

import pytest

from repo_compliance import timing


@pytest.mark.parametrize("raises", [False, True])
def test_timing_preserves_behaviour_and_logs_elapsed_time(
    raises: bool, monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setattr(timing, "perf_counter", Mock(side_effect=[10.0, 12.5]))
    result = object()
    error = ValueError("failed")

    @timing.timed
    def operation(value: object, *, fail: bool) -> object:
        """Example operation."""
        if fail:
            raise error
        return value

    with caplog.at_level(logging.DEBUG, logger=__name__):
        if raises:
            with pytest.raises(ValueError) as caught:
                operation(result, fail=True)
            assert caught.value is error
        else:
            assert operation(result, fail=False) is result

    assert operation.__name__ == "operation"
    assert operation.__doc__ == "Example operation."
    assert caplog.messages == ["operation took 2.50s"]
