"""Exercise the existing real provider loop without model, credentials or commands."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('review',ROOT/'deploy-review.py');review=importlib.util.module_from_spec(spec);spec.loader.exec_module(review)
class Budget(unittest.TestCase):
    def test_two_command_rounds_have_120_second_budget(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);provider=root/'provider';provider.mkdir();(provider/'auth.json').write_text('{}')
            policy=root/'policy';policy.write_text('Fixture policy')
            config=dict(adapter='codex',reviewHome=str(provider),policy=str(policy),bwrap='/bwrap',caBundle='/ca',codex='/codex',model='gpt-6-luna',effort='high',reviewTimeout=120)
            binding={'operation':'fixture'};calls=[]
            original=review.run
            def run(command,*,data,timeout,fail_on_compaction):
                calls.append(timeout)
                verdict=dict(binding,approved=None if len(calls)==1 else True,summary='fixture')
                if len(calls)==1:verdict['context']=[dict(source='candidate',path='definition.json',start=1,end=1)]
                (root/'work'/'verdict.json').write_text(json.dumps(verdict))
            review.run=run
            try:result=review.review(config,binding,{'definition.json':'fixed definition'},'fixed diff',root)
            finally:review.run=original
            self.assertTrue(result['approved']);self.assertEqual(calls,[120,120])
            self.assertLessEqual(sum(calls),240)
if __name__=='__main__':unittest.main()
