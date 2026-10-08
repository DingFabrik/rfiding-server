Setup
=====

Install Dependencies
--------------------

Poetry
^^^^^^

RFIDing uses `Poetry <https://python-poetry.org/>`_ to manage dependencies. To install Poetry, run:

.. code-block:: bash

    pipx install poetry

Database
^^^^^^^^

You can use any database that Django supports. For development a simple SQLite database is sufficient. For production you should use a more powerful database like PostgreSQL or MySQL.

If you choose to use PostgreSQL or MySQL, make sure to create a user and database for the project.

Install the project
-------------------

Clone the repository and install the dependencies:

.. code-block:: bash

    git clone https://github.com/DingFabrik/rfiding-server.git
    cd rfiding-server
    poetry install

Copy the example settings:

.. code-block:: bash

    cp server/rfiding/settings.prod.py server/rfiding/settings.py

The production settings read two secrets from the environment and refuse to
start without them:

- ``DJANGO_SECRET_KEY``: Django's secret key.
- ``SPACE_STATE_SECRET``: the secret clients send (in the ``X-Space-Secret``
  header) to change the space state.

Generate each with ``python -c 'import secrets; print(secrets.token_urlsafe(50))'``.
Also fill in ``ALLOWED_HOSTS`` and ``CSRF_TRUSTED_ORIGINS``, and check the HTTPS
settings if TLS is terminated by a reverse proxy.

Check the configuration, including the parts that need the database (scheduled
tasks, machines using the native API):

.. code-block:: bash

    ./manage.py check --deploy --database default

Besides Django's own security checks, this warns about settings that make
features silently not work in production, such as a per-process cache, email or
Slack notifications without credentials or templates, and qualification expiry
without its periodic tasks.


Services
--------

A complete installation runs these services, which all need to be restarted
after an update:

- the web server (``daphne rfiding.asgi:application``),
- the Celery worker (``celery -A rfiding worker``),
- Celery beat (``celery -A rfiding beat -S django``), if periodic tasks such as
  ``people.tasks.expire_qualifications`` are scheduled in the admin,
- the machine manager (``./manage.py machine_manager``), if
  ``ENABLE_CLIENT_API`` is enabled.

Set ``HEALTH_CHECK_URL`` to the address of the website, then check that all
services are running the installed code:

.. code-block:: bash

    ./manage.py check --deploy --tag services --fail-level WARNING

It fails with an error for every service that is not running or still runs an
older version, so it can be run from a cronjob or a monitoring system. Each
process computes its version from the source code and dependencies when it
starts. If the code is deployed without its source tree, set the same
``RFIDING_BUILD_ID`` environment variable (e.g. the git commit) for all
services and the check instead.
