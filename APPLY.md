# Production hardening - how to apply

From the repository root, copy these files over your checkout (same paths):

    backend/sandbox.py                 (new)
    backend/security/middleware.py     (replaces)
    tests/test_sandbox.py              (new)
    tests/test_hardening.py            (new)
    Dockerfile                         (replaces)
    requirements.txt                   (adds gunicorn)

Then run once:

    python apply_python_debugger_patch.py

and:

    ruff check backend tests && pytest -q

Production environment variables
    APP_ENV=production        closes admin/data routes unless a token is set
    ADMIN_TOKEN=<long random> unlocks them via "Authorization: Bearer <token>"
    TRUST_PROXY_HOPS=1        reverse proxies in front of the app (default 1)

Note: the demo UI's Training Hub calls /api/llm/dataset. With APP_ENV=production
that call returns 403 unless the UI sends the token, so leave APP_ENV unset for
the finals demo unless you add the header in UI and UX/app.js.
