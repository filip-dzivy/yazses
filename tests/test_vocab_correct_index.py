"""`correct()` looks terms up by phonetic key instead of scanning the vocabulary.

The scan recomputed every term's phonetic key for every window of every
utterance, so its cost grew with dictionary size × utterance length on the path
between the decoder and the keyboard. The index must be a pure speed-up: these
tests pin that its output is identical to the scan's, and that the number of
key computations no longer depends on how many terms the user has.
"""

from __future__ import annotations

import random

from hypothesis import given, settings
from hypothesis import strategies as st

import yazses.postprocess.vocab_correct as vc
from yazses.postprocess.vocab_correct import (
    _MAX_PHRASE_TOKENS,
    _STOPWORDS,
    _WORD_RE,
    DEFAULT_MAX_DISTANCE_RATIO,
    MIN_TOKEN_LENGTH,
    Correction,
    _distance,
    _without_possessive,
    correct,
    phonetic_key,
)

# ---- the pre-index implementation, kept verbatim as the reference ------------


def _reference_is_close(heard: str, term: str, max_ratio: float) -> bool:
    if len(heard.replace(" ", "")) < MIN_TOKEN_LENGTH:
        return False
    if phonetic_key(heard.replace(" ", "")) != phonetic_key(term.replace(" ", "")):
        return False
    bare_heard = heard.lower().replace(" ", "").replace("-", "")
    bare_term = term.lower().replace(" ", "").replace("-", "")
    key_length = len(phonetic_key(bare_term))
    ratio = max_ratio * (1.75 if key_length >= 5 else 1.0)
    budget = max(1, int(max(len(bare_term), len(bare_heard)) * ratio))
    return _distance(bare_heard, bare_term) <= budget


def _reference_correct(text, vocabulary, *, max_distance_ratio=DEFAULT_MAX_DISTANCE_RATIO):
    terms = [t.strip() for t in vocabulary if t and t.strip()]
    if not text or not terms:
        return text, []
    terms.sort(key=lambda t: (-len(t.split()), -len(t)))
    known = {t.lower() for t in terms}
    spans = [(m.start(), m.end(), m.group()) for m in _WORD_RE.finditer(text)]
    if not spans:
        return text, []
    corrections, out, cursor, i = [], [], 0, 0
    while i < len(spans):
        match_len, replacement = 0, ""
        if _without_possessive(spans[i][2]).lower() in known:
            i += 1
            continue
        for width in range(min(_MAX_PHRASE_TOKENS, len(spans) - i), 0, -1):
            if any(text[spans[i + k][1]:spans[i + k + 1][0]] != " " for k in range(width - 1)):
                continue
            if width > 1 and any(spans[i + k][2].lower() in _STOPWORDS for k in range(width)):
                continue
            heard = text[spans[i][0]:spans[i + width - 1][1]]
            if heard.lower() in known:
                break
            hit = next((t for t in terms if _reference_is_close(heard, t, max_distance_ratio)), None)
            if hit is not None:
                match_len, replacement = width, hit
                break
        if match_len:
            start, end = spans[i][0], spans[i + match_len - 1][1]
            out.append(text[cursor:start])
            out.append(replacement)
            corrections.append(Correction(text[start:end], replacement, start, end))
            cursor = end
            i += match_len
        else:
            i += 1
    out.append(text[cursor:])
    return "".join(out), corrections


# ---- equivalence -------------------------------------------------------------

VOCAB = ["Kubernetes", "YazSes", "PostgreSQL", "Ardebili", "faster-whisper", "kubectl",
         "Prometheus", "Grafana", "Terraform", "Kafka Connect", "kafka", "Postgres"]

CORPUS = [
    "deploy it on cooper netties tonight",
    "cubernetties and postgres sequel and pro meetheus",
    "from this from its from tags",
    "run yazses doctor then yazses say hello",
    "the YazSes's tray icon",
    "teraform plan and grafanna dashboards",
    "kafka konnect is down, kafka is up",
    "faster whisper beats ardebilly",
    "",
    "123 456 !!!",
]


def test_index_matches_the_scan_on_the_known_corpus():
    for text in CORPUS:
        assert correct(text, VOCAB) == _reference_correct(text, VOCAB), text


def test_index_matches_the_scan_on_seeded_random_input():
    rng = random.Random(73)
    letters = "bcdfgklmnprstvzaeiou"
    for _ in range(300):
        vocab = ["".join(rng.choice(letters) for _ in range(rng.randint(3, 10)))
                 for _ in range(rng.randint(1, 40))]
        vocab += [a + " " + b for a, b in zip(vocab[::5], vocab[1::5])]
        words = [rng.choice(vocab).lower() if rng.random() < 0.3
                 else "".join(rng.choice(letters) for _ in range(rng.randint(2, 9)))
                 for _ in range(rng.randint(0, 40))]
        text = " ".join(words)
        for ratio in (0.2, DEFAULT_MAX_DISTANCE_RATIO, 0.5):
            assert correct(text, vocab, max_distance_ratio=ratio) == _reference_correct(
                text, vocab, max_distance_ratio=ratio
            )


_word = st.text(alphabet="abcdefgklmnoprstuvz -'", min_size=1, max_size=12)


@settings(max_examples=300, deadline=None)
@given(text=st.lists(_word, max_size=20).map(" ".join), vocab=st.lists(_word, max_size=15))
def test_index_matches_the_scan_property(text, vocab):
    assert correct(text, vocab) == _reference_correct(text, vocab)


# ---- the cost no longer scales with the vocabulary ---------------------------


def _key_calls(monkeypatch, text, vocab) -> int:
    calls = 0
    real = vc.phonetic_key

    def counting(word: str) -> str:
        nonlocal calls
        calls += 1
        return real(word)

    monkeypatch.setattr(vc, "phonetic_key", counting)
    correct(text, vocab)
    return calls


def test_phonetic_keys_are_computed_once_per_term_not_per_window(monkeypatch):
    text = " ".join(["deploy the report about cooper netties today"] * 10)
    small = VOCAB
    large = VOCAB + [f"Zzterm{i}" for i in range(1000)]
    small_calls = _key_calls(monkeypatch, text, small)
    large_calls = _key_calls(monkeypatch, text, large)
    # One key per added term to build the index, and nothing more: the
    # per-window work is identical however large the dictionary is.
    assert large_calls - small_calls == 1000
