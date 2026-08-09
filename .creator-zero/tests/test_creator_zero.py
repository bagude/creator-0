from __future__ import annotations
import importlib.util, json, tempfile, unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sp=importlib.util.spec_from_file_location("cz",ROOT/"cz.py")
cz=importlib.util.module_from_spec(sp); sp.loader.exec_module(cz)

class Tests(unittest.TestCase):
    def setUp(self):
        self.c=cz.load_json(ROOT/"contracts/root_contract.json")
        self.s=cz.load_json(ROOT/"examples/minimal_spec.json")

    def test_valid(self): cz.validate_spec(self.s,self.c)

    def test_bad_primitive(self):
        b=json.loads(json.dumps(self.s)); b["nodes"][0]["primitive"]="telepathy"
        with self.assertRaises(cz.BoundaryViolation): cz.validate_spec(b,self.c)

    def test_bad_tool(self):
        b=json.loads(json.dumps(self.s)); b["nodes"][0]["tools"].append("ProductionRoot")
        with self.assertRaises(cz.BoundaryViolation): cz.validate_spec(b,self.c)

    def test_authority_only_delegate(self):
        b=json.loads(json.dumps(self.s)); b["edges"][0]["transfers_authority"]=True
        with self.assertRaises(cz.BoundaryViolation): cz.validate_spec(b,self.c)

    def test_child_attenuates(self):
        ch=cz.derive_child_contract(self.c)
        self.assertLess(ch["max_depth"],self.c["max_depth"])
        self.assertLess(ch["max_children"],self.c["max_children"])
        self.assertTrue(set(ch["allowed_tools"])<=set(self.c["allowed_tools"]))

    def test_cycle_rejected(self):
        b=json.loads(json.dumps(self.s))
        b["edges"].append({"source":"child-creator","target":"observer","relation":"consult","requires_response":True,"response_changes_parent_state":True,"transfers_authority":False})
        with self.assertRaises(cz.BoundaryViolation): cz.validate_spec(b,self.c)

    def test_return_cycle_allowed(self):
        b=json.loads(json.dumps(self.s))
        b["edges"].append({"source":"child-creator","target":"observer","relation":"return","requires_response":False,"response_changes_parent_state":True,"transfers_authority":False})
        cz.validate_spec(b,self.c)

    def test_materialize(self):
        with tempfile.TemporaryDirectory() as td:
            rb=cz.materialize(self.s,self.c,Path(td))
            self.assertTrue(rb["generated_agents"])
            self.assertTrue(list(Path(td).glob("*.md")))

if __name__=="__main__": unittest.main()
