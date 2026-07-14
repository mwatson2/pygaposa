import asyncio

from pygaposa.device import Device
from pygaposa.poll_manager import DefaultPollManagerConfig


def make_device(mocker):
    api = mocker.Mock()
    firestore = mocker.Mock()
    logger = mocker.Mock()
    info = {"Serial": "SER123", "Name": "Test Device"}
    return Device(api, firestore, logger, DefaultPollManagerConfig, info)


def minimal_document():
    return {
        "State": {},
        "Info": {},
        "Assistant": {},
        "HeartBeat": {},
        "Uid": "uid",
        "DeletedChannels": [],
        "Channels": {},
        "Rooms": {},
        "Groups": {},
    }


def test_listeners_fire_when_not_suppressed(mocker):
    device = make_device(mocker)
    calls = []
    device.addListener(lambda: calls.append(1))

    device.document = minimal_document()
    device.onDocumentUpdated()

    assert calls == [1]


def test_listeners_suppressed_while_depth_positive(mocker):
    device = make_device(mocker)
    calls = []
    device.addListener(lambda: calls.append(1))
    device.document = minimal_document()

    device.suppressNotifyDepth = 1
    device.onDocumentUpdated()
    assert calls == []

    device.suppressNotifyDepth = 0
    device.onDocumentUpdated()
    assert calls == [1]


async def test_update_brackets_suppression(mocker):
    """update(notifyListeners=False) suppresses only for the duration of the poll."""
    device = make_device(mocker)
    depths = []

    async def fake_poll():
        depths.append(device.suppressNotifyDepth)

    device.pollManager.poll = fake_poll

    await device.update(notifyListeners=False)
    await device.update(notifyListeners=True)

    assert depths == [1, 0]
    assert device.suppressNotifyDepth == 0


async def test_create_background_task_tracks_and_clears(mocker):
    device = make_device(mocker)
    ran = asyncio.Event()

    async def work():
        ran.set()

    task = device.createBackgroundTask(work())
    assert task in device.backgroundTasks

    await task
    await asyncio.sleep(0)  # let the done-callback run

    assert ran.is_set()
    assert task not in device.backgroundTasks


async def test_background_task_failure_is_logged_not_raised(mocker):
    device = make_device(mocker)

    async def boom():
        raise RuntimeError("outage")

    task = device.createBackgroundTask(boom())

    # The failure is captured by the done-callback, not surfaced as an
    # "exception never retrieved" error.
    await asyncio.gather(task, return_exceptions=True)
    await asyncio.sleep(0)

    assert device.logger.error.called
    assert task not in device.backgroundTasks


async def test_close_cancels_background_tasks_and_polling(mocker):
    device = make_device(mocker)
    started = asyncio.Event()

    async def long_running():
        started.set()
        await asyncio.sleep(3600)

    task = device.createBackgroundTask(long_running())
    await started.wait()

    await device.close()
    await asyncio.sleep(0)

    assert task.cancelled()
    assert device.backgroundTasks == set()
    assert device.pollManager.pollingTask is None
