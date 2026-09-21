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
- Deployed source commit: `7f8e4e78ff8193a3db195915e4a17dd240abc3fd`
- Explorer contract: https://explorer-studio.genlayer.com/address/0xd7347AFBe443540cFfC8BeF3e38A35D5ca0a52d9
- Deploy transaction: https://explorer-studio.genlayer.com/tx/0x7b22b8dd9282c7dd3ad3fdd8c76eb89da8e544d246078ed6112937ef2d9bc044
- Offline verification: `python3 sim/check.py`, 6/6 pass on 2026-09-21
- Hosted Studio checks: deployment accepted in Normal (Full Consensus) mode;
  schema verified. Live cross-contract evaluation not run.
