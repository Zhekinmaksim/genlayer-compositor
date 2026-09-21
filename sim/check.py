import hashlib
import pathlib
import types


class UserError(Exception):
    pass


class Address(str):
    pass


class TreeMap(dict):
    @classmethod
    def __class_getitem__(cls, _item):
        return cls


class DynArray(list):
    @classmethod
    def __class_getitem__(cls, _item):
        return cls


class Keccak256:
    def __init__(self):
        self.value = hashlib.sha3_256()

    def update(self, data):
        self.value.update(data)

    def hexdigest(self):
        return self.value.hexdigest()


class Event:
    def emit(self):
        pass


class Public:
    write = staticmethod(lambda fn: fn)
    view = staticmethod(lambda fn: fn)


class Upstream:
    outcomes = {}

    def __init__(self, address):
        self.address = str(address)

    def view(self):
        return self

    def get_outcome(self, item_id):
        return self.outcomes[(self.address, item_id)]


gl = types.SimpleNamespace(
    Contract=object,
    Event=Event,
    public=Public(),
    vm=types.SimpleNamespace(UserError=UserError),
    message=types.SimpleNamespace(sender_address=Address("0xaaa")),
    get_contract_at=lambda address: Upstream(address),
)
namespace = {
    "Address": Address,
    "TreeMap": TreeMap,
    "DynArray": DynArray,
    "Keccak256": Keccak256,
    "allow_storage": lambda cls: cls,
    "u256": int,
    "gl": gl,
}
root = pathlib.Path(__file__).resolve().parents[1]
source = (root / "contract.py").read_text().replace("from genlayer import *", "")
exec(compile(source, str(root / "contract.py"), "exec"), namespace)


def fresh(mode="all", k=0, schemes=None):
    compositor = namespace["Compositor"]()
    compositor.composites = TreeMap()
    compositor.open_composite(
        "case", mode, k, ["a", "b", "c"], ["x", "y", "z"],
        schemes or ["standard", "standard", "standard"],
    )
    return compositor


def set_outcomes(values):
    Upstream.outcomes = dict(zip([("a", "x"), ("b", "y"), ("c", "z")], values))


def policies():
    compositor = fresh("all")
    set_outcomes([1, 1, 1])
    compositor.evaluate("case")
    assert compositor.get_outcome("case") == namespace["R_PASS"]
    compositor = fresh("any")
    set_outcomes([2, 1, 2])
    compositor.evaluate("case")
    assert compositor.get_outcome("case") == namespace["R_PASS"]
    compositor = fresh("kofn", 2)
    set_outcomes([1, 2, 2])
    compositor.evaluate("case")
    assert compositor.get_outcome("case") == namespace["R_FAIL"]


def forced_and_unknown():
    compositor = fresh("any")
    set_outcomes([1, 3, 3])
    compositor.evaluate("case")
    assert compositor.get_outcome("case") == namespace["R_PASS"]
    compositor = fresh("all")
    set_outcomes([1, 3, 1])
    compositor.evaluate("case")
    assert compositor.get_outcome("case") == namespace["R_UNDETERMINED"]


def pending_retries():
    compositor = fresh("all")
    set_outcomes([1, 0, 1])
    try:
        compositor.evaluate("case")
    except UserError as exc:
        assert str(exc) == "INPUT_PENDING"
    else:
        raise AssertionError("INPUT_PENDING")
    set_outcomes([1, 1, 1])
    compositor.evaluate("case")
    assert compositor.get_outcome("case") == namespace["R_PASS"]


def duplicate_guard():
    compositor = namespace["Compositor"]()
    compositor.composites = TreeMap()
    try:
        compositor.open_composite("case", "all", 0, ["a", "a"], ["x", "x"], ["standard", "standard"])
    except UserError as exc:
        assert str(exc) == "DUPLICATE_INPUT"
        return
    raise AssertionError("DUPLICATE_INPUT")


def two_code_undetermined():
    compositor = fresh(
        "all", schemes=[
            "positive_or_undetermined",
            "positive_or_undetermined",
            "standard",
        ],
    )
    set_outcomes([1, 2, 1])
    compositor.evaluate("case")
    assert compositor.get_outcome("case") == namespace["R_UNDETERMINED"]


def invalid_scheme():
    compositor = namespace["Compositor"]()
    compositor.composites = TreeMap()
    try:
        compositor.open_composite("case", "all", 0, ["a", "b"], ["x", "y"], ["standard", "wrong"])
    except UserError as exc:
        assert str(exc) == "INVALID_INPUT_SCHEME"
        return
    raise AssertionError("INVALID_INPUT_SCHEME")


tests = [policies, forced_and_unknown, pending_retries, duplicate_guard, two_code_undetermined, invalid_scheme]
for test in tests:
    test()
    print("PASS", test.__name__)
print(f"{len(tests)}/{len(tests)} pass")
