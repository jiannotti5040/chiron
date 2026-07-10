# Plugins (prototype)

Drop `<name>.py` in this folder and the monolith runs it without a rebuild:

    python3 chiron_monolith.py <name> [args...]

A plugin may `import chiron`, `import semic`, or any other embedded module —
the monolith's import hook resolves those to the certified embedded copies.

Two rules, both enforced by the loader:

1. **Embedded wins.** A plugin named like an embedded module is ignored.
   A plugin can *add* to the runtime; it can never replace the certified
   spine. This is what keeps the fold's zero-false-verification contract
   intact with third-party files sitting next to it.
2. **Plugins are outside the fold's claims.** `--selftest` sweeps only
   embedded modules; `--list` marks plugins as external. If your plugin
   carries gates, run them yourself: `python3 chiron_monolith.py <name> selftest`.

Status: prototype. The contract above is tested (`example_echo` +
loader behavior), but the plugin surface is one release old at most —
expect it to move.

See `example_echo.py` for the minimal shape.
