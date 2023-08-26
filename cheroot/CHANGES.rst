.. scm-version-title:: v8.6.0

Significant improvements:

- :issue:`384` via :pr:`385`, :pr:`406`: Exposed type stubs with
  annotations for public API -- by :user:`kasium`.

- :pr:`401` (related to the :pr:`352` effort): Started reusing the
  the ``expriration_interval`` setting as timeout in the low-level
  :py:func:`~select.select` invocation, effectively reducing the system
  load when idle, that is noticeable on low-end hardware systems. On
  Windows OS, due to different :py:func:`~select.select` behavior, the
  effect is less significant and comes with a theoretically decreased
  performance on quickly repeating requests, which has however found
  to be not significant in real world scenarios.
  -- by :user:`MichaIng`.

Internal changes:

- Implemented a manual-trigger-based release workflow.
- Integrated publishing GitHub Releases into the workflow.
- Migrated the docs theme to `Furo <https://pradyunsg.me/furo>`__
  (created by :user:`pradyunsg`).
- Attempted to improve the stability of testing.
- Configured the CI to test the same distribution as will be shipped.
- Improved the linting setup and contributor checklists.
- Stopped running tests under Ubuntu 16.04.
- Tweaked the distribution packages metadata to satisfy strict checks.
- Implemented distribution build reproducibility using a pip constraints
  lock-file.
- Added per-environment lock-files into the tox test environments.

.. scm-version-title:: v8.5.2

- :issue:`358` via :pr:`359`: Fixed a regression from
  :pr:`199` that made the worker threads exit on invalid
  connection attempts and could make the whole server
  unresponsive once there was no workers left.
  -- by :user:`cameronbrunner`.

.. scm-version-title:: v8.5.1

- :cp-issue:`1873` via :pr:`340`: Resurrected an
  unintentionally removed feature of interrupting a server
  main thread by externally assigning an exception to the
  :py:meth:`HTTPServer.interrupt <cheroot.server.\
  HTTPServer.interrupt>` property -- by :user:`liamstask`.

- :pr:`350`: Fixed the incarnation of an earlier regression
  of not resetting the serving state
  on :py:data:`SIGINT` originally fixed by :pr:`322` and
  :pr:`331` but reintroduced by the changes in :pr:`311`
  -- by :user:`liamstask`.

.. scm-version-title:: v8.5.0

- :issue:`305` via :pr:`311`: In
  :py:class:`~cheroot.connections.ConnectionManager`,
  process connections as they become active rather than
  waiting for a ``tick`` event, addressing performance
  degradation introduced in v8.1.0 -- by :user:`liamstask`.

- :issue:`341` via :pr:`342`: Suppress legitimate OS errors
  expected on shutdown -- by :user:`webknjaz`.

.. scm-version-title:: v8.4.8

- :issue:`317` via :pr:`337`: Fixed a regression in
  8.4.5 where the connections dictionary would change
  size during iteration, leading to a :py:exc:`RuntimeError`
  raised in the logs -- by :user:`liamstask`.

.. scm-version-title:: v8.4.7

- :pr:`334`: Started filtering out TLS/SSL errors when
  the version requested by the client is unsupported
  -- by :user:`sanderjo` and :user:`Safihre`.

.. scm-version-title:: v8.4.6

- :issue:`328` via :pr:`322` and :pr:`331`: Fixed a
  regression introduced in the earlier refactoring in v8.4.4
  via :pr:`309` that caused the :py:meth:`~cheroot.server.\
  HTTPServer.serve` method to skip setting
  ``serving=False`` on :py:data:``SIGINT`` and
  :py:data:``SIGTERM`` -- by :user:`marc1n` and
  :user:`cristicbz`.

.. scm-version-title:: v8.4.5

- :issue:`312` via :pr:`313`: Fixed a regression introduced
  in the earlier refactoring in v8.4.4 via :pr:`309` that
  caused the connection manager to modify the selector map
  while looping over it -- by :user:`liamstask`.

- :issue:`312` via :pr:`316`: Added a regression test for
  the error handling in :py:meth:`~cheroot.connections.\
  ConnectionManager.get_conn` to ensure more stability
  -- by :user:`cyraxjoe`.

.. scm-version-title:: v8.4.4

- :issue:`304` via :pr:`309`: Refactored :py:class:`~\
  cheroot.connections.ConnectionManager` to use :py:meth:`~\
  selectors.BaseSelector.get_map` and reorganized the
  readable connection tracking -- by :user:`liamstask`.

- :issue:`304` via :pr:`309`: Fixed the server shutdown
  sequence to avoid race condition resulting in accepting
  new connections while it is being terminated
  -- by :user:`liamstask`.

.. scm-version-title:: v8.4.3

- :pr:`282`: Fixed a race condition happening when an HTTP
  client attempts to reuse a persistent HTTP connection after
  it's been discarded on the server in :py:class:`~cheroot.\
  server.HTTPRequest` but no TCP FIN packet has been received
  yet over the wire -- by :user:`meaksh`.

  This change populates the ``Keep-Alive`` header exposing
  the timeout value for persistent HTTP/1.1 connections which
  helps mitigate such race conditions by letting the client
  know not to reuse the connection after that time interval.

.. scm-version-title:: v8.4.2

- Fixed a significant performance regression introduced in
  v8.1.0 (:issue:`305` via :pr:`308`) - by :user:`mar10`.

  The issue turned out to add 0.1s delay on new incoming
  connection processing. We've lowered that delay to mitigate
  the problem short-term, better fix is yet to come.

.. scm-version-title:: v8.4.1

- Prevent :py:exc:`ConnectionAbortedError` traceback from being
  printed out to the terminal output during the app start-up on
  Windows when built-in TLS adapter is used (:issue:`302` via
  :pr:`306`) - by :user:`mxii-ca`.

.. scm-version-title:: v8.4.0

- Converted management from low-level :py:func:`~select.select` to
  high-level :py:mod:`selectors` (:issue:`249` via :pr:`301`)
  - by :user:`tommilligan`.

  This change also introduces a conditional dependency on
  ``selectors2`` as a fall-back for legacy Python interpreters.

.. scm-version-title:: v8.3.1

- Fixed TLS socket related unclosed resource warnings
  (:pr:`291` and :pr:`298`).
- Made terminating keep-alive connections more graceful
  (:issue:`263` via :pr:`277`).

.. scm-version-title:: v8.3.0

- :cp-issue:`910` via :pr:`243`: Provide TLS-related
  details via WSGI environment interface.
- :pr:`248`: Fix parsing of the ``--bind`` CLI option
  for abstract UNIX sockets.


.. scm-version-title:: v8.2.1

- :cp-issue:`1818`: Restore support for ``None``
  default argument to ``WebCase.getPage()``.


.. scm-version-title:: v8.2.0

- Deprecated use of negative timeouts as alias for
  infinite timeouts in ``ThreadPool.stop``.
- :cp-issue:`1662` via :pr:`74`: For OPTION requests,
  bypass URI as path if it does not appear absolute.


.. scm-version-title:: v8.1.0

- Workers are now request-based, addressing the
  long-standing issue with keep-alive connections
  (:issue:`91` via :pr:`199`).


.. scm-version-title:: v8.0.0

- :issue:`231` via :pr:`232`: Remove custom ``setup.cfg``
  parser handling, allowing the project (including ``sdist``)
  to build/run on setuptools 41.4. Now building cheroot
  requires setuptools 30.3 or later (for declarative
  config support) and preferably 34.4 or later (as
  indicated in ``pyproject.toml``).


.. scm-version-title:: v7.0.0

- :pr:`224`: Refactored "open URL" behavior in
  :py:mod:`~cheroot.test.webtest` to rely on `retry_call
  <https://jaracofunctools.readthedocs.io/en/latest/?badge=latest#jaraco.functools.retry_call>`_.
  Callers can no longer pass ``raise_subcls`` or ``ssl_context``
  positionally, but must pass them as keyword arguments.


.. scm-version-title:: v6.6.0

- Revisit :pr:`85` under :pr:`221`. Now
  ``backports.functools_lru_cache`` is only
  required on Python 3.2 and earlier.
- :cp-issue:`1206` via :pr:`204`: Fix race condition in
  threadpool shrink code.


.. scm-version-title:: v6.5.8

- :issue:`222` via :commit:`621f4ee`: Fix
  :py:const:`socket.SO_PEERCRED` constant fallback value
  under PowerPC.


.. scm-version-title:: v6.5.7

- :issue:`198` via :commit:`9f7affe`: Fix race condition when
  toggling stats counting in the middle of request processing.

- Improve post Python 3.9 compatibility checks.

- Fix support of `abstract namespace sockets
  <https://utcc.utoronto.ca/~cks
  /space/blog/linux/SocketAbstractNamespace>`_.

.. scm-version-title:: v6.5.6

- :issue:`218` via :pr:`219`: Fix HTTP parser to return 400 on
  invalid major-only HTTP version in Request-Line.


.. scm-version-title:: v6.5.5

- :issue:`99` via :pr:`186`: Sockets now collect statistics (bytes
  read and written) on Python 3 same as Python 2.

- :cp-issue:`1618` via :pr:`180`: Ignore OpenSSL's 1.1+ Error 0
  under any Python while wrapping a socket.


.. scm-version-title:: v6.5.4

- :issue:`113`: Fix :py:mod:`cheroot.ssl.pyopenssl`
  under Python 3.

- :issue:`154` via :pr:`159`: Remove custom license field from
  dist metadata.

- :issue:`95`: Fully integrate :py:mod:`trustme` into all TLS tests.
  Also remove all hardcoded TLS certificates.

- :issue:`42`: Remove traces of :py:mod:`unittest` and
  :py:mod:`ddt` usage.

- Fix invalid input processing in
  :py:func:`cheroot._compat.extract_bytes`.

- Fix returning error explanation over plain HTTP for PyOpenSSL.

- Add a fallback for :py:func:`os.lchmod` where it's missing.

- Avoid traceback for invalid client cert with builtin
  :py:mod:`ssl` adapter.

- Avoid deprecation warning with :py:class:`OpenSSL.SSL.Connection`.

- Fix socket wrapper in PyOpenSSL adapter.

- Improve tests coverage:

  * Client TLS certificate tests

  * :py:func:`cheroot._compat.extract_bytes`

  * ``PEERCREDS`` lookup


.. scm-version-title:: v6.5.3

- :pr:`149`: Make ``SCRIPT_NAME`` optional per PEP 333.


.. scm-version-title:: v6.5.2

- :issue:`6` via :pr:`109`: Fix import of
  :py:mod:`cheroot.ssl.pyopenssl` by refactoring and separating
  :py:mod:`cheroot.makefile`'s stream wrappers.

- :issue:`95` via :pr:`109`: Add initial tests for SSL layer with use
  of :py:mod:`trustme`


.. scm-version-title:: v6.5.1

- :issue:`93` via :pr:`110`: Improve UNIX socket FS access mode
  in :py:meth:`cheroot.server.HTTPServer.prepare` on a file socket
  when starting to listen to it.


.. scm-version-title:: v6.5.0

- :cp-issue:`1001` via :pr:`52` and :pr:`108`: Add support for
  validating client certificates.


.. scm-version-title:: v6.4.0

- :issue:`68` via :pr:`98`: Factor out parts of
  :py:meth:`cheroot.server.HTTPServer.start` into
  :py:meth:`prepare() <cheroot.server.HTTPServer.prepare>` and
  :py:meth:`serve() <cheroot.server.HTTPServer.serve>`


.. scm-version-title:: v6.3.3

- Fix bug with returning empty result in
  :py:meth:`cheroot.ssl.builtin.BuiltinSSLAdapter.wrap`


.. scm-version-title:: v6.3.2

- :issue:`100` via :pr:`101`: Respond with HTTP 400 to malicious
  ``Content-Length`` in request headers.


.. scm-version-title:: v6.3.1

- :cp-issue:`1618`: Ignore OpenSSL's 1.1+ Error 0 under Python 2 while
  wrapping a socket.


.. scm-version-title:: v6.3.0

- :pr:`87`: Add ``cheroot`` command and runpy launcher to
  launch a WSGI app from the command-line.


.. scm-version-title:: v6.2.4

- Fix missing ``resolve_peer_creds`` argument in
  :py:class:`cheroot.wsgi.Server` being bypassed into
  :py:class:`cheroot.server.HTTPServer`.

- :pr:`85`: Revert conditional dependencies. System packagers should
  honor the dependencies as declared by cheroot, which are defined
  intentionally.


.. scm-version-title:: v6.2.3

- :pr:`85`: Skip installing dependencies from backports namespace under
  Python 3.


.. scm-version-title:: v6.2.2

- :issue:`84` (:cp-issue:`1704`): Fix regression, causing
  :py:exc:`ModuleNotFoundError` under ``cygwin``.


.. scm-version-title:: v6.2.1

- :pr:`83`: Fix regression, caused by inverted check for Windows OS.

- Add more URLs to distribution metadata


.. scm-version-title:: v6.2.0

- :pr:`37`: Implement PEERCRED lookup over UNIX-socket HTTP connection.

  * Discover connected process' PID/UID/GID

  * Respect server switches: ``peercreds_enabled`` and
    ``peercreds_resolve_enabled``

  * ``get_peer_creds`` and ``resolve_peer_creds``  methods on connection

  * ``peer_pid``, ``peer_uid``, ``peer_gid``, ``peer_user`` and ``peer_group``
    properties on connection

  * ``X_REMOTE_PID``, ``X_REMOTE_UID``, ``X_REMOTE_GID``, ``X_REMOTE_USER``
    (``REMOTE_USER``) and ``X_REMOTE_GROUP`` WSGI environment variables when
    enabled and supported

  * Per-connection caching to reduce lookup cost


.. scm-version-title:: v6.1.2

- :issue:`81`: Fix regression introduced by :pr:`80`.

  * Restore :py:attr:`storing bound socket
    <cheroot.server.HTTPServer.bind_addr>` in Windows broken by use of
    :py:obj:`socket.AF_UNIX`


.. scm-version-title:: v6.1.1

- :pr:`80`: Fix regression introduced by :commit:`68a5769`.

  * Get back support for :py:obj:`socket.AF_UNIX` in stored bound address in
    :py:attr:`cheroot.server.HTTPServer.bind_addr`


.. scm-version-title:: v6.1.0

- :pr:`67`: Refactor test suite to completely rely on pytest.

  * Integrate ``pytest-testmon`` and ``pytest-watch``

  * Stabilize testing

- :cp-issue:`1664` via :pr:`66`: Implement input termination flag support as
  suggested by `@mitsuhiko <https://github.com/mitsuhiko>`_ in his
  `wsgi.input_terminated Proposal
  <https://gist.github.com/mitsuhiko/5721547>`_.

- :issue:`73`: Fix SSL error bypassing.

- :issue:`77` via :pr:`78`: Fix WSGI documentation example to support Python 3.

- :pr:`76`: Send correct conditional HTTP error in helper function.

- :cp-issue:`1404` via :pr:`75`: Fix headers being unsent before request
  closed. Now we double check that they've been sent.

- Minor docs improvements.

- Minor refactoring.


.. scm-version-title:: v6.0.0

- Drop support for Python 2.6, 3.1, 3.2, and 3.3.

- Also drop built-in SSL support for Python 2.7 earlier
  than 2.7.9.


.. scm-version-title:: v5.11.0

- :cp-issue:`1621`: To support :py:mod:`~cheroot.test.webtest`
  applications that feed absolute URIs to
  :py:meth:`~cheroot.test.webtest.WebCase.getPage`
  but expect the scheme/host/port to be ignored (as cheroot 5.8
  and earlier did), provide a ``strip_netloc`` helper and recipe
  for calling it in a subclass.


.. scm-version-title:: v5.10.0

- Minor refactorings of ``cheroot/server.py`` to reduce redundancy
  of behavior.

- Delinting with fewer exceptions.

- Restored license to BSD.


.. scm-version-title:: v5.9.2

- :issue:`61`: Re-release without spurious files in the distribution.


.. scm-version-title:: v5.9.1

- :issue:`58`: Reverted encoding behavior in wsgi module to correct
  regression in CherryPy tests.


.. scm-version-title:: v5.9.0

- :cp-issue:`1088` and :pr:`53`: Avoid using SO_REUSEADDR on Windows
  where it has different semantics.

- ``cheroot.tests.webtest`` adopts the one method that was unique
  in CherryPy, now superseding the implementation there.

- Substantial cleanup around compatibility functions
  (:py:mod:`~cheroot._compat` module).

- License unintentionally changed to MIT. BSD still declared and intended.


.. scm-version-title:: v5.8.3

- Improve HTTP request line validation:

  * Improve HTTP version parsing

- Fix HTTP CONNECT method processing:

  * Respond with ``405 Method Not Allowed`` if ``proxy_mode is False``

  * Validate that request-target is in authority-form

- Improve tests in ``test.test_core``

- :pr:`44`: Fix EPROTOTYPE @ Mac OS


.. scm-version-title:: v5.8.2

- Fix :pr:`39` regression. Add HTTP request line check:
  absolute URI path must start with a
  forward slash ("/").


.. scm-version-title:: v5.8.1

- CI improvements:

  * Add basic working Circle CI v2 config

- Fix URI encoding bug introduced in :pr:`39`

  * Improve :py:class:`cheroot.test.helper.Controller` to properly match
    Unicode


.. scm-version-title:: v5.8.0

- CI improvements:

  * Switch to native PyPy support in Travis CI

  * Take into account :pep:`257` compliant modules

  * Build wheel in AppVeyor and store it as an artifact

- Improve urllib support in :py:mod:`cheroot._compat`

- :issue:`38` via :pr:`39`: Improve URI parsing:

  * Make it compliant with :rfc:`7230`, :rfc:`7231` and :rfc:`2616`

  * Fix setting of ``environ['QUERY_STRING']`` in WSGI

  * Introduce ``proxy_mode`` and ``strict_mode`` argument in ``server.HTTPRequest``

  * Fix decoding of Unicode URIs in WSGI 1.0 gateway


.. scm-version-title:: v5.7.0

- CI improvements:

  * Don't run tests during deploy stage

  * Use VM based build job environments only for ``pyenv`` environments

  * Opt-in for beta trusty image @ Travis CI

  * Be verbose when running tests (show test names)

  * Show ``xfail``/skip details during test run

- :issue:`34`: Fix ``_handle_no_ssl`` error handler calls

- :issue:`21`: Fix ``test_conn`` tests:

  * Improve setup_server def in HTTP connection tests

  * Fix HTTP streaming tests

  * Fix HTTP/1.1 pipelining test under Python 3

  * Fix ``test_readall_or_close`` test

  * Fix ``test_No_Message_Body``

  * Clarify ``test_598`` fail reason

- :issue:`36`: Add GitHub templates for PR, issue && contributing

- :issue:`27`: Default HTTP Server header to Cheroot version str

- Cleanup :py:mod:`~cheroot._compat` functions from server module


.. scm-version-title:: v5.6.0

- Fix all :pep:`257` related errors in all non-test modules.

  ``cheroot/test/*`` folder is only one left allowed to fail with this linter.

- :cp-issue:`1602` and :pr:`30`: Optimize chunked body reader loop by returning
  empty data is the size is 0.

- :cp-issue:`1486`: Reset buffer if the body size is unknown

- :cp-issue:`1131`: Add missing size hint to SizeCheckWrapper


.. scm-version-title:: v5.5.2

- :pr:`32`: Ignore ``"unknown error"`` and ``"https proxy request"``
  SSL errors.

  Ref: :gh:`sabnzbd/sabnzbd#820 <sabnzbd/sabnzbd/issues/820>`

  Ref: :gh:`sabnzbd/sabnzbd#860 <sabnzbd/sabnzbd/issues/860>`


.. scm-version-title:: v5.5.1

- Make AppVeyor list separate tests in corresponding tab.

- :pr:`29`: Configure Travis CI build stages.

  Prioritize tests by stages.

  Move deploy stage to be run very last after all other stages finish.

- :pr:`31`: Ignore "Protocol wrong type for socket" (EPROTOTYPE) @ OSX for non-blocking sockets.

  This was originally fixed for regular sockets in :cp-issue:`1392`.

  Ref: https://forums.sabnzbd.org/viewtopic.php?f=2&t=22728&p=112251


.. scm-version-title:: v5.5.0

- :issue:`17` via :pr:`25`: Instead of a read_headers function, cheroot now
  supplies a :py:class:`HeaderReader <cheroot.server.HeaderReader>` class to
  perform the same function.

  Any :py:class:`HTTPRequest <cheroot.server.HTTPRequest>` object may override
  the header_reader attribute to customize the handling of incoming headers.

  The server module also presents a provisional implementation of
  a :py:class:`DropUnderscoreHeaderReader
  <cheroot.server.DropUnderscoreHeaderReader>` that will exclude any headers
  containing an underscore. It remains an exercise for the
  implementer to demonstrate how this functionality might be
  employed in a server such as CherryPy.

- :pr:`26`: Configured TravisCI to run tests under OS X.


.. scm-version-title:: v5.4.0

- :pr:`22`: Add "ciphers" parameter to SSLAdapter.


.. scm-version-title:: v5.3.0

- :pr:`8`: Updated style to better conform to :pep:`8`.

  Refreshed project with `jaraco skeleton
  <https://github.com/jaraco/skeleton>`_.

  Docs now built and `deployed at RTD
  <https://cheroot.cherrypy.dev/en/latest/history.html>`_.


.. scm-version-title:: v5.2.0

- :issue:`5`: Set ``Server.version`` to Cheroot version instead of CherryPy
  version.

- :pr:`4`: Prevent tracebacks and drop bad HTTPS connections in the
  ``BuiltinSSLAdapter``, similar to ``pyOpenSSLAdapter``.

- :issue:`3`: Test suite now runs and many tests pass. Some are still failing.


.. scm-version-title:: v5.1.0

- Removed the WSGI prefix from classes in :py:mod:`cheroot.wsgi`. Kept aliases
  for compatibility.

- :issue:`1`: Corrected docstrings in :py:mod:`cheroot.server` and
  :py:mod:`cheroot.wsgi`.

- :pr:`2`: Fixed :py:exc:`ImportError` when pkg_resources cannot find the
  cheroot distribution.


.. scm-version-title:: v5.0.1

- Fix error in ``parse_request_uri`` created in :commit:`68a5769`.


.. scm-version-title:: v5.0.0

- Initial release based on :gh:`cherrypy.cherrypy.wsgiserver 8.8.0
  <cherrypy/cherrypy/tree/v8.8.0/cherrypy/wsgiserver>`.
