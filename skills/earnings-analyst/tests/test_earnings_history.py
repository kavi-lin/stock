"""Offline contracts + actual CLI gates for earnings history. No network/model calls."""
import copy
import ast
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
ROOT = SCRIPTS.parents[2]
sys.path.insert(0, str(SCRIPTS))
import earnings_history as h
from validate import validate_payload as validate_base
from validate_infographic import validate_payload as validate_inf
from fetch import slim_income, slim_cashflow


def bundle(quarter=2):
    specs = [(2026, 2, "06-30"), (2026, 1, "03-31"), (2025, 4, "12-31"),
             (2025, 3, "09-30"), (2025, 2, "06-30"), (2025, 1, "03-31"),
             (2024, 4, "12-31"), (2024, 3, "09-30")]
    income = [{"date": f"{y}-{end}", "fiscalYear": y, "period": f"Q{q}",
               "revenue": 120 - 10 * i, "grossProfit": 60 - 5 * i,
               "operatingIncome": 30, "netIncome": 20, "epsDiluted": 2.0 - i / 10,
               "reportedCurrency": "USD", "costOfRevenue": 60 - 5 * i}
              for i, (y, q, end) in enumerate(specs)]
    if quarter == 1:
        income = income[1:]
    release = "2026-07-15" if quarter == 2 else "2026-04-15"
    d = {"ticker": "TEST", "as_of_date": release, "last_earnings_date": income[0]["date"],
         "schema_version": "V1.0", "data_source": "fixture",
         "snapshot": {"companyName": "Test", "sector": "Test", "industry": "Test", "price": 20, "marketCap": 100},
         "quarterly_pnl": income,
         "balance_sheet": [{"date": r["date"], "totalAssets": 100, "totalLiabilities": 20,
                            "totalEquity": 80, "totalCurrentAssets": 80, "totalCurrentLiabilities": 10,
                            "totalDebt": 10} for r in income],
         "cash_flow": [{"date": r["date"], "period": r["period"], "operatingCashFlow": 40,
                       "freeCashFlow": 30, "capitalExpenditure": -10, "reportedCurrency": "USD"} for r in income],
         "ttm_metrics": {}, "annual_growth": [], "valuation": {}, "analyst_grades": [],
         "derived": {"margins_8q": [], "yoy_growth": {}, "balance_health": {}, "cash_flow_quality": {}},
         "quality_flags": [], "composite_score": 60, "verdict": "MIXED",
         "score_components": {"quality": 20, "growth": 20, "valuation": 10, "analyst": 10},
         "earnings_surprises": [{"date": "2026-11-15", "revenueActual": None, "epsActual": None},
                                {"date": release, "revenueActual": income[0]["revenue"],
                                 "revenueEstimated": 105, "epsActual": 2.0, "epsEstimated": 1.8}]}
    return d


def expectation(**changes):
    e = {"statement": "Q2 revenue guidance 115–125 USD", "origin": "management", "metric": "revenue",
         "target_period": {"fiscal_year": 2026, "period": "Q2"}, "operator": "range",
         "low": 115, "high": 125, "better": "higher", "unit": "currency", "currency": "USD",
         "accounting_basis": "gaap", "fx_basis": "reported", "segment": "consolidated",
         "source_ref": "https://example.com/ir/q1", "source_quote": "We expect Q2 revenue of 115 to 125 USD.",
         "published_at": "2026-04-15"}
    e.update(changes)
    return e


def bound(**changes):
    return h.bind_expectations([expectation(**changes)], "2026-04-16T00:00:00+00:00", "original.json")[0]


def narrative(d, expectations=None):
    return {"ticker": d["ticker"], "as_of_date": d["as_of_date"], "last_earnings_date": d["last_earnings_date"],
            "fiscal_label": "fixture", "schema_version": "V1.0", "schema_kind": "infographic",
            "transcript_used": False, "headline_oneliner": "fixture",
            "surprise": h.earnings_context(d)["surprise"], "segments_q": {"is_fy_fallback": True,
            "items": [{"name": "total", "amount_usd": 100}]},
            "capital_returns": {"buyback_authorization_usd": None, "buyback_qtr_executed_usd": 0,
                                "dividend_qtr_paid_usd": 0, "total_returned_qtr_usd": 0, "announcements": []},
            "key_highlights": [{"title": "fact", "body": "fact"}] * 3, "summary": ["fact", "fact"],
            "history_schema_version": h.VERSION, "expectations": expectations or [], "observed_metrics": []}


class HistoryTest(unittest.TestCase):
    def setUp(self):
        (ROOT / "tmp").mkdir(exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / "tmp")
        self.addCleanup(self.temp.cleanup)
        self.cache = Path(self.temp.name)

    def write(self, d, inf=None):
        p = self.cache / f"{d['ticker']}_{d['last_earnings_date']}.json"
        p.write_text(json.dumps(d))
        if inf is not None:
            h.narrative_path(p).write_text(json.dumps(inf))
        return p

    def run_cli(self, script, *args):
        return subprocess.run([sys.executable, str(SCRIPTS / script), *map(str, args)], capture_output=True, text=True)

    def freeze_prior(self, expectations=None):
        old = bundle(1); inf = narrative(old, expectations if expectations is not None else [expectation()])
        c = h.build_comparison(old, self.cache, inf)
        (self.cache / "old.md").write_text("old report")
        with patch.object(h, "utcnow", return_value="2026-04-16T00:00:00+00:00"):
            return h.save_snapshot(old, inf, c, self.cache, self.cache / "old.md")

    def test_completed_event_skips_future_first(self):
        self.assertEqual(h.earnings_context(bundle())["earnings_release_date"], "2026-07-15")
        self.assertTrue(h.earnings_context(bundle())["surprise"]["revenue_beat"])

    def test_stale_or_ambiguous_event_is_unknown(self):
        d = bundle(); d["earnings_surprises"][1]["revenueActual"] = 999
        self.assertIsNone(h.earnings_context(d)["earnings_release_date"])
        d = bundle(); d["earnings_surprises"].append({**d["earnings_surprises"][1], "date": "2026-07-14"})
        self.assertIsNone(h.earnings_context(d)["earnings_release_date"])

    def test_fiscal_year_rollover(self):
        self.assertEqual(h.next_period({"fiscal_year": 2026, "period": "Q4"}), {"fiscal_year": 2027, "period": "Q1"})

    def test_financials_align_by_date_not_array_position(self):
        d = bundle(); d["cash_flow"].reverse()
        c = h.financial_comparison(d)
        self.assertEqual(c[-1]["current"]["value"], 30)
        self.assertEqual(c[0]["qoq"]["delta"], 10)
        d["cash_flow"] = d["cash_flow"][:-1]
        self.assertIsNone(h.financial_comparison(d)[-1]["current"]["value"])

    def test_zero_eps_and_negative_fcf_not_missing_or_fake_growth(self):
        d = bundle(); d["quarterly_pnl"][0]["epsDiluted"] = 0
        d["cash_flow"][1]["freeCashFlow"] = -10
        rows = h.financial_comparison(d)
        self.assertEqual(rows[1]["current"]["value"], 0)
        self.assertEqual(rows[-1]["qoq"]["delta"], 40)
        self.assertIsNone(rows[-1]["qoq"]["pct"])

    def test_missing_quarter_not_called_qoq(self):
        d = bundle(); del d["quarterly_pnl"][1]
        self.assertIsNone(h.financial_comparison(d)[0]["previous_quarter"])

    def test_currency_change_has_no_delta(self):
        d = bundle(); d["quarterly_pnl"][1]["reportedCurrency"] = "EUR"
        self.assertEqual(h.financial_comparison(d)[0]["qoq"]["reason"], "currency_mismatch")

    def test_fy_aggregation_does_not_break_q4_or_sum_eps(self):
        d = bundle(); d["quarterly_pnl"] = d["quarterly_pnl"][2:]
        rows = h.financial_comparison(d)
        self.assertEqual(rows[0]["current"]["value"], 100)
        annual = [r for r in h.metric_actuals(d) if r["target_period"] == {"fiscal_year": 2025, "period": "FY"}]
        self.assertEqual(next(r["value"] for r in annual if r["metric"] == "revenue"), 340)
        self.assertNotIn("eps_diluted", [r["metric"] for r in annual])

    def test_range_met_exceeded_and_missed(self):
        for actual, status in ((115, "met"), (125, "met"), (130, "exceeded"), (110, "missed")):
            with self.subTest(actual=actual):
                d = bundle(); d["quarterly_pnl"][0]["revenue"] = actual
                d["earnings_surprises"][1]["revenueActual"] = actual
                self.assertEqual(h.evaluate(bound(), d, [])["status"], status)

    def test_lower_and_within_range_policy(self):
        self.assertEqual(h.evaluate(bound(low=125, high=130, better="lower"), bundle(), [])["status"], "exceeded")
        self.assertEqual(h.evaluate(bound(low=125, high=130, better="within"), bundle(), [])["status"], "missed")

    def test_point_threshold_and_negative_values(self):
        for op, threshold, status in (("gte", 120, "met"), ("gte", 130, "missed"), ("lte", 130, "exceeded")):
            self.assertEqual(h.evaluate(bound(operator=op, threshold=threshold), bundle(), [])["status"], status)
        d = bundle(); d["cash_flow"][0]["freeCashFlow"] = -5
        self.assertEqual(h.evaluate(bound(metric="free_cash_flow", operator="gte", threshold=-10), d, [])["status"], "exceeded")

    def test_full_year_not_due_at_q2(self):
        result = h.evaluate(bound(target_period={"fiscal_year": 2026, "period": "FY"}), bundle(), [])
        self.assertEqual(result["status"], "pending")

    def test_fy_revenue_evaluated_only_with_four_quarters(self):
        d = bundle(); d["quarterly_pnl"] = d["quarterly_pnl"][2:]
        d["as_of_date"] = "2026-02-15"; d["last_earnings_date"] = "2025-12-31"
        d["earnings_surprises"] = [{"date": "2026-02-01", "revenueActual": 100}]
        e = bound(target_period={"fiscal_year": 2025, "period": "FY"}, low=330, high=350, published_at="2025-08-01")
        e["recorded_at"] = "2025-08-02"
        self.assertEqual(h.evaluate(e, d, [])["status"], "met")
        del d["quarterly_pnl"][3]
        self.assertEqual(h.evaluate(e, d, [])["reason"], "actual_unavailable")

    def test_basis_mismatch_cannot_pass(self):
        for changes in ({"accounting_basis": "non_gaap"}, {"currency": "EUR"}, {"fx_basis": "constant_currency"}, {"segment": "Azure"}):
            with self.subTest(changes=changes):
                self.assertEqual(h.evaluate(bound(**changes), bundle(), [])["reason"], "basis_mismatch")

    def test_custom_metric_requires_sourced_observation(self):
        e = bound(metric="azure_revenue_yoy", unit="ratio", currency=None, accounting_basis="operational",
                  fx_basis="constant_currency", segment="Azure", low=.39, high=.40)
        self.assertEqual(h.evaluate(e, bundle(), [])["reason"], "actual_unavailable")
        actual = {k: e[k] for k in (*h.BASIS_KEYS, "target_period", "source_ref", "source_quote", "published_at")}
        actual["value"] = .405
        self.assertEqual(h.evaluate(e, bundle(), [actual])["status"], "exceeded")
        self.assertEqual(h.evaluate(e, bundle(), [actual, {**actual, "value": .30}])["reason"], "conflicting_actuals")

    def test_no_post_release_backdating(self):
        for date_value in (None, "2026-07-15", "2026-07-16"):
            e = bound(); e["recorded_at"] = date_value
            self.assertEqual(h.evaluate(e, bundle(), [])["reason"], "not_recorded_before_release")

    def test_legacy_summary_is_never_counted_as_prediction(self):
        e = bound(); e["legacy_reconstructed"] = True
        self.assertEqual(h.evaluate(e, bundle(), [])["status"], "unverifiable")
        old = bundle(1); inf = narrative(old); inf["key_highlights"] = [{"body": "FY26 guidance revenue 500"}]
        items = h.legacy_expectations(inf, h.earnings_context(old)["fiscal_period"], "old.json")
        self.assertEqual(h.evaluate(items[0], bundle(), [])["status"], "pending")

    def test_no_prior_analysis_still_has_quarter_changes(self):
        c = h.build_comparison(bundle(), self.cache)
        self.assertEqual(c["previous_analysis"]["status"], "no_previous_analysis")
        self.assertEqual(c["financial_changes"][0]["qoq"]["delta"], 10)

    def test_same_quarter_rerun_is_not_previous_analysis(self):
        d = bundle(); self.write(d, narrative(d))
        self.assertEqual(h.build_comparison(d, self.cache)["previous_analysis"]["status"], "no_previous_analysis")

    def test_sidecars_not_selected_as_base(self):
        d = bundle(); p = self.write(d, narrative(d))
        (self.cache / "TEST_2099-01-01.comparison.json").write_text("{}")
        self.assertEqual(h.find_cache(self.cache, "TEST"), str(p))

    def test_snapshot_idempotent_and_versions_immutable(self):
        first = self.freeze_prior(); contents = first.read_bytes()
        self.assertEqual(self.freeze_prior(), first)
        second = self.freeze_prior([expectation(low=116)])
        self.assertNotEqual(second, first)
        self.assertEqual(first.read_bytes(), contents)

    def test_real_previous_snapshot_and_pending_carry(self):
        self.freeze_prior([expectation(), expectation(target_period={"fiscal_year": 2026, "period": "FY"})])
        d = bundle(); inf = narrative(d); c = h.build_comparison(d, self.cache, inf)
        self.assertEqual([r["status"] for r in c["expectation_audit"]], ["met", "pending"])
        (self.cache / "new.md").write_text("new report")
        path = h.save_snapshot(d, inf, c, self.cache, self.cache / "new.md")
        carried = h.read_object(path)["content"]["open_expectations"]
        self.assertEqual(len(carried), 1)
        self.assertEqual(carried[0]["recorded_at"], "2026-04-16T00:00:00+00:00")

    def test_prior_observations_revisited_without_scoring_as_promises(self):
        self.freeze_prior([])
        c = h.build_comparison(bundle(), self.cache)
        self.assertEqual(c["expectation_audit"], [])
        self.assertEqual(len(c["watch_audit"]), 5)
        self.assertEqual(c["watch_audit"][0]["direction"], "up")
        self.assertEqual(c["watch_audit"][0]["delta"], 10)
        self.assertFalse(c["watch_audit"][0]["counts_as_prediction"])

    def test_corrupt_snapshot_is_visible_warning(self):
        p = self.freeze_prior(); d = h.read_object(p); d["content"]["bundle"]["composite_score"] = 99
        p.write_text(json.dumps(d))
        c = h.build_comparison(bundle(), self.cache)
        self.assertTrue(c["warnings"])
        self.assertEqual(c["previous_analysis"]["status"], "no_previous_analysis")

    def test_strict_contract_rejects_nan_secret_url_and_missing_basis(self):
        for e in (expectation(low=float("nan")), expectation(source_ref="https://example.com/?apikey=not-a-real-key"), expectation(currency=None)):
            self.assertTrue(h.validate_items([e]))

    def test_fetch_preserves_currency_and_filing_links(self):
        r = {"reportedCurrency": "USD", "finalLink": "https://example.com/filing", "epsDiluted": 0}
        self.assertEqual(slim_income([r])[0]["reportedCurrency"], "USD")
        self.assertEqual(slim_cashflow([r])[0]["finalLink"], r["finalLink"])

    def test_validator_rejects_fabricated_pass_through_real_cli(self):
        self.freeze_prior(); d = bundle(); d["comparison"] = h.build_comparison(d, self.cache)
        self.assertEqual(validate_base(d), [])
        d["comparison"]["expectation_audit"][0]["status"] = "exceeded"
        p = self.write(d)
        proc = self.run_cli("validate.py", "--json", p)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("deterministic evaluation", proc.stderr)

    def test_narrative_wrong_event_rejected(self):
        d = bundle(); inf = narrative(d); inf["surprise"]["revenue_actual"] = None
        p = self.write(d, inf)
        proc = self.run_cli("validate_infographic.py", "--json", h.narrative_path(p))
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("matched completed event", proc.stderr)

    def test_actual_analyze_render_validate_entrypoints(self):
        self.freeze_prior(); d = bundle(); p = self.write(d, narrative(d))
        report = self.cache / "report.md"
        for script, args in (("analyze.py", ["--json", p]), ("validate.py", ["--json", p]),
                             ("render.py", ["--json", p, "--out", report]),
                             ("validate_infographic.py", ["--json", h.narrative_path(p), "--require-history"]),
                             ("validate.py", ["--json", p, "--require-history"])):
            proc = self.run_cli(script, *args)
            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
        text = report.read_text()
        self.assertIn("上次說的，這次做到嗎", text)
        self.assertIn("**達標**", text)
        self.assertIn("下次要驗證什麼", text)
        self.assertEqual(h.read_object(p)["comparison"]["expectation_audit"][0]["status"], "met")
        self.assertTrue(Path(h.read_object(p)["comparison_snapshot"]).exists())

    def test_backend_registers_both_history_gates(self):
        tree = ast.parse((ROOT / "dashboard_server.py").read_text())
        values = {}
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Name) and t.id in {"PROTOCOL_VALIDATORS", "PROTOCOL_VALIDATOR_ARGS"}:
                        values[t.id] = ast.literal_eval(node.value)
        self.assertEqual(values["PROTOCOL_VALIDATORS"]["earnings"],
                         ["skills/earnings-analyst/scripts/validate.py", "skills/earnings-analyst/scripts/validate_infographic.py"])
        self.assertEqual(values["PROTOCOL_VALIDATOR_ARGS"]["earnings"], ["{ticker}", "--require-history"])

    def test_missing_snapshot_and_changed_report_fail_completion_cli(self):
        d = bundle(); p = self.write(d, narrative(d)); report = self.cache / "report.md"
        fail = self.run_cli("validate.py", "--json", p, "--require-history")
        self.assertNotEqual(fail.returncode, 0)
        ok = self.run_cli("render.py", "--json", p, "--out", report)
        self.assertEqual(ok.returncode, 0, ok.stderr)
        frozen = h.read_object(h.read_object(p)["comparison_snapshot"])["content"]
        archived = Path(frozen["report_archive"])
        if not archived.is_absolute():
            archived = ROOT / archived
        original = archived.read_bytes()
        report.write_text("changed after commit")
        fail = self.run_cli("validate.py", "--json", p, "--require-history")
        self.assertNotEqual(fail.returncode, 0)
        self.assertIn("report changed", fail.stderr)
        self.assertEqual(archived.read_bytes(), original)

    def test_new_contract_missing_event_uses_null_not_false_beat(self):
        d = bundle(); d["earnings_surprises"] = []
        inf = narrative(d)
        self.assertIsNone(inf["surprise"]["revenue_beat"])
        self.assertEqual(validate_inf(inf, base=d), [])

    def test_bad_contract_type_has_actionable_error(self):
        d = bundle(); inf = narrative(d); inf["expectations"] = {"bad": "shape"}
        self.assertIn("observed_metrics/expectations must be a list", validate_inf(inf, base=d))

    def test_legacy_title_resolves_fy_and_retrospective_guide_is_not_promise(self):
        d = bundle(1); inf = narrative(d)
        inf["key_highlights"] = [{"title": "FY26 guide 上調", "body": "Full-year revenue guidance"},
                                 {"title": "本季毛利率", "body": "本季毛利率優於 guide"}]
        items = h.legacy_expectations(inf, h.earnings_context(d)["fiscal_period"], "old.json")
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["target_period"], {"fiscal_year": 2026, "period": "FY"})

    def test_old_flag_taxonomy_not_claimed_resolved(self):
        d = bundle(1); d["quality_flags"] = ["accruals_warning"]
        self.write(d, narrative(d))
        c = h.build_comparison(bundle(), self.cache)
        self.assertEqual(c["quality_flag_changes"]["resolved"], [])
        self.assertEqual(c["quality_flag_changes"]["definition_changed"], ["accruals_warning"])

    def test_failed_narrative_cannot_publish_or_save_snapshot(self):
        d = bundle(); inf = narrative(d); del inf["summary"]
        p = self.write(d, inf); report = self.cache / "report.md"
        proc = self.run_cli("render.py", "--json", p, "--out", report)
        self.assertNotEqual(proc.returncode, 0)
        self.assertFalse(report.exists())
        self.assertFalse((self.cache / "history").exists())

    def test_preview_does_not_rewrite_cache_or_freeze_backdated_history(self):
        d = bundle(); inf = narrative(d); del inf["history_schema_version"]
        p = self.write(d, inf); before = p.read_bytes()
        report = self.cache / "preview.md"
        proc = self.run_cli("render.py", "--json", p, "--preview", "--out", report)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(p.read_bytes(), before)
        self.assertFalse((self.cache / "history").exists())
        self.assertIn("沒有前次分析紀錄", report.read_text())


if __name__ == "__main__":
    unittest.main()
