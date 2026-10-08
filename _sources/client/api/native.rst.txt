.. index::
    single: ESPHome
    single: Native API

ESPHome native API
==================

Machines that have an **Encryption Key** and an **IP-Address** set speak the
`ESPHome native API <https://esphome.io/components/api/>`_. The rfiding server
keeps a connection to every such machine open (unless the machine is
*Inactive*), reconnects whenever it drops, and uses it for both directions:

* the website shows the machine's live state and logs and sends commands,
* the machine checks access, loads its configuration and reports events.

The HTTP API (:doc:`v2`) stays available as a fallback, e.g. while the server
is not connected yet.

Running it
----------

The connections live in a separate process:

.. code-block:: shell

   ./manage.py machine_manager

The website and the manager talk through the channels layer, so
``CHANNEL_LAYERS`` must point at Redis (``channels_redis``) in every process.
``InMemoryChannelLayer`` only works inside a single process. Set
``ENABLE_CLIENT_API = True`` to let the website use the manager.

Saving a machine tells the manager right away: it connects, disconnects or
reconnects when the address, keys or state change, and pushes the new
configuration to the machine when only that changed. It also re-reads all
machines every minute, which catches anything else that changed.

Verifying the server
--------------------

Anyone with the encryption key can connect to a machine, Home Assistant for
example. To know that a connection comes from the rfiding server, the machine
checks that the server knows its **API Key**:

#. When a client with ``client_info`` ``rfiding-server`` connects, the machine
   publishes a random challenge in the ``rfiding challenge`` text sensor and
   turns ``rfiding server verified`` off.
#. The server calls the ``rfiding_authenticate`` action with
   ``signature = hex(HMAC-SHA256(api_key, "rfiding-server:" + challenge))``.
#. The machine computes the same value and, if it matches, turns
   ``rfiding server verified`` on. The server sees that and shows the machine as
   verified on the website.

When the server disconnects, the machine starts over with a new challenge.
Machines without an API key cannot verify the server. They still connect, but
the website shows them as *Unverified*.

Test vector: key ``secret``, challenge ``0123456789abcdef`` gives
``edb17743faceece62694a2c3b77480e908df9041bb0c05594084dcaa6b0e73da``.

Actions on the machine
----------------------

The server calls these ``api: actions:`` on the machine:

``rfiding_authenticate(signature: string)``
   See above. Must answer with ``api.respond`` (``supports_response: status``).

``set_config(config: string)``
   The configuration as JSON, the same object ``/api/v2/machine/config``
   returns. Pushed after every connect and whenever it changes.

``enable``, ``disable``, ``restart``, ``reload_config``
   Commands sent from the website or ``/api/v2/machine/control``. If the
   machine has ``set_config``, *Reload Config* pushes the configuration
   instead of calling ``reload_config``.

Entities the server reads: ``device_state``, ``current_power_consumption``,
``error_message``, ``rfiding_challenge`` and ``rfiding_server_verified``.

Requests from the machine
-------------------------

The machine sends requests with ``homeassistant.action``. The server answers
calls with ``capture_response: true`` with a JSON object. All values in
``data`` are strings.

``rfiding.check_access``
   ``data``: ``token``, optional ``compartment``.
   Response: ``{"access": true, "workingtime": 3600, "end_time": "23:59:59"}``
   or ``{"access": false, "error": "No Access!"}``. A denied access is a
   successful call; ``on_error`` only runs if the request itself failed.

``rfiding.config``
   ``data``: optional ``firmware_version`` and ``ip_address``, stored on the
   machine. Response: the configuration. Logged as a boot.

``rfiding.disabled``
   ``data``: optional ``compartment``. Logs that the machine was locked again.

ESPHome sends ``homeassistant.action`` calls to **every** connected client that
subscribed to them, and the first answer wins. Only send requests while
``rfiding server verified`` is on, and don't let Home Assistant connect to
rfiding machines with "Allow the device to perform Home Assistant actions"
enabled.

Firmware
--------

``docs/client/esphome/rfiding-native-api.yaml`` is a ready-made package for
ESPHome 2025.10 or newer that implements all of the above. It replaces
``components/api.yaml`` and needs the ``rfiding_api_key`` substitution. Route
the RFID access check through it while the server is verified, and fall back to
HTTP otherwise:

.. code-block:: yaml

   - if:
       condition:
         binary_sensor.is_on: rfiding_server_verified
       then:
         - script.execute:
             id: rfiding_api_check_access
             token_id: !lambda return token_id;
             compartment: ""
       else:
         # existing http_request.get to /api/v2/machine/check
