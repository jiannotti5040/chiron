#!/usr/bin/env python3
"""
legal_corpus.py — the hardcoded body of law, regulation, and order.

A real, citable corpus of the statutes, regulations, treaties, executive orders, technical
standards, and controlling case law that govern high-stakes autonomous decisions. This is the
authoritative source the governance, jurisdiction, precedent, and certification layers all draw
from: govern.py walks it, jurisdiction.py selects the instruments that bind a domain,
stare_decisis.py seeds doctrine from the landmark cases, holographic.py encodes it for
erasure-resilient recovery, and certify_finding.py cites it in the admissibility analysis.

Each provision is a record with: id, instrument, citation, jurisdiction, domain, a one-line
substantive summary, a severity class, and a predicate hint naming the contextual field a
compliance check would test. The corpus is grouped by domain so a caller can pull exactly the
instruments that apply to a medical, financial, military, or general-purpose AI decision.

    python3 legal_corpus.py selftest
    python3 legal_corpus.py domains
    python3 legal_corpus.py applicable military
    python3 legal_corpus.py cite AIA-ART-14
    python3 legal_corpus.py search proportionality

Sources are public primary law. Summaries are the author's plain-language compressions and are
NOT legal advice; the citation is authoritative, the summary is a pointer.
"""
import sys
import json
import argparse

# Severity classes for a non-compliance finding.
CRITICAL, MAJOR, MODERATE, MINOR = "CRITICAL", "MAJOR", "MODERATE", "MINOR"

# domain tags
AI = "ai_governance"
PRIV = "privacy"
EVID = "evidence"
WAR = "armed_conflict"
MED = "medical"
FIN = "financial"
GEN = "general"


def _p(id, instrument, citation, jurisdiction, domain, summary, severity, predicate):
    return {"id": id, "instrument": instrument, "citation": citation,
            "jurisdiction": jurisdiction, "domain": domain, "summary": summary,
            "severity": severity, "predicate": predicate}


# ---------------------------------------------------------------------------
# THE CORPUS
# ---------------------------------------------------------------------------
CORPUS = [
    # --- AI governance: EU AI Act, Regulation (EU) 2024/1689 ---
    _p("AIA-ART-5", "EU AI Act", "Reg (EU) 2024/1689, Art. 5", "EU", AI,
       "Prohibits unacceptable-risk AI: social scoring, manipulative/subliminal techniques, real-time remote biometric ID in public (with narrow exceptions).", CRITICAL, "prohibited_practice"),
    _p("AIA-ART-6", "EU AI Act", "Reg (EU) 2024/1689, Art. 6 & Annex III", "EU", AI,
       "Classifies high-risk AI systems (biometrics, critical infrastructure, law enforcement, migration, justice).", MAJOR, "high_risk_class"),
    _p("AIA-ART-9", "EU AI Act", "Reg (EU) 2024/1689, Art. 9", "EU", AI,
       "Requires a continuous risk-management system across the AI lifecycle for high-risk systems.", MAJOR, "risk_management_system"),
    _p("AIA-ART-10", "EU AI Act", "Reg (EU) 2024/1689, Art. 10", "EU", AI,
       "Data governance: training/validation/test sets must be relevant, representative, error-free and complete to the extent possible.", MAJOR, "data_governance"),
    _p("AIA-ART-13", "EU AI Act", "Reg (EU) 2024/1689, Art. 13", "EU", AI,
       "Transparency: high-risk systems must be sufficiently transparent for deployers to interpret output and use it appropriately.", MAJOR, "transparency"),
    _p("AIA-ART-14", "EU AI Act", "Reg (EU) 2024/1689, Art. 14", "EU", AI,
       "Human oversight: high-risk systems designed so a human can understand, monitor, intervene, and halt (stop button).", CRITICAL, "human_oversight"),
    _p("AIA-ART-15", "EU AI Act", "Reg (EU) 2024/1689, Art. 15", "EU", AI,
       "Accuracy, robustness and cybersecurity appropriate to the intended purpose, declared and maintained.", MAJOR, "accuracy_robustness"),
    _p("AIA-ART-50", "EU AI Act", "Reg (EU) 2024/1689, Art. 50", "EU", AI,
       "Transparency obligations: users must be informed they are interacting with AI; synthetic content marked machine-readable.", MODERATE, "ai_disclosure"),
    _p("AIA-ART-72", "EU AI Act", "Reg (EU) 2024/1689, Art. 72", "EU", AI,
       "Post-market monitoring plan proportionate to risk for high-risk systems.", MODERATE, "post_market_monitoring"),

    # --- AI governance: US ---
    _p("EO-14110", "Executive Order 14110", "E.O. 14110 (Oct 30, 2023)", "US", AI,
       "Safe, Secure, and Trustworthy AI: safety testing, red-teaming, reporting for dual-use foundation models; agency obligations.", MAJOR, "safety_testing"),
    _p("OMB-M-24-10", "OMB Memorandum", "OMB M-24-10 (Mar 28, 2024)", "US", AI,
       "Federal agency AI governance: Chief AI Officers, minimum risk-management practices for rights/safety-impacting AI.", MAJOR, "agency_governance"),
    _p("NIST-AI-RMF", "NIST AI Risk Management Framework", "NIST AI 100-1 (Jan 2023)", "US", AI,
       "Voluntary framework: GOVERN, MAP, MEASURE, MANAGE functions for trustworthy AI.", MODERATE, "rmf_function_coverage"),
    _p("NIST-AI-600", "NIST Generative AI Profile", "NIST AI 600-1 (Jul 2024)", "US", AI,
       "Risk-management profile for generative AI: CBRN, confabulation, dangerous content, data privacy.", MODERATE, "genai_risk"),
    _p("CO-SB24-205", "Colorado AI Act", "Colo. SB24-205 (2024)", "US-CO", AI,
       "Duty of reasonable care to protect consumers from algorithmic discrimination by high-risk AI; impact assessments.", MAJOR, "algorithmic_discrimination"),
    _p("AIBOR", "Blueprint for an AI Bill of Rights", "OSTP (Oct 2022)", "US", AI,
       "Five principles: safe/effective systems, algorithmic discrimination protections, data privacy, notice/explanation, human alternatives.", MINOR, "rights_principles"),

    # --- Technical standards ---
    _p("ISO-42001", "ISO/IEC 42001:2023", "ISO/IEC 42001:2023", "INT", AI,
       "AI management system (AIMS): requirements to establish, implement, maintain and improve AI governance.", MODERATE, "aims_certified"),
    _p("ISO-23894", "ISO/IEC 23894:2023", "ISO/IEC 23894:2023", "INT", AI,
       "AI risk management guidance integrating ISO 31000 with AI-specific risk sources.", MINOR, "risk_guidance"),
    _p("IEEE-7000", "IEEE 7000-2021", "IEEE Std 7000-2021", "INT", AI,
       "Model process for addressing ethical concerns during system design (value-based engineering).", MINOR, "ethical_process"),
    _p("IEEE-7001", "IEEE 7001-2021", "IEEE Std 7001-2021", "INT", AI,
       "Transparency of autonomous systems: measurable, testable transparency levels for stakeholders.", MINOR, "transparency_level"),
    _p("IEEE-7009", "IEEE 7009-2024", "IEEE Std 7009-2024", "INT", AI,
       "Fail-safe design of autonomous and semi-autonomous systems; appropriate human judgment in the loop.", MAJOR, "fail_safe"),

    # --- Privacy / data protection ---
    _p("GDPR-ART-5", "GDPR", "Reg (EU) 2016/679, Art. 5", "EU", PRIV,
       "Principles: lawfulness, fairness, transparency, purpose limitation, data minimisation, accuracy, storage limitation, integrity, accountability.", MAJOR, "data_principles"),
    _p("GDPR-ART-6", "GDPR", "Reg (EU) 2016/679, Art. 6", "EU", PRIV,
       "Processing is lawful only on a valid basis (consent, contract, legal obligation, vital/public interest, legitimate interest).", MAJOR, "lawful_basis"),
    _p("GDPR-ART-9", "GDPR", "Reg (EU) 2016/679, Art. 9", "EU", PRIV,
       "Special-category data (health, biometrics, race, etc.) processing prohibited absent a specific exception.", CRITICAL, "special_category"),
    _p("GDPR-ART-22", "GDPR", "Reg (EU) 2016/679, Art. 22", "EU", PRIV,
       "Right not to be subject to solely automated decisions with legal/significant effect; safeguards and human intervention required.", CRITICAL, "automated_decision"),
    _p("GDPR-ART-25", "GDPR", "Reg (EU) 2016/679, Art. 25", "EU", PRIV,
       "Data protection by design and by default.", MODERATE, "privacy_by_design"),
    _p("GDPR-ART-35", "GDPR", "Reg (EU) 2016/679, Art. 35", "EU", PRIV,
       "Data Protection Impact Assessment required for high-risk processing.", MAJOR, "dpia_complete"),
    _p("CCPA-1798", "CCPA/CPRA", "Cal. Civ. Code 1798.100 et seq.", "US-CA", PRIV,
       "Consumer rights to know, delete, correct, and opt out of sale/sharing; ADMT regulations.", MODERATE, "consumer_rights"),

    # --- Evidence & civil procedure (US Federal) ---
    _p("FRE-702", "Federal Rules of Evidence", "Fed. R. Evid. 702 (amended Dec 1, 2023)", "US", EVID,
       "Expert testimony admissible if based on sufficient facts, reliable principles/methods, reliably applied; proponent must show by a preponderance.", CRITICAL, "expert_reliability"),
    _p("FRE-703", "Federal Rules of Evidence", "Fed. R. Evid. 703", "US", EVID,
       "Expert may rely on inadmissible facts/data if of a type reasonably relied upon in the field.", MODERATE, "basis_of_opinion"),
    _p("FRE-705", "Federal Rules of Evidence", "Fed. R. Evid. 705", "US", EVID,
       "Expert may state an opinion and give reasons without first disclosing underlying facts, subject to disclosure on cross.", MINOR, "opinion_disclosure"),
    _p("FRE-802", "Federal Rules of Evidence", "Fed. R. Evid. 802", "US", EVID,
       "Hearsay is inadmissible unless an exception applies.", MAJOR, "hearsay"),
    _p("FRE-803-6", "Federal Rules of Evidence", "Fed. R. Evid. 803(6)", "US", EVID,
       "Business-records exception: records of regularly conducted activity made at/near the time by someone with knowledge.", MODERATE, "business_record"),
    _p("FRE-901", "Federal Rules of Evidence", "Fed. R. Evid. 901", "US", EVID,
       "Authentication: proponent must produce evidence sufficient to support a finding the item is what it is claimed to be.", MAJOR, "authentication"),
    _p("FRE-902-13", "Federal Rules of Evidence", "Fed. R. Evid. 902(13)-(14)", "US", EVID,
       "Self-authentication of machine-generated records and data copied from an electronic device, via a qualified certification.", MODERATE, "self_authentication"),
    _p("FRE-201", "Federal Rules of Evidence", "Fed. R. Evid. 201", "US", EVID,
       "Judicial notice of adjudicative facts not subject to reasonable dispute.", MINOR, "judicial_notice"),
    _p("FRCP-26", "Federal Rules of Civil Procedure", "Fed. R. Civ. P. 26(a)(2)(B)", "US", EVID,
       "Expert disclosure: written report with opinions, basis, facts, exhibits, qualifications, prior testimony, compensation.", MAJOR, "expert_disclosure"),
    _p("FRCP-37E", "Federal Rules of Civil Procedure", "Fed. R. Civ. P. 37(e)", "US", EVID,
       "Sanctions for failure to preserve electronically stored information; spoliation.", MAJOR, "esi_preservation"),
    _p("DAUBERT", "Case law", "Daubert v. Merrell Dow, 509 U.S. 579 (1993)", "US", EVID,
       "Trial judge as gatekeeper; reliability factors: testability, peer review, error rate, standards, general acceptance.", CRITICAL, "daubert_factors"),
    _p("KUMHO", "Case law", "Kumho Tire v. Carmichael, 526 U.S. 137 (1999)", "US", EVID,
       "Daubert gatekeeping extends to all expert testimony, including technical and experience-based.", MAJOR, "daubert_factors"),
    _p("JOINER", "Case law", "Gen. Elec. Co. v. Joiner, 522 U.S. 136 (1997)", "US", EVID,
       "Abuse-of-discretion review; a court may exclude opinion where an analytical gap is too great (ipse dixit).", MODERATE, "analytical_gap"),
    _p("FRYE", "Case law", "Frye v. United States, 293 F. 1013 (D.C. Cir. 1923)", "US-state", EVID,
       "General-acceptance test still controlling in some state jurisdictions.", MODERATE, "general_acceptance"),

    # --- Law of armed conflict / rules of engagement ---
    _p("API-ART-48", "Additional Protocol I", "AP I (1977), Art. 48", "INT", WAR,
       "Basic rule: parties must distinguish between civilians/combatants and civilian objects/military objectives.", CRITICAL, "distinction"),
    _p("API-ART-51", "Additional Protocol I", "AP I (1977), Art. 51", "INT", WAR,
       "Civilian population protection; prohibits indiscriminate attacks and attacks expected to cause excessive civilian harm (proportionality).", CRITICAL, "proportionality"),
    _p("API-ART-52", "Additional Protocol I", "AP I (1977), Art. 52", "INT", WAR,
       "Civilian objects may not be the object of attack; military objectives defined by nature, location, purpose, use.", CRITICAL, "civilian_object"),
    _p("API-ART-57", "Additional Protocol I", "AP I (1977), Art. 57", "INT", WAR,
       "Precautions in attack: verify targets, choose means to minimise civilian harm, cancel/suspend if disproportionate.", CRITICAL, "precaution"),
    _p("API-ART-35", "Additional Protocol I", "AP I (1977), Art. 35", "INT", WAR,
       "Means and methods of warfare are not unlimited; prohibits superfluous injury/unnecessary suffering.", MAJOR, "means_methods"),
    _p("GCIV-1949", "Geneva Convention IV", "GC IV (1949)", "INT", WAR,
       "Protection of civilian persons in time of war.", CRITICAL, "civilian_protection"),
    _p("ICRC-CIHL-14", "ICRC Customary IHL", "ICRC Customary IHL, Rule 14", "INT", WAR,
       "Proportionality in attack is a norm of customary international humanitarian law.", CRITICAL, "proportionality"),
    _p("UN-CHARTER-51", "UN Charter", "U.N. Charter, Art. 51", "INT", WAR,
       "Inherent right of individual or collective self-defence if an armed attack occurs.", MAJOR, "self_defense"),
    _p("UN-CHARTER-2-4", "UN Charter", "U.N. Charter, Art. 2(4)", "INT", WAR,
       "Members shall refrain from the threat or use of force against territorial integrity or political independence.", CRITICAL, "use_of_force"),
    _p("DODD-3000-09", "DoD Directive", "DoDD 3000.09 (2023)", "US", WAR,
       "Autonomy in weapon systems: commanders/operators exercise appropriate levels of human judgment over the use of force.", CRITICAL, "human_judgment"),
    _p("DOD-LOWM", "DoD Law of War Manual", "DoD Law of War Manual (2016, upd.)", "US", WAR,
       "Authoritative US statement of the law of war: distinction, proportionality, precautions, honour.", MAJOR, "law_of_war"),
    _p("CCW-1980", "Convention on Certain Conventional Weapons", "CCW (1980) + Protocols", "INT", WAR,
       "Restricts weapons deemed to cause excessive injury or to be indiscriminate (mines, incendiary, blinding lasers).", MAJOR, "weapon_restriction"),
    _p("ROME-ART-8", "Rome Statute", "Rome Statute (1998), Art. 8", "INT", WAR,
       "War crimes jurisdiction of the ICC, including intentionally directing attacks against civilians.", CRITICAL, "war_crime"),

    # --- Medical ---
    _p("HIPAA-164", "HIPAA", "45 C.F.R. Part 164", "US", MED,
       "Privacy and Security Rules for protected health information; minimum-necessary, safeguards, breach notification.", CRITICAL, "phi_protection"),
    _p("FDA-820", "FDA QSR", "21 C.F.R. Part 820", "US", MED,
       "Quality System Regulation for medical devices; design controls, validation.", MAJOR, "device_quality"),
    _p("FDA-SAMD", "FDA Software as a Medical Device", "FDA SaMD / PCCP guidance (2023-25)", "US", MED,
       "Risk-based oversight of AI/ML SaMD; predetermined change control plans.", MAJOR, "samd_oversight"),
    _p("EU-MDR", "EU Medical Device Regulation", "Reg (EU) 2017/745", "EU", MED,
       "Conformity, clinical evaluation, post-market surveillance for medical devices including software.", MAJOR, "mdr_conformity"),

    # --- Financial ---
    _p("SEC-10B5", "SEC Rule 10b-5", "17 C.F.R. 240.10b-5", "US", FIN,
       "Prohibits fraud, material misstatement/omission, and manipulative practices in connection with securities.", CRITICAL, "securities_fraud"),
    _p("REG-SCI", "Regulation SCI", "17 C.F.R. 242.1000 et seq.", "US", FIN,
       "Systems compliance and integrity for key market infrastructure; capacity, resiliency, security.", MAJOR, "systems_integrity"),
    _p("FINRA-3110", "FINRA Rule 3110", "FINRA Rule 3110", "US", FIN,
       "Supervision: reasonably designed supervisory system to achieve compliance, including of algorithmic activity.", MAJOR, "supervision"),
    _p("MIFID-17", "MiFID II", "Dir. 2014/65/EU, Art. 17", "EU", FIN,
       "Algorithmic trading controls: testing, kill switches, risk limits, market-making obligations.", MAJOR, "algo_trading_controls"),
    _p("EU-MAR", "Market Abuse Regulation", "Reg (EU) 596/2014", "EU", FIN,
       "Prohibits insider dealing and market manipulation; surveillance obligations.", CRITICAL, "market_abuse"),
    _p("DODD-FRANK", "Dodd-Frank Act", "Pub. L. 111-203 (2010)", "US", FIN,
       "Systemic-risk, consumer-protection, and transparency reforms for financial markets.", MODERATE, "systemic_risk"),

    # --- General / cross-cutting ---
    _p("NIST-CSF", "NIST Cybersecurity Framework", "NIST CSF 2.0 (2024)", "US", GEN,
       "Govern, Identify, Protect, Detect, Respond, Recover functions for cybersecurity risk.", MODERATE, "cyber_function"),
    _p("ISO-27001", "ISO/IEC 27001:2022", "ISO/IEC 27001:2022", "INT", GEN,
       "Information security management system requirements.", MODERATE, "isms_certified"),
    _p("OECD-AI", "OECD AI Principles", "OECD/LEGAL/0449 (2019, upd. 2024)", "INT", AI,
       "Inclusive growth, human-centred values, transparency, robustness, accountability.", MINOR, "oecd_principles"),
]

# index by domain and id
BY_ID = {p["id"]: p for p in CORPUS}
DOMAINS = sorted({p["domain"] for p in CORPUS})

# which domains' instruments bind a given operating jurisdiction (the practical mapping)
DOMAIN_BINDINGS = {
    "military": [WAR, AI, EVID, GEN],
    "medical": [MED, PRIV, AI, EVID, GEN],
    "financial": [FIN, AI, PRIV, EVID, GEN],
    "law_enforcement": [AI, PRIV, EVID, WAR, GEN],
    "creative": [AI, PRIV, GEN],
    "general": [AI, PRIV, GEN, EVID],
}


# ---------------------------------------------------------------------------
# Query API
# ---------------------------------------------------------------------------
def cite(provision_id):
    p = BY_ID.get(provision_id)
    return p["citation"] if p else None


def by_domain(domain):
    return [p for p in CORPUS if p["domain"] == domain]


def by_instrument(name):
    n = name.lower()
    return [p for p in CORPUS if n in p["instrument"].lower()]


def applicable(operating_domain):
    """Return every provision that binds an operating domain (e.g. 'military', 'medical')."""
    doms = DOMAIN_BINDINGS.get(operating_domain, DOMAIN_BINDINGS["general"])
    seen, out = set(), []
    for d in doms:
        for p in by_domain(d):
            if p["id"] not in seen:
                seen.add(p["id"])
                out.append(p)
    return out


def search(term):
    t = term.lower()
    return [p for p in CORPUS if t in p["summary"].lower() or t in p["predicate"].lower()
            or t in p["instrument"].lower() or t in p["citation"].lower()]


def predicates(operating_domain=None):
    src = applicable(operating_domain) if operating_domain else CORPUS
    return sorted({p["predicate"] for p in src})


def corpus_vector():
    """Deterministic numeric fingerprint of the whole corpus, for holographic encoding."""
    import hashlib
    out = []
    for p in CORPUS:
        h = hashlib.sha256((p["id"] + p["citation"]).encode()).digest()
        out.append((h[0] + 256 * h[1]) / 65535.0)
    return out


def stats():
    from collections import Counter
    return {
        "provisions": len(CORPUS),
        "instruments": len({p["instrument"] for p in CORPUS}),
        "jurisdictions": sorted({p["jurisdiction"] for p in CORPUS}),
        "by_domain": dict(Counter(p["domain"] for p in CORPUS)),
        "by_severity": dict(Counter(p["severity"] for p in CORPUS)),
    }


# ---------------------------------------------------------------------------
# selftest + CLI
# ---------------------------------------------------------------------------
def _selftest():
    checks = []

    def ok(name, cond):
        checks.append((name, bool(cond)))

    ok("corpus has >= 60 provisions", len(CORPUS) >= 60)
    ok("every id unique", len(BY_ID) == len(CORPUS))
    ok("every provision well-formed", all(all(k in p for k in
        ("id", "instrument", "citation", "jurisdiction", "domain", "summary", "severity", "predicate"))
        for p in CORPUS))
    ok("cite resolves Daubert", "509 U.S. 579" in (cite("DAUBERT") or ""))
    ok("military pulls law-of-armed-conflict", any(p["domain"] == WAR for p in applicable("military")))
    ok("medical pulls HIPAA", any(p["id"] == "HIPAA-164" for p in applicable("medical")))
    ok("financial pulls market-abuse", any(p["id"] == "EU-MAR" for p in applicable("financial")))
    ok("creative does NOT pull armed-conflict", not any(p["domain"] == WAR for p in applicable("creative")))
    ok("search proportionality finds AP I 51", any(p["id"] == "API-ART-51" for p in search("proportionality")))
    ok("every severity is a known class", all(p["severity"] in (CRITICAL, MAJOR, MODERATE, MINOR) for p in CORPUS))
    ok("corpus_vector length matches", len(corpus_vector()) == len(CORPUS))
    ok("EU AI Act human oversight is CRITICAL", BY_ID["AIA-ART-14"]["severity"] == CRITICAL)

    passed = sum(1 for _, c in checks if c)
    for n, c in checks:
        if not c:
            print(f"  FAIL: {n}")
    print(f"  legal_corpus.py self-test: {passed}/{len(checks)} passed  ({len(CORPUS)} provisions)")
    return passed == len(checks)


def main(argv=None):
    ap = argparse.ArgumentParser(description="The hardcoded corpus of law, regulation, and order.")
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("selftest")
    sub.add_parser("domains")
    sub.add_parser("stats")
    a = sub.add_parser("applicable"); a.add_argument("domain")
    c = sub.add_parser("cite"); c.add_argument("id")
    s = sub.add_parser("search"); s.add_argument("term")
    args = ap.parse_args(argv)

    if args.cmd == "selftest":
        return 0 if _selftest() else 1
    if args.cmd == "domains":
        print(json.dumps({"domains": DOMAINS, "operating_domains": list(DOMAIN_BINDINGS)}, indent=2)); return 0
    if args.cmd == "stats":
        print(json.dumps(stats(), indent=2)); return 0
    if args.cmd == "applicable":
        out = [{"id": p["id"], "citation": p["citation"], "severity": p["severity"], "summary": p["summary"]}
               for p in applicable(args.domain)]
        print(json.dumps(out, indent=2)); return 0
    if args.cmd == "cite":
        p = BY_ID.get(args.id)
        print(json.dumps(p, indent=2) if p else f"no such provision: {args.id}"); return 0
    if args.cmd == "search":
        print(json.dumps([{"id": p["id"], "citation": p["citation"]} for p in search(args.term)], indent=2)); return 0
    print(json.dumps(stats(), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
