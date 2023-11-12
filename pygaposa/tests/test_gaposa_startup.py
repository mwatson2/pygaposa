import json

import pytest

from pygaposa import Gaposa


@pytest.mark.asyncio
async def test_gaposa_startup():
    g = Gaposa("AIzaSyCBNj_bYZ6VmHU8iNuVmvuj0HQLpv4DTfE")
    await g.login("markwatson@cantab.net", "SfkeYNjdR3H3$UWK")
    await g.update()
    device = g.clients[0][0].devices[0]

    print(json.dumps(device.document))
