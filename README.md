# Last Commit 🕯️

**Every repo dies with one final commit. On Día de Muertos, they speak.**

**Live:** https://lastcommit.wathsala.tech

Last Commit is a graveyard for abandoned GitHub projects. Each grave is an *ofrenda*:
the repo's real history on one side, and on the other a first-person monologue from
its ghost, written by **Gemma 4** and voiced by **ElevenLabs**.

The séance happens on my laptop. The graveyard is public.

## Facts vs. fiction

Every ofrenda keeps two things strictly apart:

| Verified facts | The ghost's fiction |
| --- | --- |
| Pulled straight from the GitHub API: first and last commit, lifespan, commit count, stars, forks, open issues, archive status | Written by Gemma from those facts |
| Shown exactly as the API returned them | Labelled as fiction on the page |
| Linked to the real commits | Speaks only as the code: never names real people or describes their feelings |

Guard rails in [`lastcommit/ghost.py`](lastcommit/ghost.py): contributor usernames are
removed from the prompt, any reply that names one is regenerated, and anything that
still slips through is scrubbed.

## How it works

```
repos.txt ──► seance.py ──► GitHub API  (facts)
                    │
                    ├──► Gemma 4 via AI Studio (or Ollama)  (epitaph + monologue)
                    ├──► ElevenLabs                         (voice, MP3)
                    ▼
            site/data/*.json + site/audio/*.mp3 ──► static site on Render
```

No server, no framework, no dependencies: Python's standard library for the séance,
plain HTML/CSS/JS for the site.

## Run it yourself

Requirements: Python 3.10+, a Google AI Studio key (or [Ollama](https://ollama.com) for local Gemma), an ElevenLabs API key.

```bash
git clone https://github.com/wathsalaggg/last-commit && cd last-commit
cp .env.example .env            # add your AI Studio, ElevenLabs and GitHub keys

python3 seance.py atom/atom     # one repo
python3 seance.py --all         # every repo in repos.txt
python3 seance.py --all --force # rewrite every ghost

cd site && python3 -m http.server 8000   # open http://localhost:8000
```

Options: `--no-voice` skips ElevenLabs, `--facts-only` just refreshes GitHub data.
Defaults to `gemma-4-26b-a4b-it` on Google AI Studio. To run Gemma locally instead,
set `PROVIDER=ollama` and `MODEL=gemma3:1b` and run `ollama pull gemma3:1b`.

## Deploy

The repo includes [`render.yaml`](render.yaml): on Render, choose **New → Blueprint**
(or a Static Site with publish directory `site`). There is no build step.

## Built

Built on 31 October – 1 November 2026 for Día de Muertos.

## Credits

- [Gemma](https://ai.google.dev/gemma) by Google, used under the Gemma Terms of Use
- [Ollama](https://github.com/ollama/ollama) (MIT) for running Gemma locally
- [ElevenLabs](https://elevenlabs.io) for the voices
- [GitHub REST API](https://docs.github.com/rest) for every fact
- Fonts: [IM Fell English](https://fonts.google.com/specimen/IM+Fell+English) and
  [JetBrains Mono](https://www.jetbrains.com/lp/mono/), both SIL Open Font License
- The repos in the graveyard, and everyone who ever committed to them

## License

MIT
