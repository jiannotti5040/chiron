export const meta = {
  name: 'chiron-full-inventory',
  description: 'Complete read-only inventory of the Chiron repository: what every area is, its status, and whether it belongs in a public open-source repo',
  phases: [
    { title: 'Inventory', detail: 'one agent per repository area, producing structured records' },
    { title: 'Synthesis', detail: 'merge into one machine-readable inventory and a cleanup plan' },
  ],
}

const REPO = '/Users/jacobiannotti/Desktop/Intellectual/Jacob-s-Portfolio-Vault'

const RULES = `
Repository: ${REPO}

READ ONLY. Do not write, edit, create, or delete any file. Do not run any
mutating git command. Do not run builds. Use Read, Grep, Glob, and read-only
Bash (git log/show/ls-files, ls, wc, head, find) only.

CONTEXT YOU MUST APPLY WHEN JUDGING:

This is a PUBLIC, Apache-2.0 open-source repository. The owner's concerns,
verbatim:
  - The repo has accumulated documentation that reads like a conversation
    transcript between an AI agent and the owner, rather than software
    documentation. Editorialising, first-person narration, "what I got wrong"
    confessionals, and invented project conventions presented as project law.
    This is a defect. Flag every instance you find with file and line.
  - An iOS/macOS app is intended for App Store distribution. Shipping the
    entire application into a public repo may be wrong; the Swift source may
    be fine as open source but app-store packaging, screenshots, and
    app-centric prose do not belong in the core README.
  - The repo must be optimised for BOTH human readers and machine/agent
    consumption.

For every file or area you inspect, judge it against a professional
open-source standard: would a senior engineer landing on this repo cold find
it clear, credible, and free of noise?
`

const AREA = {
  type: 'object',
  properties: {
    area: { type: 'string' },
    purpose: { type: 'string', description: 'What this area actually is, in one or two sentences' },
    status: { type: 'string', enum: ['canonical', 'generated', 'supporting', 'research', 'historical', 'duplicate', 'obsolete', 'unclear'] },
    file_count: { type: 'integer' },
    belongs_public: { type: 'string', enum: ['yes', 'no', 'partly', 'unsure'] },
    belongs_reason: { type: 'string' },
    findings: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          file: { type: 'string' },
          line: { type: 'integer' },
          kind: { type: 'string', enum: ['conversational-prose', 'invented-convention', 'stale-fact', 'duplicate', 'orphan', 'oversized', 'app-store-material', 'missing-doc', 'other'] },
          detail: { type: 'string' },
          severity: { type: 'string', enum: ['high', 'medium', 'low'] },
        },
        required: ['file', 'kind', 'detail', 'severity'],
      },
    },
    recommendation: { type: 'string', description: 'Concrete action: keep as-is, rewrite, move, split, archive, delete — and why' },
  },
  required: ['area', 'purpose', 'status', 'belongs_public', 'belongs_reason', 'findings', 'recommendation'],
}

const AREAS = [
  { key: 'root-docs', prompt: 'The repository ROOT files only: README.md, AGENTS.md, STATUS.md, CONTRIBUTING.md, NOTICE, LICENSES.md, CITATION.cff, run-chiron.command, demo.sh, Dockerfile, .gitignore, .github/. Read README.md and AGENTS.md IN FULL. These are the front door and the highest-priority target for conversational-prose and invented-convention findings. Quote the worst offending sentences with line numbers.' },
  { key: 'docs-dir', prompt: 'The docs/ directory, every file. Read each one at least in outline. Many were written by an AI agent during a long session; identify which read as software documentation and which read as session narration or status confessionals. Also flag any doc that duplicates another.' },
  { key: 'primus', prompt: 'Primus/ — the published PyPI package (primus-intelligence). Inventory its modules, tests, docs, and packaging. Judge whether its public docs are professional. Note anything that should not ship in a published wheel.' },
  { key: 'chiron-core', prompt: 'Chiron/ — the flagship module directory (~160 files). Inventory the module families, identify the canonical entry points, and flag duplicates, orphans, or modules nothing imports. Do not read every file; sample and use imports/manifest to map it.' },
  { key: 'swift-apps', prompt: 'App/ and iOS/ — the Swift packages and the Xcode project. Determine exactly what is here, whether there are TWO apps or one, and what App-Store-specific material exists (icons, entitlements, privacy manifests, bundle IDs). Give a clear recommendation on what belongs in a public repo versus a private/app repo.' },
  { key: 'research-dirs', prompt: 'The research and theory directories: UMA Suite/, Infectatrum/, Individual Programs/, Quack System Constructs/, Ontological & Philosophical Books/, Paper/, Candor/, Veritas/, VerifiedInk/, JDICert/, prototype/, studies/, eval/, notes/, Governance/. These are ~500 files. Determine for EACH what it is, whether it is executable or prose, and whether it belongs in this repo or a separate one. This is the biggest surface and the most likely source of noise for a newcomer.' },
]

phase('Inventory')
log(`Inventorying ${AREAS.length} areas of the repository, read-only`)

const records = await parallel(AREAS.map(a => () =>
  agent(`${RULES}\n\nINVENTORY THIS AREA:\n${a.prompt}\n\nBe concrete and cite files. Do not speculate about intent; report what the files show.`,
    { label: `inv:${a.key}`, phase: 'Inventory', schema: AREA })))

const found = records.filter(Boolean)
const allFindings = found.flatMap(r => (r.findings || []).map(f => ({ ...f, area: r.area })))
log(`${found.length}/${AREAS.length} areas inventoried; ${allFindings.length} findings`)

phase('Synthesis')
const plan = await agent(
  `${RULES}

You are given a completed inventory of every area of this repository, as JSON.

Produce a CLEANUP AND RESTRUCTURE PLAN for a public Apache-2.0 repository that
must serve both human readers and coding agents.

INVENTORY:
${JSON.stringify(found, null, 1).slice(0, 60000)}

Your plan must answer, concretely and with file paths:

1. What is the minimal set of top-level directories a newcomer should see, and
   what moves, splits, or leaves?
2. Which documents must be REWRITTEN because they read as conversation rather
   than documentation? List them in priority order with the specific defect.
3. What conventions were invented by an agent and presented as project law,
   and which of those should be kept, demoted, or removed?
4. Should the iOS/macOS app live in this repo? Give a decision with reasoning
   for an App-Store-bound app in a public repo, and say exactly what would
   move if it should not.
5. What should the README contain, section by section, for a project whose
   core claim is exact law recovery with held-out proof? Give the outline
   only, not the prose.
6. What machine-readable artifacts should exist so an agent can orient itself
   without reading everything?

Be decisive. Where you are uncertain, say so rather than inventing a rationale.`,
  { label: 'synthesis', phase: 'Synthesis', effort: 'high' })

return { areas: found, findings: allFindings, plan }
