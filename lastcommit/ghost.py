"""Write the ghost's monologue with Gemma.

The model only ever writes fiction. Facts are passed in as context but are
displayed from the API data, never from model output. The prompt is kept
short and concrete because small models (1B-4B) drift on long instructions.
"""

import re
import time

from . import config
from .http import HTTPError, post_json

SYSTEM = """You are the ghost of an abandoned software project, speaking at your own ofrenda on the Day of the Dead.
Rules:
- Speak in the first person, as the code itself.
- Be wistful, a little funny, and specific. Say plainly what you did for people (from "What you were"). Quote your first and last commit messages.
- Only use numbers exactly as given. Do not invent any other numbers, dates or events.
- Address the living developers visiting your grave.
- Never name real people. Never describe what the developers felt, thought, struggled with or did. Talk only about yourself, the code.
- Do not invent events. If you are unsure, be vague and poetic instead.
- No lists, no headings, no markdown, no emoji."""

TEMPLATE = """Facts about you:
- Name: {name}
- What you were: {description}
- Written mostly in: {language}
- First commit: {first_date}, message "{first_msg}"
- Last commit: {last_date}, message "{last_msg}"
- Lived {lifespan} years, silent for {silence} years
- {commits} commits, {stars} stars
- {archived}

Write exactly this format:
EPITAPH: <one line, under 12 words, for your tombstone>
MONOLOGUE:
<about {words} words, 2 short paragraphs>"""


def _clean(text: str, names: set[str]) -> str:
    """Remove :emoji: codes, merge-branch refs and real usernames."""
    text = re.sub(r":[a-z0-9_+-]+:", "", text)
    text = re.sub(r"(Merge pull request #\d+) from \S+", r"\1", text)
    for n in names:
        text = re.sub(rf"\b{re.escape(n)}\b", "someone", text, flags=re.I)
    return re.sub(r"\s+", " ", text).strip() or "unknown"


def build_prompt(facts: dict, words: int = 140) -> str:
    first, last = facts.get("first_commit") or {}, facts.get("last_commit") or {}
    names = real_names(facts)
    return TEMPLATE.format(
        name=facts["full_name"].split("/")[1],
        description=_clean(facts["description"] or "unknown", names),
        language=facts["language"] or "unknown",
        first_date=(first.get("date") or facts["born"])[:10],
        first_msg=_clean(first.get("message", "unknown"), names),
        last_date=(last.get("date") or facts["died"])[:10],
        last_msg=_clean(last.get("message", "unknown"), names),
        lifespan=facts["lifespan_years"],
        silence=facts["years_since_last_commit"],
        commits=facts["total_commits"],
        stars=facts["stars"],
        archived="You were archived (read-only)." if facts["archived"]
        else "You were never archived, just left alone.",
        words=words,
    )


# --- providers -------------------------------------------------------------

def _ollama(prompt: str, model: str) -> str:
    url = config.get("OLLAMA_URL", "http://localhost:11434").rstrip("/")
    out = post_json(f"{url}/api/generate", {
        "model": model,
        "system": SYSTEM,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.7, "num_ctx": 2048, "num_predict": 450},
    }, timeout=900)
    return out["response"]


def _aistudio(prompt: str, model: str) -> str:
    key = config.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("PROVIDER=aistudio needs GEMINI_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    # Gemma models on AI Studio take no system role, so prepend it.
    body = {
        "contents": [{"role": "user", "parts": [{"text": SYSTEM + "\n\n" + prompt}]}],
        # Gemma 4 otherwise "thinks" until it runs out of tokens and returns
        # no answer. Minimal thinking answers in seconds.
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1024,
                             "thinkingConfig": {"thinkingLevel": "minimal"}},
    }
    for attempt in range(4):
        try:
            out = post_json(url, body, headers={"x-goog-api-key": key}, timeout=180)
            break
        except HTTPError as e:
            # 500/503/429 from AI Studio are usually transient.
            if attempt == 3 or not re.search(r"-> (429|5\d\d)", str(e)):
                raise
            time.sleep(5 * 2 ** attempt)
    parts = out["candidates"][0].get("content", {}).get("parts", [])
    # Skip the model's hidden reasoning ("thought" parts); keep only the answer.
    return "".join(p.get("text", "") for p in parts if not p.get("thought"))


PROVIDERS = {"ollama": _ollama, "aistudio": _aistudio}


# --- parsing and guard rails ----------------------------------------------

def parse(text: str) -> tuple[str, str]:
    text = text.strip().replace("**", "")
    m = re.search(r"EPITAPH:\s*(.+)", text, re.I)
    epitaph = m.group(1).strip().strip('"') if m else ""
    m = re.search(r"MONOLOGUE:\s*(.+)", text, re.I | re.S)
    body = m.group(1) if m else re.sub(r"EPITAPH:.*\n?", "", text, flags=re.I)
    paragraphs = [re.sub(r"\s+", " ", p).strip() for p in re.split(r"\n\s*\n", body)]
    return epitaph, "\n\n".join(p for p in paragraphs if p)


def real_names(facts: dict) -> set[str]:
    names = {c["login"] for c in facts.get("top_contributors", [])}
    for key in ("first_commit", "last_commit"):
        if facts.get(key):
            names.add(facts[key]["author"])
    # Org owners like "atom" or "bower" share the project's own name, so only
    # people (commit authors, contributors) are guarded.
    project = facts["full_name"].split("/")[1].lower()
    return {n for n in names if n and len(n) > 2 and n.lower() != project}


def names_mentioned(text: str, names: set[str]) -> list[str]:
    return [n for n in names if re.search(rf"\b{re.escape(n)}\b", text, re.I)]


def summon(facts: dict, provider: str | None = None, model: str | None = None,
           attempts: int = 3) -> dict:
    provider = provider or config.get("PROVIDER", "ollama")
    model = model or config.get("MODEL", "gemma3:4b")
    call = PROVIDERS[provider]
    prompt = build_prompt(facts)
    names = real_names(facts)

    epitaph, monologue = "", ""
    for _ in range(attempts):
        epitaph, monologue = parse(call(prompt, model))
        if monologue and not names_mentioned(epitaph + " " + monologue, names):
            break
    # Last resort: scrub any real names that slipped through.
    for n in names_mentioned(epitaph + " " + monologue, names):
        pattern = re.compile(rf"\b{re.escape(n)}\b", re.I)
        monologue = pattern.sub("someone", monologue)
        epitaph = pattern.sub("someone", epitaph)

    return {
        "epitaph": epitaph or "Here lies the code. It compiled once.",
        "monologue": monologue,
        "provider": provider,
        "model": model,
    }
