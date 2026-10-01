"""Install the private Piper runtime and verified Lessac voice."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import venv
from urllib.request import urlopen

from dianyi.dictionary.install import RemoteAsset, _ensure_asset, download_verified
from dianyi.dictionary.lookup import default_database_path


PIPER_VERSION = "1.8.0"
PIPER_REQUIREMENTS = (
    f"piper-tts=={PIPER_VERSION}", "onnxruntime==1.30.0", "pathvalidate==3.3.1",
    "numpy==2.5.3", "protobuf==7.36.2", "flatbuffers==25.12.19", "packaging==26.3",
)
VOICE_NAME = "en_US-lessac-medium"
VOICE_REVISION = "c10ece1aade47bb51c153c893d14e5bf8e5b7117"
VOICE_URL = (
    "https://huggingface.co/rhasspy/piper-voices/resolve/"
    f"{VOICE_REVISION}/en/en_US/lessac/medium/"
)
VOICE_ASSETS = {
    f"{VOICE_NAME}.onnx": RemoteAsset(
        VOICE_URL + f"{VOICE_NAME}.onnx", 63_201_294,
        "5efe09e69902187827af646e1a6e9d269dee769f9877d17b16b1b46eeaaf019f",
    ),
    f"{VOICE_NAME}.onnx.json": RemoteAsset(
        VOICE_URL + f"{VOICE_NAME}.onnx.json", 4_885,
        "efe19c417bed055f2d69908248c6ba650fa135bc868b0e6abb3da181dab690a0",
    ),
    "MODEL_CARD": RemoteAsset(
        VOICE_URL + "MODEL_CARD", 351,
        "ce49eb457742208166d399a40cdec2c7fa9db77960930031564ab56f12882645",
    ),
}
PIP_ASSET = RemoteAsset(
    "https://files.pythonhosted.org/packages/f3/6e/"
    "1736e5b4ae2b778ef2f81c47d797de9f891d4d8acb047a24ca37a60294dd/"
    "pip-26.2.1-py3-none-any.whl",
    1_816_632,
    "71138adf1f4ca900cdb7d289c21b7494329f2332b6d85f0e1c42108c0384ed3e",
)


def voice_model_path() -> Path:
    return default_database_path().parent / "voices" / f"{VOICE_NAME}.onnx"


def voice_runtime_path() -> Path:
    """Keep voice dependencies separate from the replaceable app environment."""
    prefix = Path(sys.prefix)
    if prefix.name == "venv" and prefix.parent.name == "dianyi":
        root = prefix.parent
    else:
        root = Path(os.environ.get("DIANYI_PREFIX", Path.home() / ".local")) / "lib/dianyi"
    return root / f"piper-venv-{PIPER_VERSION}"


def install_voice() -> Path:
    """Install CPU-only Piper, retaining no package or voice download cache."""
    runtime = voice_runtime_path()
    python = runtime / "bin/python"
    ready = runtime / ".ready"
    if not python.is_file() or not ready.is_file():
        venv.EnvBuilder(with_pip=False).create(runtime)
        # Run pip directly from its verified wheel, also on Ubuntu without ensurepip.
        with tempfile.TemporaryDirectory(prefix="dianyi-piper-install-") as temporary:
            wheel = download_verified(PIP_ASSET, Path(temporary) / "pip.whl")
            environment = os.environ.copy()
            environment["PYTHONPATH"] = str(wheel)
            subprocess.run(
                [str(python), "-m", "pip", "--isolated", "install",
                 "--index-url", "https://pypi.org/simple", "--no-cache-dir",
                 "--only-binary=:all:", *PIPER_REQUIREMENTS],
                env=environment, check=True,
            )
        subprocess.run([str(python), "-c", "from piper import PiperVoice"], check=True)
        ready.write_text(PIPER_VERSION + "\n", encoding="utf-8")
    model = voice_model_path()
    for name, asset in VOICE_ASSETS.items():
        _ensure_asset(asset, model.parent / name, urlopen)
    return model
