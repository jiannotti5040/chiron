#!/bin/bash
# PUSH_TO_GITHUB.command — double-click this file in Finder to push the vault.
# It pushes every local commit on 'main' to github.com/jiannotti5040/chiron-vault.
# If GitHub asks for credentials it will walk you through the one-time setup.

cd "$(dirname "$0")" || exit 1
echo "── Jacob's Portfolio Vault — push to GitHub ─────────────────────"
echo
echo "Local commits waiting to go up:"
git log --oneline origin/main..main 2>/dev/null | head -30
COUNT=$(git log --oneline origin/main..main 2>/dev/null | wc -l | xargs)
echo
echo "($COUNT commits ahead of GitHub)"
echo
read -r -p "Push them now? [Y/n] " ANSWER
case "$ANSWER" in n|N) echo "Okay — nothing pushed."; exit 0;; esac

if git push origin main; then
    echo
    echo "✅ Done. Everything is on GitHub:"
    echo "   https://github.com/jiannotti5040/chiron-vault"
    echo
    echo "CI ('Chiron CI') will start running the full gate battery on this"
    echo "push automatically — check the Actions tab in a few minutes."
else
    echo
    echo "── GitHub needs to know it's you (one-time setup) ──────────────"
    if command -v gh >/dev/null 2>&1; then
        echo "Found the GitHub CLI. Starting its login (choose: GitHub.com →"
        echo "HTTPS → Login with a web browser), then this will push again."
        gh auth login && gh auth setup-git && git push origin main \
            && echo "✅ Pushed." && exit 0
    else
        echo "Easiest fix: install the GitHub CLI, then run this file again."
        echo
        echo "    1) Open Terminal and run:   brew install gh"
        echo "       (no Homebrew? install from https://cli.github.com)"
        echo "    2) Double-click this file again — it will handle the rest."
        echo
        echo "Alternative: install the GitHub Desktop app (desktop.github.com),"
        echo "open this folder in it, and click 'Push origin'."
    fi
fi
echo
read -r -p "Press Enter to close…" _
