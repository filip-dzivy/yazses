"""Latency of personal-vocabulary correction (`postprocess.vocab_correct.correct`).

`correct()` runs on every dictated utterance when `[stt] vocab_correction` is on,
between the decoder and the keyboard, so its cost is added directly to the time
the user waits for text to appear. Its cost grows with two things the user
controls: how long they speak and how large their personal dictionary is.

This bench measures that growth on synthetic, deterministic input — no audio,
no model, no user data — and prints a fingerprint of every output so two runs
(e.g. before and after an optimisation) can be shown to produce *identical*
corrections, not merely faster ones.

    uv sync --group benchmark
    uv run python paper/benchmark/bench_vocab_correct.py            # -> results/vocab-correct.json
    uv run python paper/benchmark/bench_vocab_correct.py --name vocab-correct-baseline
    uv run python paper/benchmark/bench_vocab_correct.py --profile  # cProfile, writes nothing
"""
from __future__ import annotations

import argparse
import cProfile
import hashlib
import io
import pstats
import random
import statistics
import subprocess
import sys
import time

from _common import REPO_ROOT, provenance, write_result

VOCAB_SIZES = (10, 100, 500, 2000)
TRANSCRIPT_WORDS = (20, 200)
SEED = 73  # the issue number of the feature; any fixed value would do

_CONSONANTS = "bcdfgklmnprstvz"
_VOWELS = "aeiou"
_FILLER = (
    "the quick report about our new service is ready and we should deploy "
    "it today after lunch because the team wants feedback from users before "
    "friday so please check the logs and send me a short summary of what "
    "changed in the build pipeline last week"
).split()


def _pseudo_word(rng: random.Random, syllables: int) -> str:
    return "".join(rng.choice(_CONSONANTS) + rng.choice(_VOWELS) for _ in range(syllables))


def make_vocabulary(rng: random.Random, size: int) -> list[str]:
    """Jargon-like terms: capitalised pseudo-words, some multi-word."""
    terms = ["Kubernetes", "PostgreSQL", "YazSes", "kubectl"]
    while len(terms) < size:
        word = _pseudo_word(rng, rng.randint(2, 5)).capitalize()
        if rng.random() < 0.15:
            word += " " + _pseudo_word(rng, rng.randint(2, 3)).capitalize()
        terms.append(word)
    return terms[:size]


def _mishear(rng: random.Random, term: str) -> str:
    """A plausible recogniser error: lower-case, one vowel swapped, maybe split."""
    word = term.lower().replace(" ", "")
    vowel_positions = [i for i, c in enumerate(word) if c in _VOWELS]
    if vowel_positions:
        i = rng.choice(vowel_positions)
        word = word[:i] + rng.choice(_VOWELS) + word[i + 1:]
    if len(word) > 7 and rng.random() < 0.5:
        cut = len(word) // 2
        word = word[:cut] + " " + word[cut:]
    return word


def make_transcript(rng: random.Random, words: int, vocab: list[str]) -> str:
    """Ordinary prose with roughly one mis-heard vocabulary term per ten words."""
    out: list[str] = []
    while len(out) < words:
        if rng.random() < 0.1:
            out.append(_mishear(rng, rng.choice(vocab)))
        else:
            out.append(rng.choice(_FILLER))
    return " ".join(out[:words])


def _time_one(fn, text: str, vocab: list[str], min_seconds: float) -> list[float]:
    """Per-call wall time in ms, repeated until `min_seconds` have elapsed (≥ 5 runs)."""
    samples: list[float] = []
    start = time.perf_counter()
    while len(samples) < 5 or time.perf_counter() - start < min_seconds:
        t0 = time.perf_counter()
        fn(text, vocab)
        samples.append((time.perf_counter() - t0) * 1000.0)
    return samples


def _git_commit() -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=REPO_ROOT,
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except Exception:
        return "unknown"


def run(min_seconds: float) -> dict:
    from yazses.postprocess.vocab_correct import correct

    rows = []
    fingerprint = hashlib.sha256()
    for vocab_size in VOCAB_SIZES:
        for n_words in TRANSCRIPT_WORDS:
            rng = random.Random(f"{SEED}-{vocab_size}-{n_words}")
            vocab = make_vocabulary(rng, vocab_size)
            text = make_transcript(rng, n_words, vocab)

            fixed, changes = correct(text, vocab)
            fingerprint.update(fixed.encode())
            fingerprint.update(repr([(c.heard, c.corrected, c.start, c.end) for c in changes]).encode())

            samples = _time_one(correct, text, vocab, min_seconds)
            samples.sort()
            rows.append({
                "vocab_size": vocab_size,
                "words": n_words,
                "runs": len(samples),
                "median_ms": round(statistics.median(samples), 4),
                "p95_ms": round(samples[int(0.95 * (len(samples) - 1))], 4),
                "corrections": len(changes),
            })
    return {
        "provenance": provenance(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
        "bench": "vocab_correct",
        "commit": _git_commit(),
        "seed": SEED,
        "min_seconds_per_cell": min_seconds,
        "output_fingerprint": fingerprint.hexdigest()[:16],
        "rows": rows,
    }


def profile(vocab_size: int = 500, n_words: int = 200) -> str:
    """cProfile one representative call; returns the top of the cumulative table."""
    from yazses.postprocess.vocab_correct import correct

    rng = random.Random(f"{SEED}-{vocab_size}-{n_words}")
    vocab = make_vocabulary(rng, vocab_size)
    text = make_transcript(rng, n_words, vocab)
    profiler = cProfile.Profile()
    profiler.enable()
    correct(text, vocab)
    profiler.disable()
    buf = io.StringIO()
    pstats.Stats(profiler, stream=buf).sort_stats("tottime").print_stats(8)
    return buf.getvalue()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--name", default="vocab-correct",
                        help="result name under paper/results/ (default vocab-correct)")
    parser.add_argument("--no-write", action="store_true", help="print only, archive nothing")
    parser.add_argument("--min-seconds", type=float, default=0.5,
                        help="minimum wall time spent timing each cell (default 0.5)")
    parser.add_argument("--profile", action="store_true",
                        help="print a cProfile table for vocab=500, words=200 and exit")
    args = parser.parse_args()

    if args.profile:
        print(profile())
        return 0

    result = run(args.min_seconds)
    print(f"commit {result['commit']}  "
          f"output fingerprint {result['output_fingerprint']}")
    print(f"{'vocab':>6} {'words':>6} {'median ms':>11} {'p95 ms':>10} {'runs':>6} {'fixes':>6}")
    for r in result["rows"]:
        print(f"{r['vocab_size']:>6} {r['words']:>6} {r['median_ms']:>11.3f} "
              f"{r['p95_ms']:>10.3f} {r['runs']:>6} {r['corrections']:>6}")
    if not args.no_write:
        print(f"wrote {write_result(args.name, result).relative_to(REPO_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
