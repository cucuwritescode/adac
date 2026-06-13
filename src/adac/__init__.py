#created by Facundo Franchino March 2026
"""adac: automatic differentiable audio compilation.

compiles trained differentiable audio models to real-time FAUST DSP.
"""

__version__ = "0.1.0"

from adac.codegen.flamo_to_json import flamo_to_json
from adac.codegen.json_to_faust import json_to_faust
from adac.codegen.flamo_to_faust import flamo_to_faust
from adac.hotreload import HotReload
from adac.certificate import certify, write_certificate
from adac.export import export_juce

__all__ = [
    "flamo_to_json", "json_to_faust", "json_to_flamo", "flamo_to_faust",
    "HotReload", "certify", "write_certificate", "export_juce",
]


def __getattr__(name):
    #json_to_flamo needs flamo and torch; everything else runs on
    #numpy alone. loading it lazily keeps `import adac` instant and
    #dependency-light while still exposing the full api at the root.
    if name == "json_to_flamo":
        from adac.codegen.json_to_flamo import json_to_flamo
        return json_to_flamo
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
