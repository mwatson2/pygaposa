from unittest.mock import AsyncMock, Mock

import aiohttp

from pygaposa.gaposa import Gaposa


async def test_supplied_session_is_shared_and_not_closed():
    """A caller-supplied session is reused for Firebase and left open on close."""
    session = aiohttp.ClientSession()
    try:
        gaposa = Gaposa("api-key", websession=session)

        assert gaposa.session is session
        assert gaposa.ownSession is False
        # Firebase must reuse the same session rather than creating its own.
        assert gaposa.firebase.session is session
        assert gaposa.firebase.ownSession is False

        await gaposa.close()
        assert session.closed is False
    finally:
        await session.close()


async def test_own_session_is_shared_with_firebase_and_closed():
    """A self-created session is shared with Firebase and closed on close()."""
    gaposa = Gaposa("api-key")
    session = gaposa.session

    assert gaposa.ownSession is True
    assert gaposa.firebase.session is session

    await gaposa.close()
    assert session.closed is True


async def test_close_finalizes_all_devices():
    """close() must close every device (cancelling their background tasks)."""
    gaposa = Gaposa("api-key")
    session = gaposa.session

    device = Mock()
    device.close = AsyncMock()
    client = Mock()
    client.devices = [device]
    gaposa.clients = [(client, Mock())]

    await gaposa.close()

    device.close.assert_awaited_once()
    assert session.closed is True
