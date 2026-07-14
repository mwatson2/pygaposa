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
