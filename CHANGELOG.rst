Changelog
=========

All notable changes to package_name will be documented here.

The format is based on `Keep a Changelog`_, and this project adheres to `Semantic Versioning`_.

.. _Keep a Changelog: https://keepachangelog.com/en/1.0.0/
.. _Semantic Versioning: https://semver.org/spec/v2.0.0.html

Categories for changes are: Added, Changed, Deprecated, Removed, Fixed, Security.


Version `0.2.5 <https://github.com/mwatson2/pygaposa/tree/0.2.5>`__
------------------------------------------------------------------

Release date: 2026-07-13.

Security:

- Redact the ``authorization`` (Firebase bearer token) and ``auth`` headers
  before writing request headers to the debug log, so enabling debug logging no
  longer leaks reusable credentials.
- Remove the module-level ``logging.basicConfig(level=logging.DEBUG)`` calls so
  the library no longer forces global debug logging on the consuming
  application.

Fixed:

- Reuse the caller-supplied ``aiohttp`` session for Firebase requests instead of
  letting ``FirebaseApp`` create its own, and close the session on
  ``Gaposa.close()``. Previously a separate Firebase session was created and
  never closed, leaking a session per login/entry.
- Propagate polling failures. ``PollManager.execute()`` no longer swallows every
  exception; if polling keeps failing until the retry limit is reached, the
  originating exception is raised to the caller (so ``Gaposa.update()`` fails
  instead of returning stale/empty data).

Changed:

- ``Gaposa.update()`` no longer fires the per-device listeners by default (bulk
  refreshes accept a ``notifyListeners`` flag). Command-driven polls still
  notify listeners. This avoids publishing a redundant intermediate update per
  device on every scheduled refresh.
