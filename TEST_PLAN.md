# Test plan - Compositor

## Offline

1. 2 upstream PASS outcomes, mode `all`
- expected PASS when both are passed.

2. One upstream FAIL, mode `all`
- expected FAIL.

3. mode `any` with one PASS among others
- expected PASS.

4. mode `kofn` with exact threshold
- exact threshold PASS, one short of threshold NOT PASS.

5. Missing upstream outcome (pending)
- `evaluate` reverts while input remains pending.

6. Undetermined input with forced outcome
- forced PASS/FAIL path settles despite undetermined.

7. Undetermined input with undecidable policy
- expected `R_UNDETERMINED`.

8. A `positive_or_undetermined` input returns 2
- expected `R_UNDETERMINED`, not FAIL.

## Studio checks

1. Deploy with at least one upstream IC in same network and verify `open_composite`.
2. Call `get_result` for each scenario above after on-chain evaluation.
3. Confirm `evaluate` can be retried successfully after a previously pending input settles.
