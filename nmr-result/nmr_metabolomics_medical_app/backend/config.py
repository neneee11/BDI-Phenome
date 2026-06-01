from pathlib import Path


APP_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = APP_ROOT.parent
FRONTEND_DIR = APP_ROOT / "frontend"
DATABASE_DIR = APP_ROOT / "database"
DATABASE_PATH = DATABASE_DIR / "nmr_metabolomics.sqlite"

EDA_CLEAN_DATA = PROJECT_ROOT / "eda_outputs" / "mtbls242_log1p_sample_by_metabolite.csv"
MODEL_PATH = PROJECT_ROOT / "modeling_outputs" / "final_model" / "extratreesentr_top6.joblib"
SCALER_STATS_PATH = PROJECT_ROOT / "modeling_outputs" / "scaler_train_statistics.json"
SELECTED_FEATURES_PATH = PROJECT_ROOT / "modeling_outputs" / "selected_top6_metabolite_features.json"
FEATURE_SUMMARY_PATH = PROJECT_ROOT / "modeling_outputs" / "feature_selection_top6_summary.csv"
FEATURE_IMPORTANCE_PATH = PROJECT_ROOT / "modeling_outputs" / "extratreesentr_top6" / "feature_importance.csv"
MODEL_METADATA_PATH = PROJECT_ROOT / "modeling_outputs" / "extratreesentr_complexity_tuning" / "metadata.json"
CONFUSION_MATRIX_PATH = PROJECT_ROOT / "modeling_outputs" / "extratreesentr_complexity_tuning" / "best_model_confusion_matrix.csv"
GROUP_SPLIT_METADATA_PATH = PROJECT_ROOT / "modeling_outputs" / "group_split_metadata.json"
RULE_THRESHOLDS_PATH = PROJECT_ROOT / "modeling_outputs" / "rule_based_recovery" / "rule_thresholds_train_median.csv"

TIMEPOINT_LABELS = {
    "preop": "preop",
    "3 months after surgery": "3m",
    "6 months after surgery": "6m",
    "9 months after surgery": "9m",
    "12 months after surgery": "12m",
}

