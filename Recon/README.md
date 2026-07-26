# Recon — exact ledger reconciliation with a refusal record

**Private working tool. Not part of the public proof surface.**

The billable capability in one line: *anyone can flag anomalies; the money is
in refusing to call 98% of them errors.*

On live SEC data the loop ran 1,356 → 204 → 81 → 18 findings across four rule
refinements. The 1,338 that vanished were gaps in the RULE, not errors in the
data. A report with 1,356 anomalies is worthless and dies on first rebuttal. A
report with 18 defensible ones — plus a written record of what you declined to
call an error and why — is worth a percentage of what it recovers.

## Use

```python
from recon import Ledger, Rule
led = Ledger.from_csv("invoices.csv")
led.add(Rule.identity("total", ["extended", "tax", "shipping"]))
led.add(Rule.product("extended", "qty", "unit_price"))
led.run(id_field="invoice_no")
led.add(Rule.rate_table("unit_price", key="sku", table=contract_rates))
print(led.run(id_field="invoice_no").report())
led.to_json("findings.json")
```

```bash
python3 recon.py demo    # worked example, no data needed
```

## Contract

- Money is exact `Decimal`. Never float.
- A row is checked only if every field the rule needs parses. Otherwise
  REFUSED and counted — never guessed, never coerced to zero.
- Every violation reports both sides and the exact delta.
- Refinement history is retained, so the report can show the client which
  apparent findings were your own modelling gaps.

## Rule constructors

`identity` (parts sum to total) · `product` (qty × rate) · `percentage`
(tax/commission) · `rate_table` (charged vs **contracted** rate — this is
where recovered money comes from) · `non_negative`.

## Engagement shape

Contingency: a percentage of what the findings recover. The `exposure()`
figure — absolute sum of deltas — is the number to quote.
