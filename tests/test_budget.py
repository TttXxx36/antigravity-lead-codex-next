import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("d12",ROOT/"skills/multi-agent-dispatch/scripts/dispatch.py")
d=importlib.util.module_from_spec(spec);spec.loader.exec_module(d)

class BudgetTests(unittest.TestCase):
    def event(self,usage,turn="t",model="mock"):
        return json.dumps(dict(type="turn.completed",turn_id=turn,model=model,usage=usage))
    def test_dedup_subcategories_and_model(self):
        raw=self.event(dict(input_tokens=10,output_tokens=5,cached_input_tokens=4,reasoning_output_tokens=2))
        s=d.invocation_usage(raw+"\n"+raw)
        self.assertEqual(s["counts"]["total_tokens"],15)
        self.assertEqual(s["actual_model"],"mock")
        self.assertIsNone(s["gemini_tokens"])
    def test_conflicts_unknown(self):
        a=self.event(dict(input_tokens=10,output_tokens=5))
        b=self.event(dict(input_tokens=11,output_tokens=5))
        for raw in ("",a+"\n"+b,a+"\n"+self.event({},turn="other"),self.event({},turn=None)+"\n"+self.event({},turn=None)):
            self.assertIsNone(d.invocation_usage(raw)["counts"]["total_tokens"])
        self.assertIsNone(d.invocation_usage(self.event(dict(input_tokens=10,output_tokens=5,total_tokens=99)))["counts"]["total_tokens"])
        self.assertIsNone(d.invocation_usage(self.event(dict(input_tokens=True,output_tokens=-1)))["counts"]["input_tokens"])
        self.assertIsNone(d.invocation_usage(self.event(dict(input_tokens=10,output_tokens=5,total_tokens=True)))["counts"]["total_tokens"])
        self.assertIsNone(d.invocation_usage(a+"\n"+json.dumps({"type":"turn.failed"}))["counts"]["total_tokens"])
    def test_malformed_stream_and_unverifiable_total_fail_closed(self):
        a=self.event(dict(input_tokens=10,output_tokens=5))
        for bad in ("{broken","[]",'{"type":"turn.completed","usage":{"input_tokens":1,"input_tokens":2}}','{"value":NaN}'):
            with self.subTest(bad=bad):
                sample=d.invocation_usage(a+"\n"+bad)
                self.assertIsNone(sample["counts"]["total_tokens"])
                s=d.finish_usage(d.new_usage_store(),sample,10,"initial")
                with self.assertRaises(ValueError):
                    d.budget_timeout(d.make_budget(max_tokens=100),s,60)
        self.assertIsNone(d.invocation_usage(self.event(dict(total_tokens=15)))["counts"]["total_tokens"])
        self.assertEqual(d.invocation_usage(a+"\n\n")["counts"]["total_tokens"],15)

    def test_unknown_not_zero_and_no_double_settle(self):
        s=d.finish_usage(d.new_usage_store(),d.invocation_usage(self.event(dict(input_tokens=0,output_tokens=0))),10,"initial")
        self.assertEqual(d.usage_summary(s)["counts"]["total_tokens"],0)
        with self.assertRaises(d.StateIntegrityError):d.finish_usage(s,d.invocation_usage(""),1,"initial")
        s=d.finish_usage(s,d.invocation_usage(""),1,"next")
        self.assertIsNone(d.usage_summary(s)["counts"]["total_tokens"])
        self.assertEqual(s["unknown_turns"]["total_tokens"],1)
    def test_limits(self):
        s=d.new_usage_store()
        self.assertEqual(d.budget_timeout(d.make_budget(2,15,10),s,60),10)
        s=d.finish_usage(s,d.invocation_usage(self.event(dict(input_tokens=10,output_tokens=5))),1001,"initial")
        for limits in (d.make_budget(1),d.make_budget(max_tokens=15),d.make_budget(max_seconds=1)):
            with self.assertRaises(ValueError):d.budget_timeout(limits,s,60)
        self.assertEqual(d.budget_timeout(d.make_budget(max_seconds=10),s,60),8)
        with self.assertRaises(ValueError):d.budget_timeout(d.make_budget(max_tokens=10),d.new_usage_store(True),60)
        with self.assertRaises(d.StateIntegrityError):d.budget_timeout(d.make_budget(3),s|{"attempts":-1},60)
        for v in (0,-1,True,1.5):
            with self.assertRaises(ValueError):d.make_budget(v)
    def test_cache_route(self):
        low={"slug":"mock-fast","supported_efforts":["low","medium"]}
        high={"slug":"mock-high","supported_efforts":["high","xhigh"]}
        cache={"flagship":high,"wide_fast":low,"listed_models":[low,high],"client_version":"fixture"}
        with patch.object(d,"discover_frontier_models",return_value=cache):
            d.validate_cached_route("mock-fast","low")
            with self.assertRaises(ValueError):d.validate_cached_route("mock-fast","xhigh")
            with self.assertRaises(ValueError):d.validate_cached_route("retired-model",None)
            self.assertEqual(d.budget_route("low","x",None,None,None,"smart",False)["effort"],"low")
            self.assertEqual(d.budget_route("extreme","x",None,None,None,"smart",False)["model"],"mock-high")
            with self.assertRaises(ValueError):d.budget_route("low","x",None,"mock-fast","xhigh","smart",False)
            with self.assertRaises(ValueError):d.budget_route("low","x",None,"unknown",None,"smart",False)
        with patch.object(d,"discover_frontier_models",return_value={"flagship":None,"wide_fast":None,"listed_models":[],"client_version":None}):
            self.assertIsNone(d.budget_route("low","x",None,None,None,"smart",False)["effort"])
if __name__=="__main__":unittest.main()
