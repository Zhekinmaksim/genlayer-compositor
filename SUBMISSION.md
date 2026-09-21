# Portal submission - Compositor

## Title

Compositor

## Notes under 1000 chars

```text
A GenLayer IC that composes already-settled outcomes from other IC contracts.
Upstream numeric verdicts are read via on-chain view calls to `get_outcome`,
then a fixed policy (`all`, `any`, `k-of-n`) computes this contract's outcome.
Each input commits to its outcome-code scheme, so a two-code contract's
UNDETERMINED value cannot be mistaken for a negative verdict.

This is composition-only; no web or text judgment is performed here. The
non-deterministic part remains in the upstream contracts and is treated as fixed
input. The contract is conservative with undecided upstream states and propagates
undecidability unless the policy is already forced.
```

## Evidence checklist

- GitHub: https://github.com/Zhekinmaksim/genlayer-compositor
- Commit: pending
- Explorer contract: pending
- Deploy transaction: pending
- Offline verification: `python3 sim/check.py`, 4/4 pass on 2026-09-12
- Hosted Studio checks from `TEST_PLAN.md`: pending
