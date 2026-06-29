# Running Chiron — everything, end to end

Everything is plain `python3`. The core needs no install; `numpy` is only used by a couple of
optional tools. Run these from inside the `Chiron/` folder.

## 0. Run everything with one command

```bash
python3 vault.py                  # starts the engine + every service; prints one URL
# then open http://127.0.0.1:8765 ;  Ctrl-C stops everything
```

`vault.py` launches all five local services so you never juggle ports (console :8765, launcher
:8768, assistant :8769, grow control :8767, LLM grow :8766). `python3 vault.py --core` runs just the
engine. The sections below cover each service if you'd rather start them individually.

## 1. The engine + operator console

```bash
python3 chiron.py serve            # opens the offline console at http://127.0.0.1:8765
```

That one command gives you Analyze, the Congress, Growth, Self-growth, Feed, and the status pages.
The engine itself is fully offline and deterministic.

CLI, without the console:

```bash
python3 chiron.py collapse 1 1 2 3 5 8 13     # recover + prove a generator
python3 chiron.py solve "WKLV LV D WHVW"      # crack a classical cipher, ciphertext-only
python3 chiron.py selftest                    # full embedded gate suite
```

## 2. Growing — start, stop, point it anywhere (from the dashboard)

The grower is a separate, network-capable process (the engine never touches the network). A small
control service lets the dashboard start it, stop it, and redirect it whenever you want.

```bash
python3 grow_control.py serve      # control plane at http://127.0.0.1:8767
```

Then open the console (port 8765), go to the **Feed** tab, pick a source (Wikipedia topics, a
website, a JSON API, or OEIS), and use **Grower control → Start / Stop**. Status (running, current
source, Congress size, pass count) updates live.

Same thing from the command line:

```bash
python3 grow_control.py start --kind oeis --value keyword:core   # start, pointed at OEIS
python3 grow_control.py start --kind web  --value "https://example.com"
python3 grow_control.py status
python3 grow_control.py stop
```

The grower keeps running and self-extending until you stop it; point it somewhere new at any time
and it picks up the change on its next pass.

## 3. LLM-assisted growth — the President (optional, free)

The one deliberately non-deterministic component, isolated in its own service. The LLM only
*proposes* candidate structures; the engine *verifies* every one, so nothing enters the Congress
unverified.

```bash
# get a free key at https://aistudio.google.com/apikey  (Gemini; Groq/OpenRouter also work)
export GROW_LLM_API_KEY=your_key_here
python3 president_grow.py serve    # at http://127.0.0.1:8766 ; also the console's "Grow · President" tab
```

Without a key it stays disabled and the rest of the system is unaffected.

## 4. Start your own grow from a file — `grow_clean.py`

For pointing a fresh grow at your own material (any file, the Wikipedia preset, or ingestion-driven
search). Every grown fact is still verified by the engine.

```bash
python3 grow_clean.py file ./notes.txt
python3 grow_clean.py ingest ./paper.txt --llm     # grow from it AND from what it points to
python3 grow_clean.py wikipedia "prime numbers"
```

## 5. Run it all at once

```bash
python3 chiron.py serve &          # engine + console        :8765
python3 console_server.py serve &  # run any function        :8768
python3 assistant_server.py serve &# chat assistant          :8769
python3 grow_control.py serve &    # start/stop/point grow   :8767
python3 president_grow.py serve &  # LLM grow (if key set)    :8766
# open http://127.0.0.1:8765  —  the Run and Chat tabs drive everything below
```

Once those are up, the console's **Run** tab lists every engine and subfunction and runs any of them
live; the **Chat** tab lets you say what you want in plain language — it reads your intent and runs
the real, deterministic functions (recover a rule, speak it back, search or summarize the Congress,
run any engine). The model directs, the engine does the work, so every result is exact. The
assistant and `president_grow` need a free LLM key (`export GROW_LLM_API_KEY=…`; get one at
https://aistudio.google.com/apikey); everything else runs with no key.

| Service | Port | What it is |
|---|---|---|
| `chiron.py serve` | 8765 | the engine + operator console (offline) |
| `console_server.py serve` | 8768 | the launcher — run any function across all engines (Run tab) |
| `assistant_server.py serve` | 8769 | natural-language assistant over the engine + Congress (Chat tab) |
| `grow_control.py serve` | 8767 | start / stop / point the continuous grower |
| `president_grow.py serve` | 8766 | LLM-assisted growth (propose → verify) |

## 6. Verify and benchmark

```bash
python3 chiron.py selftest         # the engine's own gates
python3 semic.py selftest          # semantic calculus (56/56)
python3 bench_suite.py             # six external tasks vs established baselines
python3 epistemic.py demo          # one contract, four instances
python3 build.py verify-all        # chiron.py + semic.py recompile byte-identically
python3 build_manifest.py --run    # index every script + its emitted certificate (artifacts/)
```

## 7. Wrap an LLM output (accountability certificate)

```bash
python3 llm_certify.py "obviously 2 4 8 16 32 64 continues, and 2+2=5"
```

Audits the honesty of the text, exactly verifies the checkable claims (here: the geometric sequence
verifies, `2+2=5` is refused), runs the governance gate, and signs it. It certifies *accountability*,
never that a free-text answer is correct.
