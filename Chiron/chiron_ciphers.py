#!/usr/bin/env python3
# (c) 2026 Jacob Iannotti. PolyForm Noncommercial 1.0.0 - noncommercial use permitted;
# commercial rights reserved. See LICENSE.md. SPDX-License-Identifier: PolyForm-Noncommercial-1.0.0
# ============================================================================
#  chiron_ciphers.py — seed Chiron with a CRYPTOGRAPHY basis.
#
#  Generates a corpus of ciphers / codes (Caesar, ROT13, Atbash, base64, hex,
#  binary, Morse, A1Z26, reversal), lets the engine SOLVE each one ciphertext-
#  only, records every recovered symbol-transform as a verified law, and
#  assimilates the decoded messages into the Congress under "cryptography".
#  A strong, on-brand foundation for the engine's real strength: structure.
#
#  Run:  python3 chiron_ciphers.py [--memory chiron_memory.json]
# ============================================================================
import argparse
import base64
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import chiron

A = ord('A')
_R_MORSE = {v: k for k, v in chiron._MORSE.items()}

MESSAGES = [
    "ATTACK AT DAWN", "THE QUICK BROWN FOX", "MEET ME AT THE SECRET PLACE",
    "VICTORY IS NEAR", "HELLO WORLD THIS IS A TEST", "ALL YOUR BASE ARE OURS",
    "RETREAT TO THE NORTH BRIDGE", "THE KEY IS UNDER THE STONE",
    "KNOWLEDGE IS THE ONLY GOOD", "SEND REINFORCEMENTS AT NOON",
]


def caesar(t, k):
    return "".join(chr((ord(c.upper()) - A + k) % 26 + A) if c.isalpha() else c for c in t)


def atbash(t):
    return "".join(chr(A + 25 - (ord(c.upper()) - A)) if c.isalpha() else c for c in t)


def to_morse(t):
    return " ".join(_R_MORSE.get(c.upper(), "") for c in t if c.upper() in _R_MORSE or c == " ").strip()


def encoders():
    return [
        ("caesar-3",  lambda t: caesar(t, 3),  True),
        ("caesar-7",  lambda t: caesar(t, 7),  True),
        ("rot13",     lambda t: caesar(t, 13), True),
        ("atbash",    atbash,                  True),
        ("base64",    lambda t: base64.b64encode(t.encode()).decode(), False),
        ("hex",       lambda t: t.encode().hex(), False),
        ("binary",    lambda t: " ".join(format(b, "08b") for b in t.encode()), False),
        ("morse",     to_morse,                False),
        ("reverse",   lambda t: t[::-1],       False),
    ]


def main(argv=None):
    ap = argparse.ArgumentParser(description="Seed Chiron with a cryptography basis")
    ap.add_argument("--memory", default=os.path.join(HERE, "chiron_memory.json"))
    args = ap.parse_args(argv)

    org = (chiron.Chiron.load_memory(args.memory)
           if os.path.exists(args.memory) else chiron.Chiron())

    solved = total = laws = 0
    print("[ciphers] solving a cryptography corpus and seeding the Congress…")
    for msg in MESSAGES:
        for name, enc, is_symbol_transform in encoders():
            total += 1
            cipher = enc(msg)
            sol = chiron.solve_cipher(cipher)
            ok = sol["plaintext"].strip().upper().replace("  ", " ") == msg.upper()
            solved += ok
            # record the recovered transform as a verified law where one exists
            if is_symbol_transform:
                try:
                    inv = chiron.collapse(msg, cipher)
                    if getattr(inv, "verified", False):
                        org.record_growth(inv, "cryptography", source="cipher:" + name,
                                          author="Chiron solver")
                        laws += 1
                except Exception:
                    pass
            # assimilate the decoded message as cryptography knowledge
            try:
                org.assimilate(sol["plaintext"], source="cipher:%s:%s" % (name, msg[:16]),
                               author="Chiron solver", domain_hint="cryptography")
            except Exception:
                pass
            print("  [%s] %-9s %-26s -> %s" % ("OK" if ok else "  ", name, cipher[:26], sol["plaintext"][:30]))
        org.grow_concepts()

    org.save_memory(args.memory)
    st = org.state()
    print("\n[ciphers] solved %d/%d ciphers | recorded %d transform laws | "
          "Congress now %.2f MB, domains: %s"
          % (solved, total, laws, os.path.getsize(args.memory) / 1e6, st.get("domains")))
    print("[ciphers] basis written to %s" % args.memory)
    return 0


if __name__ == "__main__":
    sys.exit(main())
