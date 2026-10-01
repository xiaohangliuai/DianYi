"""Private stdin/stdout worker; launched with the isolated Piper interpreter."""

from __future__ import annotations

import re
import subprocess
import sys


def main() -> None:
    from piper import PiperVoice

    model_path, player = sys.argv[1:]
    voice = PiperVoice.load(model_path)
    for line in sys.stdin:
        word = line.rstrip("\n")
        if re.fullmatch(r"[A-Za-z]+(?:['’\-][A-Za-z]+)*", word) is None:
            print("error", flush=True)
            continue
        try:
            audio = b"".join(chunk.audio_int16_bytes for chunk in voice.synthesize(word))
            subprocess.run(
                [player, "-q", "-t", "raw", "-f", "S16_LE", "-c", "1",
                 "-r", str(voice.config.sample_rate)],
                input=audio, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                timeout=15, check=True,
            )
        except Exception:
            # Never include the selected word in diagnostic output.
            print("error", flush=True)
        else:
            print("ok", flush=True)
        finally:
            word, line, audio = "", "", b""


if __name__ == "__main__":
    main()
