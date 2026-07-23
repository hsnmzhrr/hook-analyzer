"""Hook Analyzer: scores the opening of a YouTube script on retention-relevant metrics.

Usage:
    python hook_analyzer.py sample_scripts/good_hook.txt
    python hook_analyzer.py sample_scripts/good_hook.txt --ai   # adds AI qualitative critique (Gemini, free tier)
"""

import argparse
import os
import re
import sys

HOOK_WORDS = 60  # first ~15 seconds of narration at 140 wpm

POWER_WORDS = {
    "secret", "mistake", "never", "nobody", "banned", "warning", "proof",
    "shocking", "hidden", "truth", "exposed", "free", "instantly", "dangerous",
    "before", "stop", "wrong", "lie", "trap", "scam", "hack", "million",
}

WEAK_OPENERS = (
    "hi", "hello", "hey guys", "welcome", "in this video", "today we",
    "today i", "what's up", "so today",
)


def count_syllables(word: str) -> int:
    word = word.lower().strip(".,!?;:\"'")
    if not word:
        return 0
    vowels = "aeiouy"
    count = 0
    prev_vowel = False
    for ch in word:
        is_vowel = ch in vowels
        if is_vowel and not prev_vowel:
            count += 1
        prev_vowel = is_vowel
    if word.endswith("e") and count > 1:
        count -= 1
    return max(count, 1)


def flesch_reading_ease(text: str) -> float:
    sentences = [s for s in re.split(r"[.!?]+", text) if s.strip()]
    words = text.split()
    if not sentences or not words:
        return 0.0
    syllables = sum(count_syllables(w) for w in words)
    return 206.835 - 1.015 * (len(words) / len(sentences)) - 84.6 * (syllables / len(words))


def extract_hook(text: str) -> str:
    words = text.split()
    return " ".join(words[:HOOK_WORDS])


def analyze(text: str) -> dict:
    hook = extract_hook(text)
    hook_lower = hook.lower()
    words = hook.split()
    sentences = [s.strip() for s in re.split(r"[.!?]+", hook) if s.strip()]

    metrics = {
        "hook_text": hook,
        "word_count": len(words),
        "sentence_count": len(sentences),
        "avg_sentence_length": round(len(words) / max(len(sentences), 1), 1),
        "reading_ease": round(flesch_reading_ease(hook), 1),
        "has_question": "?" in hook,
        "has_number": bool(re.search(r"\d", hook)),
        "second_person": len(re.findall(r"\b(you|your|you're)\b", hook_lower)),
        "power_words": sorted(w for w in POWER_WORDS if re.search(rf"\b{w}\b", hook_lower)),
        "weak_opener": next((w for w in WEAK_OPENERS if hook_lower.startswith(w)), None),
    }

    # Composite score out of 100, weights from retention-editing practice:
    # direct address and stakes matter more than raw readability.
    score = 0
    score += 20 if metrics["second_person"] >= 2 else 10 if metrics["second_person"] == 1 else 0
    score += 15 if metrics["power_words"] else 0
    score += 15 if metrics["has_number"] else 0
    score += 10 if metrics["has_question"] else 0
    score += 15 if metrics["avg_sentence_length"] <= 14 else 5 if metrics["avg_sentence_length"] <= 20 else 0
    score += 15 if metrics["reading_ease"] >= 70 else 8 if metrics["reading_ease"] >= 50 else 0
    score += 10 if not metrics["weak_opener"] else 0
    metrics["score"] = score
    return metrics


def ai_critique(hook: str) -> str:
    import requests
    key = os.environ["GEMINI_API_KEY"]
    prompt = (
        "You are a YouTube retention editor. Critique this hook in 4 bullet points: "
        "what holds attention, what loses it, the single biggest fix, and a rewritten "
        f"first sentence.\n\nHOOK:\n{hook}"
    )
    r = requests.post(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",
        params={"key": key},
        json={"contents": [{"parts": [{"text": prompt}]}],
              "generationConfig": {"maxOutputTokens": 400}},
        timeout=60,
    )
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("script_file", help="Path to a plain-text script file")
    p.add_argument("--ai", action="store_true", help="Add AI critique via Gemini free tier (needs GEMINI_API_KEY)")
    args = p.parse_args()

    with open(args.script_file) as f:
        text = f.read()

    m = analyze(text)

    print(f"\n{'=' * 52}\nHOOK ANALYSIS: {args.script_file}\n{'=' * 52}")
    print(f"Score: {m['score']}/100\n")
    print(f"Words in hook window: {m['word_count']}")
    print(f"Sentences: {m['sentence_count']} (avg {m['avg_sentence_length']} words)")
    print(f"Flesch reading ease: {m['reading_ease']} (70+ is conversational)")
    print(f"Direct address (you/your): {m['second_person']}x")
    print(f"Contains question: {m['has_question']}")
    print(f"Contains number: {m['has_number']}")
    print(f"Power words: {', '.join(m['power_words']) or 'none'}")
    if m["weak_opener"]:
        print(f"WEAK OPENER DETECTED: starts with '{m['weak_opener']}'")

    if args.ai:
        if not os.environ.get("GEMINI_API_KEY"):
            sys.exit("--ai requires GEMINI_API_KEY. Free key at https://aistudio.google.com")
        print(f"\n{'-' * 52}\nAI CRITIQUE\n{'-' * 52}")
        print(ai_critique(m["hook_text"]))


if __name__ == "__main__":
    main()
