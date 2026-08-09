# What Chiron can actually read

The mandate asks for an accurate capability matrix rather than a claim of
universal file support. This is that matrix, written from the code rather than
from intent.

## Supported

| Format | How it is read | Notes |
|---|---|---|
| Plain text (`.txt`, `.md`, `.log`, …) | `FileInput.read` | Strict UTF-8 only |
| Source code | `FileInput.read` | Treated as text; no parsing of syntax |
| JSON | `FileInput.read` | Read as text, not as structure |
| Anything else declaring `public.data` | `FileInput.read` | Accepted only if it decodes as strict UTF-8 |
| PDF (text layer) | `Chiron/pdf_text.py` | Uncompressed and FlateDecode streams. Refuses by name rather than returning doubtful text — see below |

Accepted content types are declared at `App/Sources/ChironApp/FileInput.swift:175`:
`.plainText`, `.text`, `.data`, `.sourceCode`, `.json`.

## Not supported

| Format | Status |
|---|---|
| Word, Pages, RTF | Not implemented |
| Spreadsheets | Not implemented |
| Images, audio, video | Not implemented, and out of scope — there is no OCR or transcription path |
| Encrypted or password-protected files | Not implemented; fails as invalid UTF-8 |
| Directories | Refused deliberately. `chiron verify` and `chiron analyze` accept one regular file; a directory is rejected rather than walked |

### PDF, and what it refuses

`Chiron/pdf_text.py` reads the text layer of uncompressed and `FlateDecode`
PDFs using only `zlib` — no third-party dependency, so the SBOM stays as small
as it claims. It refuses by name rather than guessing:

| Refusal | Meaning |
|---|---|
| `encrypted` | `/Encrypt` present; no decryption is attempted |
| `unsupported-filter` | a stream filter other than FlateDecode |
| `no-text-operators` | valid PDF, no text-showing operators — words may be images, or glyphs drawn directly. **There is no OCR.** |
| `unreliable-encoding` | text came out, but its character statistics say the font uses a custom map |
| `not-a-pdf`, `too-large`, `malformed` | as named |

`unreliable-encoding` is the one worth understanding. A PDF using a subsetted
font with a custom `/Differences` map decodes into prose that *looks* right
with one letter systematically wrong — `st!rted` for "started". Both PDFs
tested during development hit a refusal: one had no text operators at all, and
one produced exactly that substitution. Returning it would have put wrong text
carrying the shape of right text into a provenance record, and a citation
would then point at words nobody wrote. Mapping those fonts needs the embedded
font program, so the output is checked statistically and refused when it fails.

Refusing readable-looking text is the correct trade here, and it is why the
supported row above says "text layer" rather than "PDF".

## Bounds, and why they agree

Both sides cap a source at **8 MiB**:

- `FileInput.maxBytes` — `App/Sources/ChironApp/FileInput.swift:11`
- `DEFAULT_MAX_BYTES` — `Chiron/source_provenance.py:29`

These are the same number on purpose. A Swift-side bound larger than the
Python one would let the app accept a file the vault then silently truncates,
and a provenance record over a truncated source is a record of something the
user did not supply. `docs/SECURITY_MODEL.md` records this as a bound that had
drifted once already.

Oversize input is **reported, not silently cut**: `FileInput.read` reads
`maxBytes + 1` precisely so it can tell that truncation would have occurred and
say so.

## Encoding

Strict UTF-8, with no lossy fallback. A file that is not valid UTF-8 fails with
`invalidUTF8` rather than being repaired with replacement characters.

That is deliberate and it is a provenance property, not a parsing preference.
Byte offsets are how a span is tied back to its source; substituting U+FFFD for
an undecodable byte changes the byte length of the text and every offset after
it, so a citation would point at the wrong place. Refusing is the only answer
that keeps the offsets meaning what they say.

`FileInput` also detects an *incomplete* UTF-8 sequence at the truncation
boundary (`incompleteUTF8SuffixLength`) and trims it, so a multi-byte character
split by the size cap does not read as corruption.

## What happens after a file is read

Reading is only the first step. The path is:

1. `FileInput.read` — bounded read, strict UTF-8, truncation reported
2. `register_local_text_file` — content hash and source identity
3. the requested operation — `analyze`, `certify`, `attest`
4. a record carrying spans back to the registered source

`WorkspaceView` re-checks the file after import and raises
`fileChangedAfterImport` if it changed underneath, because a record that cites
a source which has since moved on is not a record of anything.

## Not uploaded

Reading a file does not send it anywhere. A hosted model is reached only when
the operator has both configured a credential and granted network
authorization, which are separate switches — see `ProposerRouter.RoutingPolicy`
and `NetworkAuthorization` in `App/Sources/ChironIntelligence/`. The default is
denied, and deterministic checking is unaffected by that default.
