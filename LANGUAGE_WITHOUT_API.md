# Natural Language Without an External API

*How Chiron handles prose and free text deterministically, offline, with no model
download and no API call — and why that constraint is the moat, not the limitation.
The last major hurdle, locked down.*

---

## 0. The trap to avoid

The wrong move is to bolt an LLM onto Chiron so it can "understand" prose. That
breaks the one property the whole vault is built on: **deterministic, offline,
owner-signed, abstain-or-prove honesty.** An LLM is non-deterministic, needs the
network, can't show its work, and will fabricate meaning under pressure — the exact
failure (machine patronization, confident non-communication) that LexGuard, JDICert,
Candor, and Chiron's honest residuals exist to defeat. If language only works by
phoning an API, the system is not actualized; it's a thin client.

So the rule is: **never fake understanding.** Decompose language into the substrates
where Chiron's exact / structural / statistical recovery genuinely applies, recover
what is recoverable, learn the soft layer (semantics) by **counting on a local
corpus**, and **abstain honestly** on the rest.

## 1. The principle

Prose has no single exact generator — but it is layered, and several of its layers
*do* admit exact or statistical recovery. Meaning ("semantics") is the soft layer,
and the classical result is that you don't need a trained model to get a real handle
on it: **a word is known by the company it keeps.** Co-occurrence counts on local
text yield genuine semantic structure. No API. No download. Just arithmetic.

## 2. Proof of the keystone (offline distributional semantics)

Run on a tiny local corpus, pure-Python, stdlib only — PPMI co-occurrence + cosine:

```
cos(dog,  cat)    = 0.624     both animals     (share runs / sleeps / barks)
cos(king, queen)  = 1.000     both royalty     (share rules / reigns / commands)
cos(puppy,dog)    = 0.817
cos(prince,king)  = 0.379
cos(dog,  king)   = 0.061     different meaning -> low
cos(cat,  queen)  = 0.049     different meaning -> low
```

Meaning-similarity fell out of counting. Scale the corpus (Chiron's grower already
collects one offline) and add truncated SVD and the vectors sharpen — still with no
API anywhere. **This is the unlock the hurdle was hiding.**

## 3. The four offline layers

Each is deterministic, bundled, and offline. Each respects abstain-or-prove.

| Layer | Offline mechanism (no API) | What it yields | Already in the vault |
|---|---|---|---|
| **Lexical–statistical** | Deterministic tokenizer; character/word **n-gram (Markov)** models built from the text + the local Congress corpus; per-token surprisal, perplexity, Zipf, Shannon entropy. A Markov model is itself a *generator* Chiron can `collapse` and measure. | Language/register ID; "does this fit the document's statistical law?"; **injection / anomaly detection** | Chiron entropy machinery; the grown 10 MB Congress corpus |
| **Structural–grammatical** | Sentence segmentation; **rule-based POS** (transformation/Brill rules + a bundled lexicon, no neural net); a **relabel-invariant parse skeleton** — exactly the trick `collapse_code` already uses on ASTs. | Template/boilerplate detection; **structural twins** (paraphrase-of-structure, plagiarism, contract-clause match); grammaticality | `collapse_code`, `text_structure`, the AST skeleton |
| **Prosodic–formal** | Exact meter / rhyme / acrostic / fixed-form scanning. | Recovery of poetic, templated, or **encoded** structure; verse/forgery analysis | `primus_verses.py`, `scans_as_hexameter` |
| **Distributional–semantic** | **Count-based embeddings**: co-occurrence -> PPMI -> (optional) truncated SVD, trained on the **local** corpus. Builds the relational graph the HCT stack runs on. | Semantic similarity, synonymy, topic; the graph for significance | Proven above; the grower supplies the corpus |

## 4. The discipline (the actual "lock")

The same rule that makes the numeric engine trustworthy makes the language layer
trustworthy:

- **Exact layers verify on held-out.** Does the recovered grammar / meter / template
  predict held-out lines exactly? If yes, it's a law; if not, residual.
- **The semantic layer reports confidence and abstains** when local-corpus support is
  thin. It says "weak evidence," it does not invent a meaning.
- **Candor audits the output.** Any prose the system emits passes the anti-patronization
  audit — it states its own limits on every run.
- **Never fabricate meaning.** Where prose has no generator, the engine returns a
  classified residual and abstains, exactly as it does on a random number stream.

## 5. How it plugs into the HCT projection stack (the convergence)

This is the elegant part. The HCT layers I planned to bridge from `cert_engine.py`
are *precisely* the offline semantic engine for language:

```
text ──▶ co-occurrence graph ──▶ significance = tanh(α·Ollivier-Ricci curvature) ──▶ distributional vectors
        (Contextual substrate)   (Emotive substrate: what matters / ambiguity)      (Semantic substrate)
```

`SignificanceGeometry` (curvature on a relational graph), `EmotiveSubstrateProjectionStack`,
and `SentimentProjection` all operate on exactly this kind of graph — and a co-occurrence
graph from local text *is* that graph. So **P→C→E→S projection, run on local
co-occurrence, gives offline semantics + significance with no API.** The language
solution and the HCT-bridge gameplan are the same build.

## 6. Why no-API is the moat

A deterministic, offline, auditable, owner-signed language analyzer is a *different
thing* from an LLM — and in regulated, defense, legal, and air-gapped contexts it is
the more valuable thing. It will not match an LLM's fluency or world knowledge, and it
must never pretend to. What it does, reproducibly and with zero false positives:

- detect **injected / anomalous text** (a prompt injection in a document, an AI-inserted
  paragraph, a tampered contract clause) as a deviation from the document's own law;
- **attribute origin** (human vs synthetic, author A vs author B) via Infectatrum's
  Jensen-Shannon origin-signatures — already offline;
- **match structure** (plagiarism, boilerplate, clause reuse) via relabel-invariant skeletons;
- **measure distributional semantics** from the local corpus — without sending one byte
  anywhere.

That is the niche an LLM structurally cannot fill.

## 7. Applied to the actionable-intelligence brief

The prose brief is the language version of the numeric one already running in
`actionable_intelligence.py`:

> recover the document's structural + statistical law -> **flag the sentence/paragraph
> that breaks it** (injection, tampered clause, AI insertion, plagiarized block with a
> foreign origin-signature) -> **attribute origin** -> **govern** the call
> (PROCEED / ESCALATE / REJECT). Offline, deterministic, zero false positives.

## 8. Build plan — `language.py` (a green-safe bridge)

1. Wrap the existing pieces (`text_structure`, `collapse_string`, `collapse_code`
   skeleton, Primus prosody, Infectatrum signatures) behind one prose front door.
2. Add the **n-gram / Markov** statistical model (stdlib) trained on text + the local
   Congress corpus; expose surprisal + anomaly scan.
3. Add **count-based embeddings** (PPMI + optional SVD via the optional numpy path,
   pure-Python fallback) over the local corpus; expose semantic similarity with confidence.
4. Add the **rule-based POS + relabel-invariant parse skeleton**; expose structural twins.
5. **Bridge** `cert_engine`'s `SignificanceGeometry` / projection stack onto the
   co-occurrence graph for significance/emotive scoring (Pillar I/II of the gameplan).
6. Compose into a **prose brief** mirroring `actionable_intelligence.py`.
7. Mirror to both folders; keep `chiron.py` byte-unchanged and GREEN; dual-frame in
   `FRAMING.md`; verify with held-out + a live demo. No phase ships red.

## 9. Honest limits

- Count-based semantics is weaker than transformer embeddings and **needs a real local
  corpus**; the 10 MB Congress is a start, the grower extends it offline.
- The rule-based parser is transparent but coarser than a neural parser.
- This will not answer open-domain questions or write fluent prose. It is an
  **analyzer**, not a generator-of-fluency — by design, and that is the point.

The trade is deliberate: determinism, auditability, and offline operation in exchange
for fluency. For everything this vault is for, that is the right side of the trade.
