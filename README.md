# Compositor - consensus over other contracts' verdicts

A GenLayer Intelligent Contract that computes a decision from the on-chain state
of OTHER Intelligent Contracts. The consensus object is a policy applied to
settled upstream verdicts, not text or web data.

## Consensus mechanism

New relative to the earlier primitives: composition. The contract reads several
upstream verdict contracts via `gl.get_contract_at(addr).view().get_outcome(id)`
and applies a fixed policy (all / any / k-of-n). Reading finalized state is
deterministic - every validator reads the same settled values - so the
aggregation needs no equivalence principle. The non-determinism already happened
upstream, in the contracts being read.

This supports upstream contracts with a numeric `get_outcome(id)` view and
an explicitly selected outcome scheme per input. Contracts exposing only a
string `outcome_of(id)` view require an adapter and cannot be used directly.

## Honest handling of missing signal

An UNDETERMINED upstream input propagates: a composite is never more decided than
its inputs, UNLESS the outcome is already forced (ANY with one positive is PASS
regardless; ALL with one negative is FAIL regardless; k-of-n once k positives
exist or once more than n-k are negative). A still-pending input makes evaluate
revert so it can be retried once settled, rather than producing a false verdict.

## Outcomes

- PASS / FAIL per the policy.
- UNDETERMINED when an undetermined input actually affects the result.

## API

- `open_composite(id, mode, k, input_addrs, input_ids, input_schemes)` -> policy hash
- `evaluate(id)` - permissionless; reverts if any input still pending
- `get_outcome(id)` -> 0 pending, 1 pass, 2 fail, 3 undetermined
- `get_result(id)` -> positive/settled counts and input count

## Upstream convention

Inputs must expose numeric `get_outcome(id)`. Select `standard` for 0 pending,
1 positive, 2 negative, 3 undetermined. Select
`positive_or_undetermined` for 0 pending, 1 positive, 2 undetermined, as used
by Transitive Record Clusterer and Normalized Value Extractor. The choice is
included in the immutable policy hash.

## Test plan (hosted Studio)

1. All inputs positive, mode all -> PASS.
2. One input negative, mode all -> FAIL.
3. Mode any, one positive rest negative -> PASS.
4. k-of-n threshold exactly met -> PASS; one short -> FAIL.
5. One input undetermined but outcome already forced -> settles correctly.
6. One input undetermined and outcome not forced -> UNDETERMINED.
7. One input still pending -> evaluate reverts, then succeeds once settled.

## Notes

Verify inter-contract reads with upstream contracts in the same Studio network.
Offline tests use a proxy mock, so deployment alone does not prove a live
composite evaluation.
