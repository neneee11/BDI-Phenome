import json
import math
import os
import sqlite3
import urllib.error
import urllib.request
import warnings
from datetime import datetime
from typing import Any, Dict, Iterable, List, Mapping, Optional

import joblib
import pandas as pd

try:
    from . import config
except ImportError:
    import config  # type: ignore


def load_json(path) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def loads(value: Optional[str]) -> Any:
    return json.loads(value) if value else None


def as_float(value: Any) -> float:
    try:
        value = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Value {value!r} is not numeric") from exc
    if not math.isfinite(value):
        raise ValueError(f"Value {value!r} is not finite")
    return value


class ModelService:
    def __init__(self) -> None:
        self.selected_features = load_json(config.SELECTED_FEATURES_PATH)["selected_top6_metabolite_features"]
        self.scaler_stats = load_json(config.SCALER_STATS_PATH)
        self.rule_thresholds = pd.read_csv(config.RULE_THRESHOLDS_PATH)
        self.feature_definitions = self._load_feature_definitions()
        self.metrics = self._load_metrics()
        self.confusion_matrix = self._load_confusion_matrix()
        self.group_split = load_json(config.GROUP_SPLIT_METADATA_PATH)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.model = joblib.load(config.MODEL_PATH)

    def _load_feature_definitions(self) -> Dict[str, Dict[str, Any]]:
        summary = pd.read_csv(config.FEATURE_SUMMARY_PATH)
        importance = pd.read_csv(config.FEATURE_IMPORTANCE_PATH)
        imp = dict(zip(importance["metabolite"], importance["importance"]))
        out: Dict[str, Dict[str, Any]] = {}
        for _, row in summary.iterrows():
            metabolite = row["metabolite"]
            out[metabolite] = {
                "metabolite": metabolite,
                "postop_pattern": str(row["postop_pattern"]),
                "metabolic_axis": str(row["metabolic_axis"]),
                "importance": round(float(imp.get(metabolite, 0.0)), 4),
            }
        return out

    def _load_metrics(self) -> Dict[str, Any]:
        best = load_json(config.MODEL_METADATA_PATH).get("best_balanced_choice", {})
        return {
            "model_name": "ExtraTreesClassifier",
            "roc_auc": round(float(best["test_roc_auc"]), 3),
            "accuracy": round(float(best["test_accuracy"]), 3),
            "f1": round(float(best["test_f1"]), 3),
            "precision": round(float(best["test_precision"]), 3),
            "recall": round(float(best["test_recall"]), 3),
            "balanced_accuracy": round(float(best["test_balanced_accuracy"]), 3),
            "auc_gap": round(float(best["auc_gap_train_minus_test"]), 3),
            "n_estimators": int(best["n_estimators"]),
            "max_depth": str(best["max_depth"]),
            "min_samples_leaf": int(best["min_samples_leaf"]),
        }

    def _load_confusion_matrix(self) -> Dict[str, Any]:
        cm = pd.read_csv(config.CONFUSION_MATRIX_PATH)
        return {
            "labels": ["Preop", "Post-op"],
            "matrix": [
                [int(cm.loc[0, "pred_preop"]), int(cm.loc[0, "pred_postop"])],
                [int(cm.loc[1, "pred_preop"]), int(cm.loc[1, "pred_postop"])],
            ],
        }

    def log1p_values(self, metabolites: Mapping[str, Any], value_type: str = "log1p") -> Dict[str, float]:
        values = {}
        for feature in self.selected_features:
            if feature not in metabolites:
                raise ValueError(f"Missing required metabolite: {feature}")
            value = as_float(metabolites[feature])
            values[feature] = math.log1p(max(value, 0.0)) if value_type == "raw" else value
        return values

    def scale_values(self, log_values: Mapping[str, float]) -> Dict[str, float]:
        means = self.scaler_stats["train_means_log1p"]
        scales = self.scaler_stats["train_scales_std"]
        return {f: (float(log_values[f]) - float(means[f])) / float(scales[f]) for f in self.selected_features}

    def rule_score(self, scaled_values: Mapping[str, float]) -> Dict[str, Any]:
        matched, unmatched = [], []
        for _, row in self.rule_thresholds.iterrows():
            metabolite = str(row["metabolite"])
            direction = str(row["direction_for_postop_like"])
            threshold = float(row["train_median_threshold_scaled"])
            value = float(scaled_values[metabolite])
            ok = value < threshold if direction == "low" else value > threshold
            payload = {
                "metabolite": metabolite,
                "direction": direction,
                "value_scaled": round(value, 3),
                "threshold_scaled": round(threshold, 3),
                "signal": str(row.get("postop_signal", "")),
            }
            (matched if ok else unmatched).append(payload)

        score = len(matched)
        if score <= 2:
            state, flag = "preop-like", "closer dietitian follow-up"
        elif score == 3:
            state, flag = "transition", "monitor next follow-up"
        else:
            state, flag = "post-op-like", "routine follow-up"
        return {
            "score": score,
            "state": state,
            "flag": flag,
            "matched_rules": matched,
            "unmatched_rules": unmatched,
            "reasons": ", ".join(r["metabolite"] for r in matched) if matched else "no post-op-like rule matched",
        }

    def predict(self, metabolites: Mapping[str, Any], value_type: str = "log1p") -> Dict[str, Any]:
        log_values = self.log1p_values(metabolites, value_type)
        scaled_values = self.scale_values(log_values)
        X = pd.DataFrame([{f: scaled_values[f] for f in self.selected_features}])
        proba = float(self.model.predict_proba(X)[0][1])
        label = int(proba >= 0.5)
        rules = self.rule_score(scaled_values)

        biomarkers = []
        for feature in self.selected_features:
            definition = self.feature_definitions[feature]
            rule_row = self.rule_thresholds[self.rule_thresholds["metabolite"] == feature].iloc[0]
            direction = str(rule_row["direction_for_postop_like"])
            threshold = float(rule_row["train_median_threshold_scaled"])
            scaled = float(scaled_values[feature])
            postop_like = scaled < threshold if direction == "low" else scaled > threshold
            biomarkers.append(
                {
                    "metabolite": feature,
                    "log1p_value": round(float(log_values[feature]), 3),
                    "scaled_value": round(scaled, 3),
                    "postop_pattern": definition["postop_pattern"],
                    "metabolic_axis": definition["metabolic_axis"],
                    "importance": definition["importance"],
                    "postop_like": bool(postop_like),
                    "rule_direction": direction,
                    "threshold_scaled": round(threshold, 3),
                }
            )
        biomarkers.sort(key=lambda x: x["importance"], reverse=True)

        return {
            "predicted_label": label,
            "predicted_label_name": "post-op" if label == 1 else "preop",
            "post_op_probability": round(proba, 4),
            "preop_probability": round(1.0 - proba, 4),
            "rule_recovery_score": rules["score"],
            "rule_recovery_state": rules["state"],
            "nutrition_followup_flag": rules["flag"],
            "rule_reasons": rules["reasons"],
            "matched_rules": rules["matched_rules"],
            "unmatched_rules": rules["unmatched_rules"],
            "biomarkers": biomarkers,
            "input_log1p": {k: round(v, 4) for k, v in log_values.items()},
            "input_scaled": {k: round(v, 4) for k, v in scaled_values.items()},
        }

    def metadata(self) -> Dict[str, Any]:
        return {
            "selected_features": self.selected_features,
            "feature_definitions": self.feature_definitions,
            "metrics": self.metrics,
            "confusion_matrix": self.confusion_matrix,
            "group_split": self.group_split,
        }


class DataRepository:
    def __init__(self, model_service: ModelService) -> None:
        self.model_service = model_service
        self.clean_df: Optional[pd.DataFrame] = None

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(config.DATABASE_PATH)
        conn.row_factory = sqlite3.Row
        return conn

    def initialize(self, force_rebuild: bool = True) -> None:
        config.DATABASE_DIR.mkdir(parents=True, exist_ok=True)
        with self.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS samples (
                    sample_name TEXT PRIMARY KEY,
                    subject_id TEXT,
                    time_point TEXT,
                    time_order INTEGER,
                    label_preop_postop INTEGER,
                    label_name TEXT,
                    all_metabolites_json TEXT NOT NULL,
                    top6_metabolites_json TEXT NOT NULL,
                    prediction_json TEXT NOT NULL,
                    predicted_label INTEGER,
                    predicted_label_name TEXT,
                    post_op_probability REAL,
                    recovery_score INTEGER,
                    recovery_state TEXT,
                    nutrition_followup_flag TEXT,
                    rule_reasons TEXT,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS app_predictions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    sample_name TEXT,
                    input_json TEXT NOT NULL,
                    prediction_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
                """
            )
        if force_rebuild:
            self.rebuild_from_artifacts()

    def load_clean_data(self) -> pd.DataFrame:
        if self.clean_df is None:
            self.clean_df = pd.read_csv(config.EDA_CLEAN_DATA)
        return self.clean_df.copy()

    def rebuild_from_artifacts(self) -> None:
        df = self.load_clean_data()
        features = self.model_service.selected_features
        all_features = self.model_service.scaler_stats["feature_columns"]
        now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        rows = []
        for _, row in df.iterrows():
            all_metabolites = {col: float(row[col]) for col in all_features if col in row}
            top6 = {feature: float(row[feature]) for feature in features}
            pred = self.model_service.predict(top6, "log1p")
            label = 0 if str(row["time_point"]) == "preop" else 1
            rows.append(
                (
                    str(row["Sample Name"]),
                    str(row["subject_id"]),
                    str(row["time_point"]),
                    int(row["time_order"]),
                    label,
                    "preop" if label == 0 else "post-op",
                    dumps(all_metabolites),
                    dumps(top6),
                    dumps(pred),
                    int(pred["predicted_label"]),
                    str(pred["predicted_label_name"]),
                    float(pred["post_op_probability"]),
                    int(pred["rule_recovery_score"]),
                    str(pred["rule_recovery_state"]),
                    str(pred["nutrition_followup_flag"]),
                    str(pred["rule_reasons"]),
                    now,
                )
            )
        with self.connect() as conn:
            conn.execute("DELETE FROM samples")
            conn.executemany(
                """
                INSERT INTO samples VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                rows,
            )

    def summary(self) -> Dict[str, Any]:
        df = self.load_clean_data()
        counts = df.groupby(["time_order", "time_point"]).size().reset_index(name="n").sort_values("time_order")
        with self.connect() as conn:
            recovery = [dict(r) for r in conn.execute("SELECT recovery_state, COUNT(*) n FROM samples GROUP BY recovery_state")]
            predicted = [dict(r) for r in conn.execute("SELECT predicted_label_name, COUNT(*) n FROM samples GROUP BY predicted_label_name")]
        return {
            "n_samples": int(len(df)),
            "n_subjects": int(df["subject_id"].nunique()),
            "n_metabolites": int(len(self.model_service.scaler_stats["feature_columns"])),
            "n_selected_features": int(len(self.model_service.selected_features)),
            "timepoint_counts": [
                {"time_point": str(r["time_point"]), "label": config.TIMEPOINT_LABELS.get(str(r["time_point"]), str(r["time_point"])), "n": int(r["n"])}
                for _, r in counts.iterrows()
            ],
            "recovery_state_counts": recovery,
            "predicted_state_counts": predicted,
            "metrics": self.model_service.metrics,
        }

    def list_samples(self, q: str = "", state: str = "", limit: int = 120) -> List[Dict[str, Any]]:
        where, params = [], []
        if q:
            where.append("(sample_name LIKE ? OR subject_id LIKE ?)")
            params += [f"%{q}%", f"%{q}%"]
        if state:
            where.append("recovery_state = ?")
            params.append(state)
        sql = """
            SELECT sample_name, subject_id, time_point, label_name, predicted_label_name,
                   post_op_probability, recovery_score, recovery_state, nutrition_followup_flag
            FROM samples
        """
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY time_order, sample_name LIMIT ?"
        params.append(limit)
        with self.connect() as conn:
            return [dict(row) for row in conn.execute(sql, params)]

    def get_sample(self, sample_name: str) -> Optional[Dict[str, Any]]:
        with self.connect() as conn:
            row = conn.execute("SELECT * FROM samples WHERE sample_name = ?", (sample_name,)).fetchone()
        if row is None:
            return None
        item = dict(row)
        item["all_metabolites"] = loads(item.pop("all_metabolites_json"))
        item["top6_metabolites"] = loads(item.pop("top6_metabolites_json"))
        item["prediction"] = loads(item.pop("prediction_json"))
        return item

    def save_custom_prediction(self, source: str, input_payload: Dict[str, Any], prediction: Dict[str, Any]) -> int:
        now = datetime.utcnow().isoformat(timespec="seconds") + "Z"
        with self.connect() as conn:
            cur = conn.execute(
                "INSERT INTO app_predictions (source, sample_name, input_json, prediction_json, created_at) VALUES (?, ?, ?, ?, ?)",
                (source, input_payload.get("sample_name"), dumps(input_payload), dumps(prediction), now),
            )
            return int(cur.lastrowid)

    def trajectories(self) -> Dict[str, Any]:
        df = self.load_clean_data()
        features = self.model_service.selected_features
        grouped = df.groupby(["time_order", "time_point"])[features].median().reset_index().sort_values("time_order")
        return {
            "value_type": "median log1p abundance",
            "series": [
                {
                    "metabolite": feature,
                    "postop_pattern": self.model_service.feature_definitions[feature]["postop_pattern"],
                    "points": [
                        {"time_point": str(r["time_point"]), "label": config.TIMEPOINT_LABELS.get(str(r["time_point"]), str(r["time_point"])), "value": round(float(r[feature]), 3)}
                        for _, r in grouped.iterrows()
                    ],
                }
                for feature in features
            ],
        }

    def performance(self) -> Dict[str, Any]:
        meta = self.model_service.metadata()
        return {
            "metrics": meta["metrics"],
            "confusion_matrix": meta["confusion_matrix"],
            "group_split": meta["group_split"],
            "features": list(meta["feature_definitions"].values()),
        }


SYSTEM_PROMPT = """You are a clinical decision-support assistant for an NMR metabolomics bariatric-surgery prototype.
Answer in Thai, concise and careful. Do not diagnose disease."""


def local_assistant_answer(question: str, sample: Optional[Dict[str, Any]], summary: Dict[str, Any]) -> str:
    q = question.lower()
    sample_text = ""
    if sample:
        pred = sample["prediction"]
        sample_text = (
            f"\n\nตัวอย่าง {sample['sample_name']}: ทำนาย {pred['predicted_label_name']} "
            f"(post-op probability {pred['post_op_probability']:.2f}), recovery score "
            f"{pred['rule_recovery_score']}/6 = {pred['rule_recovery_state']}. เหตุผลหลัก: {pred['rule_reasons']}."
        )
    if "score" in q or "คะแนน" in q:
        return "Recovery score คือคะแนน 0-6 จาก biomarker 6 ตัว: 0-2 = preop-like, 3 = transition, 4-6 = post-op-like. ใช้ช่วยจัดลำดับการติดตามโภชนาการ ไม่ใช่คำวินิจฉัย." + sample_text
    if "model" in q or "โมเดล" in q or "auc" in q:
        m = summary.get("metrics", {})
        return f"โมเดลใช้ ExtraTreesClassifier กับ top-6 metabolites. Test ROC-AUC {m.get('roc_auc')}, Accuracy {m.get('accuracy')}, F1 {m.get('f1')}, AUC gap {m.get('auc_gap')} โดยแบ่ง train/test ตาม subject_id เพื่อลด leakage." + sample_text
    if "สาร" in q or "biomarker" in q or "metabolite" in q:
        return "Top-6 คือ Dimethyl sulfone, L-valine, isopropanol, lipoproteins, glycine และ L-leucine. Pattern หลังผ่าคือ Dimethyl sulfone/glycine เพิ่ม ส่วน L-valine/L-leucine/lipoproteins/isopropanol ลด." + sample_text
    return "ระบบนี้ใช้ NMR metabolite profile เพื่อบอกว่า metabolic state คล้ายก่อนผ่าหรือหลังผ่า พร้อม post-op probability, recovery score, biomarker reasons และ nutrition follow-up flag." + sample_text


def cloud_assistant_answer(question: str, sample: Optional[Dict[str, Any]], summary: Dict[str, Any]) -> Optional[str]:
    api_key = os.environ.get("OPENAI_API_KEY")
    model = os.environ.get("OPENAI_MODEL")
    if not api_key or not model:
        return None
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Question: {question}\nContext: {dumps({'summary': summary, 'sample': sample})[:8000]}"},
        ],
        "temperature": 0.2,
    }
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data["choices"][0]["message"]["content"]
    except (urllib.error.URLError, KeyError, TimeoutError, json.JSONDecodeError):
        return None


def assistant_answer(question: str, sample: Optional[Dict[str, Any]], summary: Dict[str, Any]) -> Dict[str, Any]:
    cloud = cloud_assistant_answer(question, sample, summary)
    if cloud:
        return {"mode": "llm", "answer": cloud}
    return {"mode": "local_assistant", "answer": local_assistant_answer(question, sample, summary)}

