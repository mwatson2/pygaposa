from unittest import mock

import pytest

from pygaposa.firebase import FirebaseApp, Firestore, FirestorePath, pathjoin


def test_init():
    app = mock.MagicMock(spec=FirebaseApp)
    firestore = mock.MagicMock(spec=Firestore)
    path = "test/path"

    fp = FirestorePath(app, firestore, path)

    assert fp.app == app
    assert fp.firestore == firestore
    assert fp.path == path


def test_child():
    app = mock.MagicMock(spec=FirebaseApp)
    firestore = mock.MagicMock(spec=Firestore)
    path = "parent/path"
    child_path = "child/path"

    fp = FirestorePath(app, firestore, path)
    fp_child = fp.child(child_path)

    assert isinstance(fp_child, FirestorePath)
    assert fp_child.path == f"{path}/{child_path}"


def test_sanitize_path():
    app = mock.MagicMock(spec=FirebaseApp)
    path = "unsanitized/path/"

    fp = FirestorePath(app, None, path)
    fp.sanitize_path()

    assert fp.path == path[:-1]  # ensure trailing '/' is removed


@pytest.mark.asyncio
async def test_get():
    app = mock.MagicMock(spec=FirebaseApp)
    firestore = mock.MagicMock(spec=Firestore)
    path = "get/path"

    fp = FirestorePath(app, firestore, path)
    await fp.get()

    # ensures that get() method of the firestore mock was called with correct arguments
    firestore.get.assert_called_once_with(path)


def test_pathjoin_without_slash():
    base = "base"
    path = "path"

    result = pathjoin(base, path)

    assert result == "base/path"


def test_pathjoin_with_slash():
    base = "base/"
    path = "/path/"

    result = pathjoin(base, path)

    assert result == "base/path/"


def test_pathjoin_empty_base():
    base = ""
    path = "path"

    result = pathjoin(base, path)

    assert result == "/path"


def test_pathjoin_empty_path():
    base = "base"
    path = ""

    result = pathjoin(base, path)

    assert result == "base"
