import asyncio
from logging import Logger
from unittest.mock import AsyncMock, MagicMock

import pytest

from pygaposa.poll_manager import PollMagagerConfig, PollManager


@pytest.fixture
def mock_poll() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_logger() -> Logger:
    return MagicMock()


@pytest.fixture
def poll_manager(mock_poll, mock_logger) -> PollManager:
    config: PollMagagerConfig = {
        "poll_interval": 2,
        "poll_retries": 5,
        "poll_timeout": 10,
    }
    return PollManager(mock_poll, mock_logger, config)


async def test_wait_for_update(poll_manager, mock_poll) -> None:
    await poll_manager.wait_for_update()
    mock_poll.assert_awaited_once()


async def test_wait_for_condition(poll_manager, mock_poll) -> None:
    condition = MagicMock(return_value=True)
    await poll_manager.wait_for_condition(condition)
    mock_poll.assert_awaited_once()
    condition.assert_called_once()


async def test_wait_for_condition_with_timeout(poll_manager, mock_poll) -> None:
    condition = MagicMock(return_value=False)
    await poll_manager.wait_for_condition(condition)
    mock_poll.assert_awaited()
    condition.assert_called()
    assert mock_poll.call_count == 6


async def test_wait_for_condition_three_times(poll_manager, mock_poll) -> None:
    condition = MagicMock(side_effect=[False, False, True])
    await poll_manager.wait_for_condition(condition)
    assert mock_poll.await_count == 3
    condition.assert_called_with()


async def test_wait_for_update_propagates_poll_failure(poll_manager, mock_poll) -> None:
    """A poll that keeps failing must raise, not silently complete."""
    mock_poll.side_effect = RuntimeError("network down")

    with pytest.raises(RuntimeError, match="network down"):
        await poll_manager.wait_for_update()

    # Polled the initial attempt plus every retry before giving up.
    assert mock_poll.await_count == poll_manager.poll_retries + 1


async def test_wait_for_condition_recovers_after_transient_failure(
    poll_manager, mock_poll
) -> None:
    """A poll that fails once then succeeds should complete normally."""
    mock_poll.side_effect = [RuntimeError("blip"), None]
    condition = MagicMock(side_effect=[True])

    await poll_manager.wait_for_condition(condition)

    assert mock_poll.await_count == 2


async def test_close_cancels_polling_and_waiters(poll_manager) -> None:
    """close() must stop the polling task and cancel outstanding waiters."""
    started = asyncio.Event()

    async def blocking_poll():
        started.set()
        await asyncio.sleep(3600)

    poll_manager.poll = blocking_poll
    future = poll_manager.add_condition(MagicMock(return_value=False))
    await started.wait()

    await poll_manager.close()

    assert future.cancelled()
    assert poll_manager.pollingTask is None
    assert poll_manager.waiters == []
