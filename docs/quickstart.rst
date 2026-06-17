===========
Quick Start
===========

The whole API lives at the top level of ``adac``.

Compile a model
---------------

Given a trained FLAMO model and a sample rate, one call returns FAUST source:

.. code-block:: python

   import adac

   faust_code = adac.flamo_to_faust(model, fs=48000, name="MyReverb")

   with open("reverb.dsp", "w") as f:
       f.write(faust_code)

For inspection, the two stages are available separately. The intermediate JSON
config is plain data, so it can be examined or edited between the steps:

.. code-block:: python

   config = adac.flamo_to_json(model, fs=48000, name="MyReverb")
   faust_code = adac.json_to_faust(config, controls={"rt60": True, "dry_wet": True})

Hear it while it trains
-----------------------

``HotReload`` republishes the model to a running FAUST plugin during training,
so the optimisation is audible as it runs. Knob positions survive the reloads.

.. code-block:: python

   live = adac.HotReload(fs=48000, name="MyReverb", controls={"rt60": True})
   for step in range(n_steps):
       loss = criterion(model(x), target)
       loss.backward()
       optimiser.step()
       live.update(model)
   live.update(model, force=True)

Certify
-------

``certify`` computes a small-gain stability certificate for every feedback
loop. The verdict is one of ``certified-stable``, ``marginally-stable``,
``indeterminate``, ``not-certified``, or ``unstable``.

.. code-block:: python

   cert = adac.certify(config)
   print(cert["verdict"])

Ship it
-------

``export_juce`` turns a config into an installed plugin in one call, gating on
the certificate. A model whose verdict is unsafe is refused unless
``strict=False`` is passed.

.. code-block:: python

   adac.export_juce(
       adac.flamo_to_json(model, fs=48000, name="MyReverb"),
       "exported/", name="MyReverb",
       controls={"rt60": True, "dry_wet": True, "pre_delay": True},
       juce_modules="~/JUCE/modules",
       build=True,
   )

Runnable versions of these snippets are in the ``examples/`` directory of the
repository.
