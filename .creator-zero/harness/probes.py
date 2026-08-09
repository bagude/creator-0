"""Property/edge probes for R1, R7, R8 of docs/solver_spec.md."""

import copy
import os
import sys
import time
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "src"))

from solver import solve

results = []


def probe(name, fn):
    try:
        ok, detail = fn()
    except Exception as e:  # unexpected crash inside probe harness itself
        ok, detail = False, "probe crashed: %r" % (e,)
    results.append((name, ok, detail))


def expect_value_error(arg_factory):
    def fn():
        arg = arg_factory()
        try:
            out = solve(arg)
        except ValueError as e:
            return True, "ValueError: %s" % e
        except Exception as e:
            return False, "wrong exception %r" % (e,)
        return False, "no exception, returned %r" % (out,)
    return fn


# ---- R1: every rejection clause ----
probe("R1 jobs not a list (tuple)", expect_value_error(lambda: ((0, 1, 1),)))
probe("R1 jobs not a list (None)", expect_value_error(lambda: None))
probe("R1 job wrong arity (2 elems)", expect_value_error(lambda: [(0, 1)]))
probe("R1 job wrong arity (4 elems)", expect_value_error(lambda: [(0, 1, 1, 1)]))
probe("R1 job not tuple/list (int)", expect_value_error(lambda: [5]))
probe("R1 job not tuple/list (str len 3)", expect_value_error(lambda: ["abc"]))
probe("R1 float start", expect_value_error(lambda: [(0.0, 1, 1)]))
probe("R1 float end", expect_value_error(lambda: [(0, 1.5, 1)]))
probe("R1 float weight", expect_value_error(lambda: [(0, 1, 1.0)]))
probe("R1 str field", expect_value_error(lambda: [(0, "1", 1)]))
probe("R1 bool fields (False, True, 3)", expect_value_error(lambda: [(False, True, 3)]))
probe("R1 bool weight (0, 2, True)", expect_value_error(lambda: [(0, 2, True)]))
probe("R1 zero-length end==start", expect_value_error(lambda: [(2, 2, 1)]))
probe("R1 inverted end<start", expect_value_error(lambda: [(3, 1, 1)]))
probe("R1 weight == 0", expect_value_error(lambda: [(0, 1, 0)]))
probe("R1 weight < 0", expect_value_error(lambda: [(0, 1, -2)]))
probe("R1 valid job then invalid job", expect_value_error(lambda: [(0, 2, 5), (1, 1, 1)]))
probe("R1 valid job then non-int field", expect_value_error(lambda: [(0, 2, 5), (3, 4, "x")]))
probe("R1 job as list also accepted-shape but invalid values", expect_value_error(lambda: [[0, 0, 1]]))


def r1_validation_before_work():
    # If validation happens before scheduling work, a valid-then-invalid list
    # must raise (already probed) AND must not partially mutate the argument.
    arg = [[0, 2, 5], (1, 1, 1)]
    snap = copy.deepcopy(arg)
    try:
        solve(arg)
        return False, "no exception raised"
    except ValueError:
        pass
    if arg != snap:
        return False, "argument mutated before raising: %r" % (arg,)
    return True, "raised ValueError, argument untouched"


probe("R1 validation-before-work (no partial mutation)", r1_validation_before_work)


# ---- R7 ----
probe("R7 solve([]) == (0, [])",
      lambda: ((solve([]) == (0, [])), "returned %r" % (solve([]),)))


# ---- R8: no mutation (deep snapshot), determinism, scaling ----
def r8_no_mutation():
    jobs = [[1, 4, 3], [3, 5, 2], (0, 6, 6), [4, 7, 3], (3, 8, 7),
            [5, 9, 4], (6, 10, 5), [8, 11, 2]]
    snap = copy.deepcopy(jobs)
    solve(jobs)
    if jobs != snap:
        return False, "mutated: %r" % (jobs,)
    if any(type(a) is not type(b) for a, b in zip(jobs, snap)):
        return False, "element types changed"
    return True, "deep snapshot identical"


probe("R8 argument not mutated (deep snapshot, mixed list/tuple jobs)", r8_no_mutation)


def r8_determinism():
    rng = random.Random(424242)
    for _ in range(200):
        n = rng.randint(0, 10)
        jobs = []
        for _ in range(n):
            s = rng.randint(-6, 8)
            e = s + rng.randint(1, 6)
            jobs.append((s, e, rng.randint(1, 3)))
        r1 = solve(jobs)
        r2 = solve(jobs)
        r3 = solve(list(jobs))
        if not (r1 == r2 == r3):
            return False, "nondeterministic on %r: %r %r %r" % (jobs, r1, r2, r3)
    return True, "200 repeat-call instances identical"


probe("R8 determinism (repeat calls)", r8_determinism)


def make_random_instance(n, seed):
    rng = random.Random(seed)
    jobs = []
    for _ in range(n):
        s = rng.randint(-1000, 1000)
        e = s + rng.randint(1, 50)
        jobs.append((s, e, rng.randint(1, 10)))
    return jobs


def r8_scaling():
    times = {}
    for n in (100, 200, 400):
        jobs = make_random_instance(n, seed=1000 + n)
        t0 = time.perf_counter()
        solve(jobs)
        times[n] = time.perf_counter() - t0
    detail = " ".join("n=%d:%.4fs" % (n, t) for n, t in sorted(times.items()))
    ratio_1 = times[200] / times[100] if times[100] > 0 else float("inf")
    ratio_2 = times[400] / times[200] if times[200] > 0 else float("inf")
    detail += " ratio200/100=%.2f ratio400/200=%.2f" % (ratio_1, ratio_2)
    ok = all(t < 30.0 for t in times.values())
    return ok, detail


probe("R8 empirical polynomial scaling n=100,200,400", r8_scaling)


def main():
    n_pass = sum(1 for _, ok, _ in results if ok)
    n_fail = len(results) - n_pass
    for name, ok, detail in results:
        print("%s | %s | %s" % ("PASS" if ok else "FAIL", name, detail))
    print("PROBES total=%d pass=%d fail=%d" % (len(results), n_pass, n_fail))
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
