"""Synthetic-only tests of temporal isolation, safe loading and UI semantics."""
import copy
import json
import math
import shutil
import subprocess
import tempfile
import unittest
from datetime import date,datetime,timedelta
from pathlib import Path

from healthaio import hrv_model as core
from healthaio.config import Config
from healthaio.context import Context
from healthaio.hrv_train import partition,save
from healthaio.store import write_table,Store


def records(n=1000):
    start=date(2023,1,1)
    return [{"date":start+timedelta(days=i),"hrv_ms":40+4*math.sin(i/9),"resting_hr":60+i%7,
             "sleep_min":420+i%60,"workout_min":20 if i%3==0 else 0,"steps":7000,
             "exercise_min":30,"complete":True} for i in range(n)]


def fixture(rows):
    end=max(rows)
    return {"version":core.VERSION,"selected":"median28","fit":{"kind":"median28"},"learned_fit":{"kind":"median28"},
            "created_on":(end+timedelta(days=1)).isoformat(),"trained_through":end.isoformat(),
            "source_sha256":core.fingerprint(rows,end),"interval_halfwidth_ms":8,
            "training":{"pairs":100,"hrv_days":150},
            "evaluation":{"n":1,"start":end.isoformat(),"end":end.isoformat(),"train_through":(end-timedelta(days=1)).isoformat(),
                          "mae_ms":4,"baseline_mae_ms":5,"interval_coverage":.8,
                          "cases":[{"date":end.isoformat(),"actual":40,"prediction":42,"baseline":43}]}}


class HRVModel(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.cfg=Config(root=Path(self.temp.name),data_dir=Path(self.temp.name)/"data",timezone="Australia/Melbourne")
        self.data=records(100)
        write_table(self.cfg.data_dir,"body_daily",self.data)
        self.last=self.data[-1]["date"]
        self.rows=core.clean_rows(Store(self.cfg.data_dir).rows("body_daily"),self.last)

    def tearDown(self): self.temp.cleanup()

    def ctx(self, days=1): return Context(self.cfg,now=datetime.combine(self.last+timedelta(days=days),datetime.min.time()))

    def test_feature_prefix_is_unchanged_by_future_data(self):
        at=self.last-timedelta(days=10)
        before=core.features(self.rows,at)
        changed=copy.deepcopy(self.rows)
        for d in changed:
            if d>at: changed[d]={k:9999 for k in core.FIELDS}
        self.assertEqual(before,core.features(changed,at))

    def test_partial_current_and_missing_next_day_are_not_training_labels(self):
        changed=copy.deepcopy(self.rows)
        changed[self.last]["complete"]=False
        data=core.pairs(changed)
        self.assertNotIn(self.last.isoformat(),[r["target_date"] for r in data])
        self.assertIsNone(core.features(changed,self.last))
        del changed[self.last-timedelta(days=1)]
        self.assertNotIn((self.last-timedelta(days=1)).isoformat(),[r["target_date"] for r in core.pairs(changed)])

    def test_features_need_distinct_calendar_coverage(self):
        self.assertIsNone(core.features(dict(list(self.rows.items())[-9:]),self.last))
        self.assertEqual(core.features(self.rows,self.last)["coverage"],28)

    def test_calendar_splits_do_not_use_holdout_in_selection(self):
        rows=core.clean_rows(records(),date(2030,1,1));data=core.pairs(rows)
        folds,precal,cal,dev,test=partition(data)
        for train,valid in folds:
            self.assertLess(train[-1]["target_date"],valid[0]["target_date"])
            self.assertLess(valid[-1]["target_date"],cal[0]["target_date"])
        self.assertLess(precal[-1]["target_date"],cal[0]["target_date"])
        self.assertLess(cal[-1]["target_date"],test[0]["target_date"])
        self.assertLess(dev[-1]["target_date"],test[0]["target_date"])

    def test_json_inference_matches_independent_coefficient_arithmetic(self):
        row=core.features(self.rows,self.last)
        fit={"kind":"ridge","features":["hrv_now","sleep_hours"],"medians":[0,7],"means":[0,7,0,0],
             "scales":[1,2,1,1],"coef":[.25,.1,0,0],"intercept":.01}
        expected=row["base"]*math.exp(.01+.25*row["features"]["hrv_now"]+.1*(row["features"]["sleep_hours"]-7)/2)
        self.assertAlmostEqual(core.predict(row,fit),expected,places=10)

    def test_fresh_model_private_permissions_and_stale_data_label(self):
        save(self.cfg,fixture(self.rows))
        self.assertEqual((self.cfg.root/core.FILENAME).stat().st_mode&0o777,0o600)
        fresh=core.build(self.ctx(),self.last+timedelta(days=1))
        self.assertEqual(fresh["status"],"ready")
        old=core.build(self.ctx(4),self.last+timedelta(days=4))
        self.assertEqual(old["status"],"stale_data")
        self.assertEqual(fresh["prediction"],old["prediction"])
        self.assertEqual(old["target_date"],(self.last+timedelta(days=1)).isoformat())
        json.dumps(old,allow_nan=False)

    def test_history_view_does_not_recalculate_with_future_trained_parameters(self):
        save(self.cfg,fixture(self.rows))
        p=core.build(self.ctx(),self.last-timedelta(days=5))
        self.assertEqual(p["status"],"history_only")
        self.assertNotIn("prediction",p)
        self.assertEqual(p["history"],[])

    def test_source_revision_invalidates_model_but_new_days_are_allowed(self):
        save(self.cfg,fixture(self.rows))
        extra=dict(self.data[-1],date=self.last+timedelta(days=1))
        write_table(self.cfg.data_dir,"body_daily",self.data+[extra])
        self.assertEqual(core.build(self.ctx(2),self.last+timedelta(days=2))["status"],"ready")
        self.data[-1]["hrv_ms"]=70
        write_table(self.cfg.data_dir,"body_daily",self.data+[extra])
        self.assertEqual(core.build(self.ctx(2),self.last+timedelta(days=2))["status"],"source_changed")

    def test_invalid_models_and_bad_source_fail_without_breaking_recovery(self):
        self.assertEqual(core.build(self.ctx(),self.last)["status"],"not_trained")
        for bad in ("[]","{",'{"version":"x"}',json.dumps(dict(fixture(self.rows),selected=42))):
            (self.cfg.root/core.FILENAME).write_text(bad)
            self.assertEqual(core.build(self.ctx(),self.last)["status"],"invalid_model")
        save(self.cfg,fixture(self.rows))
        with (self.cfg.data_dir/"body_daily.csv").open("a") as f: f.write("not-a-date,\n")
        self.assertEqual(core.build(self.ctx(),self.last)["status"],"invalid_source")

    @unittest.skipUnless(shutil.which("node"),"requires node")
    def test_bilingual_render_preserves_stale_date_and_no_subjective_score(self):
        save(self.cfg,fixture(self.rows))
        p=core.build(self.ctx(4),self.last+timedelta(days=4))
        web=Path(__file__).resolve().parents[1]/"healthaio/web"
        script='''globalThis.document={documentElement:{dataset:{}}};
const [web,lang,raw]=process.argv.slice(1);const {setLang}=await import(`${web}/js/i18n.js`);setLang(lang);
const {hrvModelHtml}=await import(`${web}/js/hrv-model.js`);process.stdout.write(hrvModelHtml(JSON.parse(raw)));'''
        for lang,word in (("zh","不是今天的预测"),("en","not today")):
            out=subprocess.run(["node","--input-type=module","-e",script,"--",str(web),lang,json.dumps(p)],capture_output=True,text=True,check=True).stdout
            self.assertIn(word,out);self.assertNotIn("undefined",out);self.assertNotIn("/10",out)


if __name__=="__main__": unittest.main()
