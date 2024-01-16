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
