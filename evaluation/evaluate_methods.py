"""
Reproducible Evaluation & Baseline Comparison Script for LearnWhy AI (PSM147 / QE4).

Compares:
  - Baseline A (`baseline_score`): Score-based recommendations using concept mastery deficit (1 - M_c)
    and difficulty without misconception diagnosis or follow-up disambiguation.
  - Proposed B (`proposed`): Transparent misconception diagnosis + diagnostic follow-up when ambiguous
    + explainable recommendation (0.50*gap + 0.30*prereq + 0.20*difficulty) + fresh verification.

Outputs:
  - Console summary table
  - JSON artifact at `evaluation/latest_evaluation_report.json`

Usage:
  PYTHONPATH=backend python3 evaluation/evaluate_methods.py
"""
from collections import defaultdict
import json
from pathlib import Path
import statistics
import sys
import time

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, event  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.database import Base, get_db  # noqa: E402
from app.core.security import rate_limiter  # noqa: E402
from app.main import app  # noqa: E402
from app.models.entities import Activity, Concept, Question  # noqa: E402
from app.seed import seed_database  # noqa: E402


def compute_classification_metrics(
    y_true: list[str], y_pred: list[str]
) -> dict:
    labels = sorted(set(y_true) | set(y_pred))
    per_class = {}
    precisions = []
    recalls = []
    f1s = []

    for label in labels:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == label and p == label)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != label and p == label)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == label and p != label)

        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0

        per_class[label] = {
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
            "support": sum(1 for t in y_true if t == label),
        }
        precisions.append(prec)
        recalls.append(rec)
        f1s.append(f1)

    exact_matches = sum(1 for t, p in zip(y_true, y_pred) if t == p)
    return {
        "macro_precision": round(statistics.mean(precisions), 4) if precisions else 0.0,
        "macro_recall": round(statistics.mean(recalls), 4) if recalls else 0.0,
        "macro_f1": round(statistics.mean(f1s), 4) if f1s else 0.0,
        "exact_match_accuracy": round(exact_matches / len(y_true), 4) if y_true else 0.0,
        "per_class": per_class,
    }


def run_evaluation() -> dict:
    dataset_path = ROOT_DIR / "evaluation" / "labeled_evaluation_dataset.json"
    with open(dataset_path, "r", encoding="utf-8") as f:
        dataset = json.load(f)

    rate_limiter.reset()
    eval_engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        future=True,
    )

    @event.listens_for(eval_engine, "connect")
    def _fk_pragma(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    EvalSessionLocal = sessionmaker(
        autocommit=False, autoflush=False, bind=eval_engine, future=True
    )
    Base.metadata.create_all(bind=eval_engine)

    with EvalSessionLocal() as session:
        seed_database(session)
        questions_by_sid = {
            q.stable_id: q.id for q in session.query(Question).all()
        }
        activities_by_id = {
            a.id: a.stable_id for a in session.query(Activity).all()
        }

    def override_get_db():
        db = EvalSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    latencies_ms: list[float] = []
    api_errors = 0
    total_api_calls = 0

    all_cases = dataset["cases"]
    dev_cases = [c for c in all_cases if c["split"] == "dev"]
    test_cases = [c for c in all_cases if c["split"] == "held_out_test"]

    y_true_test: list[str] = []
    y_pred_test: list[str] = []
    y_pred_without_followup_test: list[str] = []

    proposed_relevance_hits = 0
    baseline_relevance_hits = 0
    proposed_verif_correct = 0
    baseline_verif_correct = 0
    proposed_error_recurred = 0
    baseline_error_recurred = 0
    completion_times: list[int] = []
    case_logs = []

    with TestClient(app) as client:
        for idx, case in enumerate(test_cases):
            rate_limiter.reset()
            # Create an isolated synthetic evaluation learner per test case
            t0 = time.perf_counter()
            reg_res = client.post(
                "/api/auth/register",
                json={
                    "email": f"eval.test.{idx}@synthetic.learnwhy.edu",
                    "password": "EvalPassword123!",
                    "full_name": f"Synthetic Eval Learner {idx}",
                    "role": "student",
                },
            )
            latencies_ms.append((time.perf_counter() - t0) * 1000.0)
            total_api_calls += 1
            if reg_res.status_code >= 400:
                api_errors += 1
                continue

            headers = {"Authorization": f"Bearer {reg_res.json()['access_token']}"}
            q_id = questions_by_sid[case["question_stable_id"]]

            # Step 1: Submit initial attempt
            t0 = time.perf_counter()
            att_res = client.post(
                "/api/attempts",
                headers=headers,
                json={"question_id": q_id, "response": case["submitted_response"]},
            )
            latencies_ms.append((time.perf_counter() - t0) * 1000.0)
            total_api_calls += 1
            if att_res.status_code >= 400:
                api_errors += 1
                continue

            att_body = att_res.json()
            diag = att_body["diagnosis"]

            pred_before_fu = (
                diag["misconception"]["code"]
                if (diag["status"] == "diagnosed" and diag["misconception"])
                else (
                    "AMBIGUOUS_NEEDS_FOLLOWUP"
                    if diag["status"] == "ambiguous_followup_needed"
                    else "INSUFFICIENT_EVIDENCE"
                )
            )
            y_pred_without_followup_test.append(pred_before_fu)

            # Step 2: If ambiguous & follow-up available, submit diagnostic follow-up
            if (
                diag["requires_diagnostic_followup"]
                and diag["followup_question"]
                and case.get("followup_response")
            ):
                fu_q_id = diag["followup_question"]["id"]
                t0 = time.perf_counter()
                fu_res = client.post(
                    f"/api/attempts/{att_body['attempt_id']}/diagnostic-follow-up",
                    headers=headers,
                    json={
                        "followup_question_id": fu_q_id,
                        "response": case["followup_response"],
                    },
                )
                latencies_ms.append((time.perf_counter() - t0) * 1000.0)
                total_api_calls += 1
                if fu_res.status_code < 400:
                    diag = fu_res.json()["diagnosis"]
                else:
                    api_errors += 1

            final_pred_label = (
                diag["misconception"]["code"]
                if (
                    diag["status"] in ("diagnosed", "resolved_by_followup")
                    and diag.get("misconception")
                )
                else "INSUFFICIENT_EVIDENCE"
            )
            y_true_test.append(case["ground_truth_misconception"])
            y_pred_test.append(final_pred_label)

            # Step 3: Compare Proposed B vs Baseline A top-1 recommendation relevance
            t0 = time.perf_counter()
            prop_rec_res = client.get(
                "/api/recommendations?strategy=proposed&refresh=true",
                headers=headers,
            )
            latencies_ms.append((time.perf_counter() - t0) * 1000.0)
            total_api_calls += 1

            t0 = time.perf_counter()
            base_rec_res = client.get(
                "/api/recommendations?strategy=baseline_score&refresh=true",
                headers=headers,
            )
            latencies_ms.append((time.perf_counter() - t0) * 1000.0)
            total_api_calls += 1

            prop_recs = prop_rec_res.json()["recommendations"]
            base_recs = base_rec_res.json()["recommendations"]

            prop_top_act = prop_recs[0]["activity"]["stable_id"] if prop_recs else None
            base_top_act = base_recs[0]["activity"]["stable_id"] if base_recs else None

            expected_act = case["expected_activity_stable_id"]
            if prop_top_act == expected_act:
                proposed_relevance_hits += 1
            if base_top_act == expected_act:
                baseline_relevance_hits += 1

            # Step 4: Complete intervention & verify (Proposed B)
            if prop_recs:
                rec_id = prop_recs[0]["id"]
                t0 = time.perf_counter()
                comp_res = client.post(
                    f"/api/interventions/{rec_id}/complete",
                    headers=headers,
                    json={"completion_seconds": case["simulated_completion_seconds"]},
                )
                latencies_ms.append((time.perf_counter() - t0) * 1000.0)
                total_api_calls += 1
                verif_q = comp_res.json()["verification_question"]

                t0 = time.perf_counter()
                ver_res = client.post(
                    f"/api/interventions/{rec_id}/verify",
                    headers=headers,
                    json={
                        "verification_question_id": verif_q["id"],
                        "response": case["simulated_verification_response_proposed"],
                        "completion_seconds": case["simulated_completion_seconds"],
                    },
                )
                latencies_ms.append((time.perf_counter() - t0) * 1000.0)
                total_api_calls += 1
                ver_body = ver_res.json()
                if ver_body["is_correct"]:
                    proposed_verif_correct += 1
                if ver_body["error_recurred"]:
                    proposed_error_recurred += 1

                # Evaluate simulated Baseline A verification response on the same verification item
                # to compare error recurrence under identical item difficulty
                base_ans = case["simulated_verification_response_baseline"]
                if base_ans.upper() == ver_body["authoritative_answer_key"].upper():
                    baseline_verif_correct += 1
                else:
                    baseline_error_recurred += 1

            completion_times.append(case["simulated_completion_seconds"])
            case_logs.append(
                {
                    "case_id": case["case_id"],
                    "question_stable_id": case["question_stable_id"],
                    "ground_truth": case["ground_truth_misconception"],
                    "predicted_after_followup": final_pred_label,
                    "proposed_top_activity": prop_top_act,
                    "baseline_top_activity": base_top_act,
                    "expected_activity": expected_act,
                }
            )

    app.dependency_overrides.clear()

    diag_metrics = compute_classification_metrics(y_true_test, y_pred_test)
    n_test = len(test_cases)
    sorted_lat = sorted(latencies_ms)
    p50_ms = sorted_lat[int(0.50 * len(sorted_lat))] if sorted_lat else 0.0
    p95_ms = sorted_lat[min(len(sorted_lat) - 1, int(0.95 * len(sorted_lat)))] if sorted_lat else 0.0

    report = {
        "evaluation_title": "LearnWhy AI — Baseline A vs. Proposed B Comparative Evaluation Report",
        "is_synthetic_benchmark": True,
        "methodology_and_limitations": (
            "SYNTHETIC / EXPERT-LABELED BENCHMARK REPORT: All diagnosis precision/recall/F1 and "
            "recommendation relevance metrics below are computed deterministically on the held-out test split "
            f"(N_test={n_test}, N_dev={len(dev_cases)}) without tuning rules on the test split. "
            "Verification accuracy and error recurrence figures reflect the documented synthetic simulation "
            "cases in `evaluation/labeled_evaluation_dataset.json`, NOT a clinical study with human students. "
            "Real educational impact requires an institutionally approved study with consented learners."
        ),
        "versions": {
            "rule_engine_version": settings.RULE_ENGINE_VERSION,
            "mastery_model_version": settings.MASTERY_MODEL_VERSION,
            "dataset_version": dataset["dataset_version"],
        },
        "sample_sizes": {
            "total_cases": len(all_cases),
            "development_split_n": len(dev_cases),
            "held_out_test_split_n": n_test,
        },
        "diagnosis_metrics_held_out_test": diag_metrics,
        "comparison_summary": {
            "baseline_a_score_based": {
                "method": "Baseline A: Score-based ranking (1 - mastery) without misconception diagnosis",
                "recommendation_relevance_rate": round(baseline_relevance_hits / n_test, 4) if n_test else 0.0,
                "simulated_immediate_verification_accuracy": round(baseline_verif_correct / n_test, 4) if n_test else 0.0,
                "simulated_error_recurrence_rate": round(baseline_error_recurred / n_test, 4) if n_test else 0.0,
            },
            "proposed_b_misconception_aware": {
                "method": "Proposed B: Misconception diagnosis + ambiguous follow-up + explainable recommendation + fresh verification",
                "recommendation_relevance_rate": round(proposed_relevance_hits / n_test, 4) if n_test else 0.0,
                "simulated_immediate_verification_accuracy": round(proposed_verif_correct / n_test, 4) if n_test else 0.0,
                "simulated_error_recurrence_rate": round(proposed_error_recurred / n_test, 4) if n_test else 0.0,
            },
        },
        "completion_time_seconds_synthetic": {
            "mean": round(statistics.mean(completion_times), 1) if completion_times else 0.0,
            "median": round(statistics.median(completion_times), 1) if completion_times else 0.0,
            "min": min(completion_times) if completion_times else 0,
            "max": max(completion_times) if completion_times else 0,
        },
        "system_performance": {
            "total_api_requests": total_api_calls,
            "api_error_rate": round(api_errors / total_api_calls, 4) if total_api_calls else 0.0,
            "latency_p50_ms": round(p50_ms, 2),
            "latency_p95_ms": round(p95_ms, 2),
            "meets_500ms_p95_target": p95_ms < 500.0,
        },
        "held_out_test_case_results": case_logs,
    }

    out_path = ROOT_DIR / "evaluation" / "latest_evaluation_report.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    return report


if __name__ == "__main__":
    rep = run_evaluation()
    print("=== LearnWhy AI Reproducible Evaluation Summary (Held-Out Test Split) ===")
    print(f"Sample sizes: N_dev={rep['sample_sizes']['development_split_n']}, N_test={rep['sample_sizes']['held_out_test_split_n']}")
    dm = rep["diagnosis_metrics_held_out_test"]
    print(f"Diagnosis Macro Precision: {dm['macro_precision']:.4f} | Macro Recall: {dm['macro_recall']:.4f} | Macro F1: {dm['macro_f1']:.4f}")
    ca = rep["comparison_summary"]["baseline_a_score_based"]
    cb = rep["comparison_summary"]["proposed_b_misconception_aware"]
    print(f"Baseline A Recommendation Relevance: {ca['recommendation_relevance_rate']*100:.1f}% vs Proposed B: {cb['recommendation_relevance_rate']*100:.1f}%")
    print(f"System Latency: p50={rep['system_performance']['latency_p50_ms']} ms, p95={rep['system_performance']['latency_p95_ms']} ms, error_rate={rep['system_performance']['api_error_rate']}")
    print("Saved full report to evaluation/latest_evaluation_report.json")
