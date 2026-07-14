Changelog
=========

All notable changes to package_name will be documented here.

The format is based on `Keep a Changelog`_, and this project adheres to `Semantic Versioning`_.

.. _Keep a Changelog: https://keepachangelog.com/en/1.0.0/
.. _Semantic Versioning: https://semver.org/spec/v2.0.0.html

Categories for changes are: Added, Changed, Deprecated, Removed, Fixed, Security.


Version `0.2.7 <https://github.com/mwatson2/pygaposa/tree/0.2.7>`__
------------------------------------------------------------------

Release date: 2026-07-14.

Security:

- Do not log Firebase request URLs verbatim. ``FirebaseAuth.sign_in``,
  ``FirebaseAuth.refresh_id_token`` and ``Firestore._get`` previously logged the
  raw ``ClientResponse`` at debug level; the sign-in and token-refresh URLs
  include ``?key=<api key>``, so enabling debug logging leaked the configured
  Firebase API key. These now log only the method, query-stripped URL and
  status.

Fixed:

- Make polling cancellation-safe. When a caller of ``Device.update()`` /
  ``PollManager.wait_for_condition()`` is cancelled (e.g. an outer timeout
  expires), the waiter is now removed and the detached background polling task
  is cancelled when it was the last waiter. Previously the poll continued in the
  background and could later notify listeners with stale data after the caller
  had given up.


Version `0.2.6 <https://github.com/mwatson2/pygaposa/tree/0.2.6>`__
------------------------------------------------------------------

Release date: 2026-07-14.

Fixed:

- Track and finalize fire-and-forget command-poll tasks. ``Motor``/``Group``
  commands issued with ``waitForUpdate=False`` previously created untracked
  ``asyncio`` tasks. These are now tracked on the device, their failures are
  logged instead of surfacing as "Task exception was never retrieved" errors
  (which could otherwise occur during an outage now that polling failures
  propagate), and they are cancelled by ``Gaposa.close()`` so nothing keeps
  polling after shutdown.
- ``Gaposa.close()`` now cancels each device's outstanding background tasks and
  stops its polling before closing the session. ``PollManager`` gained a
  ``close()`` method to support this.


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
