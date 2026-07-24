# Hook Analyzer

Scores the first 60 words of a YouTube script (roughly the first 15 seconds of narration) on retention-relevant metrics. Rule-based scoring, with an optional Gemini API pass (free tier) for qualitative critique.

Built from patterns observed across 800+ professionally produced scripts: hooks that retain viewers use direct address, concrete numbers, short sentences, and high-stakes vocabulary. Hooks that lose viewers open with greetings and channel housekeeping.

## What it measures

| Metric | Why it matters |
|---|---|
| Direct address (you/your) | Viewer must feel personally implicated in the first seconds |
| Power words | Stakes vocabulary (mistake, hidden, never) signals payoff |
| Numbers | Specificity reads as credibility |
| Avg sentence length | Under 14 words sustains narration pace |
| Flesch reading ease | 70+ means conversational, not essay-like |
| Weak opener detection | "Hey guys, welcome back" is a measurable retention killer |

Composite score out of 100. Weights encode editing practice: direct address and stakes are weighted above raw readability.

## Setup

```bash
pip install requests
```

The rule-based scoring runs offline with no key required. The `--ai` flag needs a free Gemini API key from aistudio.google.com. The code reads it from the environment at runtime, never from a file:

```bash
export GEMINI_API_KEY=your_key_here        # macOS/Linux
$env:GEMINI_API_KEY = "your_key_here"      # Windows PowerShell
```

Two notes on auth and model choice, both of which caused real failures during testing:

- Keys issued since mid-2026 start with `AQ.` rather than the older `AIza`. Both work here. The key is sent in an `x-goog-api-key` header rather than a URL query parameter, so it never appears in logs or stack traces.
- Model is `gemini-2.5-flash` with `thinkingConfig.thinkingBudget` set to 0. Thinking models spend their output budget on internal reasoning before writing, which returns an empty critique at small token ceilings.

## Usage

```bash
python hook_analyzer.py sample_scripts/good_hook.txt
python hook_analyzer.py your_script.txt --ai   # adds AI critique, needs GEMINI_API_KEY
```

## Example results

Included samples:

- `good_hook.txt` scores **90/100** (5x direct address, 5 power words, numbers, 12-word avg sentences)
- `weak_hook.txt` scores **33/100** (greeting opener, no numbers, no power words)

Also included: two of my own produced scripts, run through the tool unedited.

- `hassan_real_1_inout.txt` (brand-expose opening) scores **35/100**. Editorially this is a strong hook, high stakes, direct contrast, a real curiosity gap, but it opens with two long sentences (30-word average), which the readability and sentence-length weights penalize hard.
- `hassan_real_2_hobbies.txt` (self-improvement opening) scores **70/100**. A rhetorical-question opener with short sentences and repeated direct address, mechanically strong even though editorially it is one of the more generic hooks in my catalog.

This is the tool's real limitation surfacing on real data, not a cherry-picked pair: rule-based scoring rewards surface mechanics (sentence length, direct address, readability) and cannot judge whether the underlying claim is actually interesting. That gap is exactly what the `--ai` critique pass exists to cover.

## Limitations (honest ones)

- Rule-based scoring can't judge whether the hook's *claim* is actually interesting. That's what the free `--ai` critique pass is for.
- English only. Syllable counting is heuristic.
- The 60-word window assumes 140 wpm narration; adjust `HOOK_WORDS` for faster pacing.
- The `--ai` pass depends on a third-party model whose behaviour changes without notice. The migration from `gemini-2.0-flash` (retired June 2026) to `gemini-2.5-flash` is recorded in the commit history.
- The `--ai` pass only receives the 60-word window, not the full script. It cannot distinguish a deliberate cliffhanger from the window's own truncation, and will sometimes critique the cutoff as an editorial flaw.
