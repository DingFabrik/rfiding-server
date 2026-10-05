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

