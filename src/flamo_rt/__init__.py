#created by Facundo Franchino March 2026
"""flamo-rt: Real-time deployment of FLAMO audio graphs via FAUST."""

__version__ = "0.1.0"

from flamo_rt.codegen.flamo_to_json import flamo_to_json
from flamo_rt.codegen.json_to_faust import json_to_faust
from flamo_rt.codegen.flamo_to_faust import flamo_to_faust

try:
    from flamo_rt.codegen.json_to_flamo import json_to_flamo
except ImportError:
    pass

__all__ = ["flamo_to_json", "json_to_faust", "flamo_to_faust", "json_to_flamo"]
