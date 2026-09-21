# v0.2.16
# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }

# Compositor - consensus over other contracts' verdicts
#
# The consensus object is a decision computed from the on-chain state of OTHER
# Intelligent Contracts, not from text or the web. The contract reads several
# upstream verdict contracts via gl.get_contract_at(addr).view(), applies a
# fixed policy over their outcomes, and settles its own verdict.
#
# This is a mechanism none of the earlier primitives use: composition. It lets
# the adjudicator / equivalence / aggregator family be wired into higher-order
# decisions ("release only if the rubric passed AND the facts corroborated AND
# no contradiction was found") without any one contract growing to do all of it.
#
# Determinism note: reading another contract's stored view is deterministic -
# every validator reads the same finalized state - so the aggregation itself
# needs no equivalence principle. The non-determinism already happened upstream,
# in the contracts being read. This contract's job is to compose their settled
# results honestly, including propagating their UNDETERMINED upward.

from genlayer import *
from dataclasses import dataclass
import json


R_PENDING = 0
R_PASS = 1
R_FAIL = 2
R_UNDETERMINED = 3   # any required input is itself undetermined or unsettled

# Upstream verdict convention shared by the sibling contracts:
# 0 pending, 1 positive (accepted/equivalent/corroborated/consistent),
# 2 negative, 3 undetermined. Compositor reads get_outcome() -> u256.
UP_PENDING = 0
UP_POSITIVE = 1
UP_NEGATIVE = 2
UP_UNDETERMINED = 3

SCHEME_STANDARD = "standard"  # 0 pending, 1 positive, 2 negative, 3 undetermined
SCHEME_POSITIVE_OR_UNDETERMINED = "positive_or_undetermined"  # 0, 1, 2 undetermined

MODE_ALL = "all"     # every input must be positive
MODE_ANY = "any"     # at least one positive
MODE_KOFN = "kofn"   # at least k positive

MAX_INPUTS = 8
MAX_ID_LEN = 64
MAX_INPUT_ID_LEN = 64


def _digest(text: str) -> str:
    h = Keccak256()
    h.update(text.encode("utf-8"))
    return "0x" + h.hexdigest()


def _require(condition: bool, code: str) -> None:
    if not condition:
        raise gl.vm.UserError(code)


@allow_storage
@dataclass
class Composite:
    creator: Address
    mode: str
    k: u256
    input_addrs: DynArray[str]     # addresses of upstream verdict contracts
    input_ids: DynArray[str]       # the query id to read in each upstream contract
    input_schemes: DynArray[str]
    policy_hash: str
    outcome: u256
    positive_count: u256
    settled_count: u256
    result_hash: str


class CompositeRendered(gl.Event):
    def __init__(self, composite_id: str, outcome: int, positive_count: int, /):
        pass


class Compositor(gl.Contract):
    composites: TreeMap[str, Composite]

    def __init__(self):
        pass

    @gl.public.write
    def open_composite(
        self,
        composite_id: str,
        mode: str,
        k: int,
        input_addrs: list[str],
        input_ids: list[str],
        input_schemes: list[str],
    ) -> str:
        composite_id = composite_id.strip()
        _require(composite_id != "", "EMPTY_ID")
        _require(len(composite_id) <= MAX_ID_LEN, "ID_TOO_LONG")
        _require(composite_id not in self.composites, "ID_ALREADY_USED")
        _require(mode in (MODE_ALL, MODE_ANY, MODE_KOFN), "INVALID_MODE")
        policy_k = int(k) if mode == MODE_KOFN else 0
        addrs = [str(a) for a in input_addrs]
        ids = [str(i).strip() for i in input_ids]
        _require(len(addrs) == len(ids) == len(input_schemes), "INPUT_LENGTH_MISMATCH")
        n = len(addrs)
        _require(2 <= n <= MAX_INPUTS, "INPUT_COUNT_OUT_OF_RANGE")
        _require(mode != MODE_KOFN or 1 <= k <= n, "K_OUT_OF_RANGE")
        seen: list[str] = []
        for idx in range(n):
            _require(ids[idx] != "", "EMPTY_INPUT_ID")
            _require(len(ids[idx]) <= MAX_INPUT_ID_LEN, "INPUT_ID_TOO_LONG")
            _require(
                input_schemes[idx] in (SCHEME_STANDARD, SCHEME_POSITIVE_OR_UNDETERMINED),
                "INVALID_INPUT_SCHEME",
            )
            key = addrs[idx].lower() + "|" + ids[idx]
            _require(key not in seen, "DUPLICATE_INPUT")
            seen.append(key)

        # Policy is fixed at creation: mode, k, and the exact set of upstream
        # references. Nobody can add or swap an input after seeing outcomes.
        policy_hash = _digest(
            json.dumps(
                {"mode": mode, "k": policy_k, "addrs": addrs, "ids": ids, "schemes": input_schemes},
                sort_keys=True,
            )
        )
        c = Composite(
            creator=gl.message.sender_address,
            mode=mode,
            k=u256(policy_k),
            input_addrs=DynArray(),
            input_ids=DynArray(),
            input_schemes=DynArray(),
            policy_hash=policy_hash,
            outcome=u256(R_PENDING),
            positive_count=u256(0),
            settled_count=u256(0),
            result_hash="",
        )
        for a in addrs:
            c.input_addrs.append(a)
        for i in ids:
            c.input_ids.append(i)
        for scheme in input_schemes:
            c.input_schemes.append(scheme)
        self.composites[composite_id] = c
        return policy_hash

    @gl.public.write
    def evaluate(self, composite_id: str) -> None:
        c = self.composites[composite_id]
        _require(c.outcome == u256(R_PENDING), "ALREADY_SETTLED")

        n = len(c.input_addrs)
        positive = 0
        negative = 0
        settled = 0
        any_undetermined = False
        any_pending = False

        # Deterministic reads of finalized upstream state. No equivalence
        # principle needed - all validators read identical settled values.
        for idx in range(n):
            addr = Address(c.input_addrs[idx])
            qid = c.input_ids[idx]
            upstream = gl.get_contract_at(addr)
            outcome = int(upstream.view().get_outcome(qid))
            scheme = c.input_schemes[idx]

            if outcome == UP_POSITIVE:
                positive += 1
                settled += 1
            elif outcome == UP_NEGATIVE:
                if scheme == SCHEME_STANDARD:
                    negative += 1
                    settled += 1
                else:
                    any_undetermined = True
            elif outcome == UP_UNDETERMINED:
                any_undetermined = True
            elif outcome == UP_PENDING:
                any_pending = True
            else:
                any_undetermined = True

        # If any input is still pending, the composite is not ready. This is not
        # a verdict - it stays pending and can be evaluated again later.
        if any_pending:
            raise gl.vm.UserError("INPUT_PENDING")

        # An undetermined input propagates upward: a composite cannot be more
        # decided than its inputs. This is the honest handling of missing signal.
        if any_undetermined and not self._decidable_despite_undetermined(
            c.mode, int(c.k), positive, negative, n
        ):
            self._finalize(composite_id, R_UNDETERMINED, positive, settled, "input-undetermined")
            return

        passed = self._apply_policy(c.mode, int(c.k), positive, n)
        self._finalize(
            composite_id,
            R_PASS if passed else R_FAIL,
            positive,
            settled,
            "composed",
        )

    def _apply_policy(self, mode: str, k: int, positive: int, n: int) -> bool:
        if mode == MODE_ALL:
            return positive == n
        if mode == MODE_ANY:
            return positive >= 1
        return positive >= k

    def _decidable_despite_undetermined(
        self, mode: str, k: int, positive: int, negative: int, n: int
    ) -> bool:
        # A composite can still settle despite an undetermined input if the
        # outcome is already forced. E.g. ANY with one positive is PASS
        # regardless; ALL with one negative is FAIL regardless; KOFN once k
        # positives exist (PASS) or once more than n-k are negative (FAIL).
        if mode == MODE_ANY:
            return positive >= 1
        if mode == MODE_ALL:
            return negative >= 1
        # kofn
        if positive >= k:
            return True
        if negative > (n - k):
            return True
        return False

    def _finalize(
        self, composite_id: str, outcome: int, positive: int, settled: int, note: str
    ) -> None:
        c = self.composites[composite_id]
        c.outcome = u256(outcome)
        c.positive_count = u256(positive)
        c.settled_count = u256(settled)
        c.result_hash = _digest(c.policy_hash + "|" + note + "|" + str(positive))
        CompositeRendered(composite_id, outcome, positive).emit()

    @gl.public.view
    def get_outcome(self, composite_id: str) -> u256:
        return self.composites[composite_id].outcome

    @gl.public.view
    def get_result(self, composite_id: str) -> TreeMap[str, int]:
        c = self.composites[composite_id]
        return {
            "outcome": int(c.outcome),
            "positive_count": int(c.positive_count),
            "settled_count": int(c.settled_count),
            "inputs": len(c.input_addrs),
        }
