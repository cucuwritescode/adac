.. adac documentation master file

====
adac
====

Automatic differentiable audio compilation

``adac`` compiles trained differentiable audio models to real-time DSP. It
traverses a `FLAMO <https://github.com/gdalsanto/flamo>`_ model graph, extracts
every parameter, serialises them to a JSON intermediate representation, and
emits valid `FAUST <https://faust.grame.fr>`_ source. From there a model reaches
a variety of hardware and software targets, plugins among them, with no manual
reimplementation.

----

.. grid:: 2
   :gutter: 4

   .. grid-item-card:: Installation
      :link: installation
      :link-type: doc

      How to install ``adac`` and the optional FLAMO and FAUST toolchains.

   .. grid-item-card:: Quick Start
      :link: quickstart
      :link-type: doc

      Compile a model to FAUST, hear it train, and ship it as a plugin.

   .. grid-item-card:: API Reference
      :link: api_reference
      :link-type: doc

      The complete top-level ``adac`` namespace: the compiler, hot-reload,
      certificate, and export.

   .. grid-item-card:: Source
      :link: https://github.com/cucuwritescode/adac

      The repository, issue tracker, and examples on GitHub.


.. toctree::
   :hidden:

   installation
   quickstart
   api_reference
