#!/bin/zsh
# Double-click me: the whole vault, alive — dashboard, launcher, assistant,
# grow control, President, and the heartbeat. One Ctrl-C in this window stops it all.
cd "$(dirname "$0")" || exit 1
echo "── Jacob's Portfolio Vault — waking the organism ────────────────"
python3 bin/chiron serve
