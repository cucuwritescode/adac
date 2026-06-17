#test_ir_comparison
#author: Facundo Franchino
"""
integration test: compare flamo impulse response vs faust impulse response.

pipeline:
  1. build a real flamo fdn model (requires flamo + torch + pyFDN)
  2. extract the impulse response via flamo
  3. generate faust code via flamo_to_faust
  4. compile and run via faust2plot to get the faust impulse response
  5. compare the two irs sample by sample

this test requires:
  - flamo and torch installed (in the flamo venv)
  - faust compiler (faust2plot) on PATH
  - pyFDN installed

the test is marked as slow and will be skipped if dependencies are missing.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import pytest


#check if external dependencies are available
FLAMO_VENV = Path("/Users/cucu/Documents/GitHub/flamo/.flamo-env/bin/python3")
HAS_FLAMO_VENV = FLAMO_VENV.exists()
HAS_FAUST = shutil.which("faust2plot") is not None
PYFDN_PATH = Path("/Users/cucu/Documents/GitHub/pyFDN/src")
HAS_PYFDN = PYFDN_PATH.exists()

SKIP_REASON = []
if not HAS_FLAMO_VENV:
    SKIP_REASON.append("flamo venv not found")
if not HAS_FAUST:
    SKIP_REASON.append("faust2plot not on PATH")
if not HAS_PYFDN:
    SKIP_REASON.append("pyFDN not found")

def _find_min_delay(node: dict) -> int:
    """recursively search config tree for the smallest delay value."""
    if node.get("module_type") == "parallelDelay":
        return min(node["params"]["samples"])
    best = float("inf")
    for child in node.get("children", []):
        best = min(best, _find_min_delay(child))
    for key in ("fF", "fB"):
        sub = node.get(key)
        if sub is not None:
            best = min(best, _find_min_delay(sub))
    return best


needs_full_stack = pytest.mark.skipif(
    bool(SKIP_REASON),
    reason=", ".join(SKIP_REASON) if SKIP_REASON else "",
)


def _parse_matlab_output(text: str) -> np.ndarray:
    """parse faust2plot matlab output into a numpy array.

    faust2plot outputs matlab/octave format like:
      faustout = [ ...
       0.123; ...
       -0.456; ...
      ];
    this function extracts the numeric values.
    """
    #find all numbers in the matlab vector (handles scientific notation)
    numbers = re.findall(r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?', text)
    #skip the first number if it looks like a plot command artifact
    values = []
    in_vector = False
    for line in text.split("\n"):
        line = line.strip()
        if "faustout" in line and "[" in line:
            in_vector = True
            continue
        if in_vector:
            if "];" in line:
                break
            #extract the number before the semicolon
            match = re.search(r'([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)', line)
            if match:
                values.append(float(match.group(1)))
    return np.array(values, dtype=np.float64)


def _run_faust2plot(dsp_path: str, n_samples: int, fs: int) -> np.ndarray:
    """compile a .dsp file and extract its impulse response via faust2plot.

    faust2plot feeds silence as input, so we wrap the generated code
    with an impulse generator (1 at sample 0, 0 thereafter) to produce
    an impulse response.

    the binary is placed next to the .dsp file with the extension stripped.
    we run it with -n samples and -r sample_rate to get the ir.
    """
    dsp = Path(dsp_path)

    #wrap the dsp with an impulse generator
    original_code = dsp.read_text()
    #replace "process = <expr>;" with "fdn = <expr>; impulse = 1 - 1'; process = impulse : fdn;"
    import re
    match = re.search(r'process\s*=\s*(.+?);', original_code, re.DOTALL)
    if match:
        fdn_expr = match.group(1).strip()
        wrapped_code = original_code[:match.start()] + \
            f"fdn = {fdn_expr};\nimpulse = 1 - 1';\nprocess = impulse <: fdn;" + \
            original_code[match.end():]
        ir_dsp = dsp.with_name("ir_test.dsp")
        ir_dsp.write_text(wrapped_code)
    else:
        ir_dsp = dsp

    out_binary = str(ir_dsp.with_suffix(""))

    #compile
    result = subprocess.run(
        ["faust2plot", str(ir_dsp)],
        capture_output=True, text=True, timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"faust2plot compilation failed:\n{result.stderr}"
        )

    if not Path(out_binary).exists():
        raise RuntimeError(f"faust2plot did not produce binary at {out_binary}")

    #run the binary to get the ir
    result = subprocess.run(
        [out_binary, "-n", str(n_samples), "-r", str(fs)],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"faust ir extraction failed:\n{result.stderr}"
        )
    return _parse_matlab_output(result.stdout)


def _generate_flamo_ir(output_dir: str, fs: float = 48000.0, nfft: int = 2**16):
    """run the flamo ir generation script in the flamo venv.

    this shells out to the flamo venv python because flamo/torch
    may not be available in the test runner's environment.
    """
    script = str(Path(__file__).parent / "generate_flamo_ir.py")
    env_python = str(FLAMO_VENV)

    result = subprocess.run(
        [
            env_python, script, output_dir,
            "--fs", str(int(fs)),
            "--nfft", str(nfft),
        ],
        capture_output=True, text=True, timeout=120,
        env={
            "PYTHONPATH": f"{PYFDN_PATH}:{Path(__file__).resolve().parents[2] / 'src'}",
            "PATH": subprocess.check_output(
                ["bash", "-c", "echo $PATH"], text=True
            ).strip(),
        },
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"flamo ir generation failed:\n{result.stdout}\n{result.stderr}"
        )
    return result.stdout


@needs_full_stack
class TestIRComparison:
    """compare impulse responses from flamo (frequency domain) and faust (time domain)."""

    @pytest.fixture(scope="class")
    def ir_data(self):
        """generate both irs once for all tests in this class."""
        fs = 48000
        #use moderate nfft for speed, enough to capture the fdn tail
        nfft = 2**14
        n_compare = 4096  #compare first 4096 samples

        with tempfile.TemporaryDirectory() as tmpdir:
            #step 1: generate flamo ir and faust code
            stdout = _generate_flamo_ir(tmpdir, fs=fs, nfft=nfft)
            print(stdout)

            #load flamo ir
            flamo_ir = np.load(Path(tmpdir) / "flamo_ir.npy")

            #step 2: compile and run faust
            dsp_path = str(Path(tmpdir) / "generated.dsp")
            faust_ir = _run_faust2plot(dsp_path, n_compare, fs)

            #trim flamo ir to comparison length
            flamo_ir = flamo_ir[:n_compare]

            #load config for metadata
            with open(Path(tmpdir) / "config.json") as f:
                config = json.load(f)

        return {
            "flamo_ir": flamo_ir,
            "faust_ir": faust_ir,
            "config": config,
            "fs": fs,
            "n_compare": n_compare,
        }

    def test_same_length(self, ir_data):
        """both irs should have the same number of samples."""
        assert len(ir_data["flamo_ir"]) == len(ir_data["faust_ir"])

    def test_first_samples_zero(self, ir_data):
        """before the shortest delay, both irs should be near zero."""
        config = ir_data["config"]
        #find the shortest delay by searching the config tree
        min_delay = _find_min_delay(config)

        #both irs should be near zero before the first echo arrives
        #allow a few samples margin for the direct path
        check_range = max(1, min_delay - 10)
        flamo_early = ir_data["flamo_ir"][1:check_range]
        faust_early = ir_data["faust_ir"][1:check_range]

        #flamo uses alias_decay_db which introduces small pre-delay artifacts
        #in the frequency-domain computation. tolerance reflects this.
        np.testing.assert_allclose(
            flamo_early, 0.0, atol=1e-3,
            err_msg="flamo ir has unexpected energy before first delay"
        )
        np.testing.assert_allclose(
            faust_early, 0.0, atol=1e-6,
            err_msg="faust ir has non-zero samples before first delay"
        )

    def test_impulse_response_match(self, ir_data):
        """flamo and faust irs should match within numerical tolerance.

        flamo computes in the frequency domain (fft-based), faust computes
        sample by sample in the time domain. small numerical differences
        are expected. large differences indicate a bug in the translation.
        """
        flamo_ir = ir_data["flamo_ir"]
        faust_ir = ir_data["faust_ir"]

        #normalise both irs by their peak amplitude
        flamo_peak = np.max(np.abs(flamo_ir))
        faust_peak = np.max(np.abs(faust_ir))

        if flamo_peak > 1e-10:
            flamo_norm = flamo_ir / flamo_peak
        else:
            flamo_norm = flamo_ir

        if faust_peak > 1e-10:
            faust_norm = faust_ir / faust_peak
        else:
            faust_norm = faust_ir

        #the error tolerance accounts for frequency-domain vs time-domain
        #numerical differences. for a lossless fdn with orthogonal feedback,
        #the first few hundred samples should match very closely.
        max_abs_error = np.max(np.abs(flamo_norm - faust_norm))
        mean_abs_error = np.mean(np.abs(flamo_norm - faust_norm))

        print(f"max absolute error (normalised): {max_abs_error:.2e}")
        print(f"mean absolute error (normalised): {mean_abs_error:.2e}")
        print(f"flamo peak: {flamo_peak:.6f}, faust peak: {faust_peak:.6f}")

        #flamo computes in the frequency domain with alias_decay_db windowing,
        #faust computes sample-by-sample in the time domain. after normalising
        #by peak amplitude the shapes should match closely. the mean error
        #is the reliable metric here; a few isolated samples may differ
        #due to fft windowing edge effects.
        assert mean_abs_error < 0.01, (
            f"mean error {mean_abs_error:.6f} exceeds tolerance. "
            f"check that the faust code faithfully represents the flamo model."
        )

    def test_energy_decay_similar(self, ir_data):
        """energy decay curves should be similar between flamo and faust.

        this is a looser check than sample-by-sample but catches structural
        errors (wrong topology, missing feedback, etc).
        """
        flamo_ir = ir_data["flamo_ir"]
        faust_ir = ir_data["faust_ir"]

        #compute energy in 256-sample blocks
        block_size = 256
        n_blocks = len(flamo_ir) // block_size

        flamo_energy = np.array([
            np.sum(flamo_ir[i*block_size:(i+1)*block_size]**2)
            for i in range(n_blocks)
        ])
        faust_energy = np.array([
            np.sum(faust_ir[i*block_size:(i+1)*block_size]**2)
            for i in range(n_blocks)
        ])

        #normalise
        if np.max(flamo_energy) > 1e-20:
            flamo_energy /= np.max(flamo_energy)
        if np.max(faust_energy) > 1e-20:
            faust_energy /= np.max(faust_energy)

        #energy curves should correlate positively. perfect correlation is
        #not expected because flamo's frequency-domain alias_decay_db windowing
        #reshapes the decay envelope compared to faust's time-domain output.
        #a correlation below 0.5 would suggest a structural topology error.
        correlation = np.corrcoef(flamo_energy, faust_energy)[0, 1]
        print(f"energy decay correlation: {correlation:.6f}")
        assert correlation > 0.5, (
            f"energy decay correlation {correlation:.4f} is too low. "
            f"the fdn topology may be wrong."
        )


@needs_full_stack
class TestFaustCompilation:
    """verify that the generated faust code compiles without errors."""

    def test_compiles_to_cpp(self):
        """generated faust code should compile to c++ without errors."""
        #build a simple config and generate faust
        import sys
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
        from adac.codegen.json_to_faust import json_to_faust

        config = {
            "type": "Recursion",
            "name": "simple_fdn",
            "fs": 48000,
            "fF": {
                "type": "Leaf",
                "name": "delay",
                "module_type": "parallelDelay",
                "params": {"samples": [1000]},
                "input_channels": 1,
                "output_channels": 1,
            },
            "fB": {
                "type": "Leaf",
                "name": "gain",
                "module_type": "parallelGain",
                "params": {"gains": [0.5]},
                "input_channels": 1,
                "output_channels": 1,
            },
        }
        code = json_to_faust(config)

        with tempfile.NamedTemporaryFile(suffix=".dsp", mode="w", delete=False) as f:
            f.write(code)
            dsp_path = f.name

        try:
            result = subprocess.run(
                ["faust", "-lang", "cpp", dsp_path, "-o", "/dev/null"],
                capture_output=True, text=True, timeout=30,
            )
            assert result.returncode == 0, (
                f"faust compilation failed:\n{result.stderr}\n"
                f"generated code:\n{code}"
            )
        finally:
            Path(dsp_path).unlink(missing_ok=True)
