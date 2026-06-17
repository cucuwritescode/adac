============
Installation
============

From source
-----------

Clone the repository and install in editable mode:

.. code-block:: console

   $ git clone https://github.com/cucuwritescode/adac
   $ cd adac
   $ pip install -e .

The core compiler runs on numpy alone, so ``import adac`` stays light and the
JSON and FAUST stages need nothing further.

Full FLAMO support
------------------

Reconstructing a FLAMO model from a config, and traversing a live model, needs
PyTorch and FLAMO:

.. code-block:: console

   $ pip install -e ".[full]"

Building plugins
----------------

Emitting and building plugins additionally requires the
`FAUST <https://faust.grame.fr>`_ distribution and, for the JUCE export path,
`JUCE <https://juce.com>`_. These are external toolchains, installed separately
from the Python package.
