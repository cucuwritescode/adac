=============
API Reference
=============

Every public symbol is reachable from the top-level ``adac`` namespace:

.. code-block:: python

   import adac
   faust_code = adac.flamo_to_faust(model, fs=48000, name="MyReverb")

----

Compiler
--------

The codegen core: traverse a model, serialise to JSON, emit FAUST, and
reconstruct a model from a config.

.. autosummary::
   :toctree: generated/
   :nosignatures:

   adac.flamo_to_faust
   adac.flamo_to_json
   adac.json_to_faust
   adac.json_to_flamo

Hot reload
----------

.. autosummary::
   :toctree: generated/
   :nosignatures:

   adac.HotReload

Stability certificate
---------------------

.. autosummary::
   :toctree: generated/
   :nosignatures:

   adac.certify
   adac.write_certificate

Export
------

.. autosummary::
   :toctree: generated/
   :nosignatures:

   adac.export_juce
