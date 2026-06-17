#generate_flamo_ir.py
#author: Facundo Franchino
"""
generate an impulse response from a flamo fdn model and export the json config.

this script must run in an environment with flamo and torch installed.
it builds a 4-channel fdn, extracts the ir, and writes:
  - config.json: the flamo_to_json output
  - flamo_ir.npy: the impulse response as a numpy array

usage: python generate_flamo_ir.py <output_dir> [--fs 48000] [--n_samples 4096]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

#add adac src to path so we can import flamo_to_json
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from adac.codegen.flamo_to_json import flamo_to_json


def build_fdn(N: int, fs: float, nfft: int):
    """build a standard N-channel fdn directly from flamo primitives.

    avoids pyFDN's dss_to_flamo to sidestep version mismatches
    with the dtype kwarg. constructs the same graph structure:
    Shell(Parallel(Series(B, Recursion(delays, A), C), D))
    """
    from collections import OrderedDict

    import torch
    from flamo.processor import dsp, system

    device = torch.device("cpu")

    #prime delay lengths for maximal diffusion
    delay_samples = np.array([1103, 1447, 1811, 2137][:N])
    delays_sec = delay_samples / fs

    #hadamard feedback matrix (normalised, orthogonal, lossless)
    A = 0.5 * np.array([
        [1,  1,  1,  1],
        [1, -1,  1, -1],
        [1,  1, -1, -1],
        [1, -1, -1,  1],
    ], dtype=np.float64)[:N, :N]

    B = np.ones((N, 1), dtype=np.float64)
    C = np.ones((1, N), dtype=np.float64) / N
    D = np.zeros((1, 1), dtype=np.float64)

    #build delay module
    max_len = int(np.ceil(np.max(delays_sec) * fs))
    adb = 60.0  #alias decay in db to regularise frequency-domain solve
    delays = dsp.parallelDelay(
        size=(N,), max_len=max_len, nfft=nfft, isint=True,
        unit=1, fs=fs, alias_decay_db=adb, device=device,
    )
    delays.assign_value(torch.as_tensor(delays_sec, dtype=torch.float32, device=device))

    #build gain modules
    def make_gain(values):
        values = np.asarray(values, dtype=np.float64)
        if values.ndim == 1:
            values = values.reshape(-1, 1)
        n_out, n_in = values.shape
        g = dsp.Gain(size=(n_out, n_in), nfft=nfft, alias_decay_db=adb, device=device)
        g.assign_value(torch.as_tensor(values, dtype=torch.float32, device=device))
        return g

    #scale feedback matrix slightly below unity to ensure contractiveness
    #this avoids singular I - A at dc in the frequency-domain solve
    gain_A = make_gain(0.999 * A)
    gain_B = make_gain(B)
    gain_C = make_gain(C)
    gain_D = make_gain(D)

    #assemble the graph
    feedback_loop = system.Recursion(fF=delays, fB=gain_A)
    fdn_branch = system.Series(OrderedDict({
        "input_gain": gain_B,
        "feedback_loop": feedback_loop,
        "output_gain": gain_C,
    }))
    core = system.Parallel(brA=fdn_branch, brB=gain_D, sum_output=True)
    model = system.Shell(
        core=core,
        input_layer=dsp.FFT(nfft),
        output_layer=dsp.iFFT(nfft),
    )

    return model, delay_samples


def get_impulse_response(model, nfft: int):
    """extract the time-domain impulse response from a flamo shell model."""
    import torch
    ir = model.get_time_response()
    #ir shape: (batch, nfft, n_out, n_in) or similar
    #squeeze to (nfft,) for single-in single-out
    ir_np = ir.detach().cpu().numpy().real
    #flatten to 1d: take the (0,0) input-output pair
    if ir_np.ndim == 4:
        ir_np = ir_np[0, :, 0, 0]
    elif ir_np.ndim == 3:
        ir_np = ir_np[0, :, 0]
    elif ir_np.ndim == 2:
        ir_np = ir_np[0, :]
    return ir_np


def main():
    parser = argparse.ArgumentParser(description="generate flamo fdn impulse response")
    parser.add_argument("output_dir", type=str, help="directory to write outputs")
    parser.add_argument("--fs", type=float, default=48000.0, help="sample rate")
    parser.add_argument("--n-channels", type=int, default=4, help="fdn order")
    parser.add_argument("--nfft", type=int, default=2**16, help="fft size")
    args = parser.parse_args()

    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)

    model, delay_samples = build_fdn(args.n_channels, args.fs, args.nfft)

    #extract impulse response
    ir = get_impulse_response(model, args.nfft)
    np.save(out / "flamo_ir.npy", ir)

    #export json config
    config = flamo_to_json(model, args.fs, name="IntegrationTest")
    with open(out / "config.json", "w") as f:
        json.dump(config, f, indent=2)

    #also write the faust code
    from adac.codegen.json_to_faust import json_to_faust
    faust_code = json_to_faust(config)
    with open(out / "generated.dsp", "w") as f:
        f.write(faust_code)

    print(f"wrote {len(ir)} samples to {out / 'flamo_ir.npy'}")
    print(f"wrote config to {out / 'config.json'}")
    print(f"wrote faust to {out / 'generated.dsp'}")
    print(f"delay samples: {delay_samples.tolist()}")
    print(f"ir max: {np.max(np.abs(ir)):.6f}")


if __name__ == "__main__":
    main()
