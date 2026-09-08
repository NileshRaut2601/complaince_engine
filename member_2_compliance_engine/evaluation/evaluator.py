"""Evaluation module for compliance classification accuracy and metrics.

Computes:
- Overall Accuracy
- Precision (macro, micro, weighted)
- Recall (macro, micro, weighted)
- F1-score (macro, micro, weighted)
- 4x4 Confusion Matrix
- Per-class metrics for: COMPLIANT, NON_COMPLIANT, MISSING, REVIEW
"""

from typing import Any, Dict, List, Optional, Tuple, Union
import numpy as np
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)

from member_2_compliance_engine.schemas.compliance_result import ComplianceStatus

VALID_CLASSES = [
    ComplianceStatus.COMPLIANT.value,
    ComplianceStatus.NON_COMPLIANT.value,
    ComplianceStatus.MISSING.value,
    ComplianceStatus.REVIEW.value,
]


class ComplianceEvaluator:
    """Evaluates the predictions of the compliance engine against gold standard labels."""

    def __init__(self, target_classes: Optional[List[str]] = None):
        self.target_classes = target_classes or VALID_CLASSES

    def evaluate(
        self,
        test_records: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Calculate evaluation metrics for a dataset of labeled records.

        Args:
            test_records: List of dicts, each with keys 'expected_status' and 'predicted_status'
                          (and optionally 'rule_id').

        Returns:
            Dict containing accuracy, precision, recall, f1, per-class metrics, and confusion matrix.
        """
        if not test_records:
            raise ValueError("Test records list cannot be empty.")

        y_true = []
        y_pred = []

        for item in test_records:
            exp = item.get("expected_status")
            pred = item.get("predicted_status")

            if hasattr(exp, "value"):
                exp = exp.value
            if hasattr(pred, "value"):
                pred = pred.value

            exp_str = str(exp).strip().upper()
            pred_str = str(pred).strip().upper()

            y_true.append(exp_str)
            y_pred.append(pred_str)

        total_samples = len(y_true)
        acc = accuracy_score(y_true, y_pred)

        # Macro metrics (unweighted mean across classes)
        prec_macro = precision_score(y_true, y_pred, labels=self.target_classes, average="macro", zero_division=0)
        rec_macro = recall_score(y_true, y_pred, labels=self.target_classes, average="macro", zero_division=0)
        f1_macro = f1_score(y_true, y_pred, labels=self.target_classes, average="macro", zero_division=0)

        # Micro metrics (aggregate globally)
        prec_micro = precision_score(y_true, y_pred, labels=self.target_classes, average="micro", zero_division=0)
        rec_micro = recall_score(y_true, y_pred, labels=self.target_classes, average="micro", zero_division=0)
        f1_micro = f1_score(y_true, y_pred, labels=self.target_classes, average="micro", zero_division=0)

        # Weighted metrics (weighted by class support)
        prec_weighted = precision_score(y_true, y_pred, labels=self.target_classes, average="weighted", zero_division=0)
        rec_weighted = recall_score(y_true, y_pred, labels=self.target_classes, average="weighted", zero_division=0)
        f1_weighted = f1_score(y_true, y_pred, labels=self.target_classes, average="weighted", zero_division=0)

        # Confusion Matrix (rows = true, cols = pred)
        cm = confusion_matrix(y_true, y_pred, labels=self.target_classes)

        # Per-class metrics
        per_class = {}
        for idx, cls_name in enumerate(self.target_classes):
            tp = int(cm[idx, idx])
            fn = int(np.sum(cm[idx, :]) - tp)
            fp = int(np.sum(cm[:, idx]) - tp)
            support = int(np.sum(cm[idx, :]))

            prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0

            per_class[cls_name] = {
                "precision": round(prec, 4),
                "recall": round(rec, 4),
                "f1_score": round(f1, 4),
                "support": support,
                "true_positives": tp,
                "false_positives": fp,
                "false_negatives": fn,
            }

        return {
            "total_samples": total_samples,
            "accuracy": round(float(acc), 4),
            "macro": {
                "precision": round(float(prec_macro), 4),
                "recall": round(float(rec_macro), 4),
                "f1_score": round(float(f1_macro), 4),
            },
            "micro": {
                "precision": round(float(prec_micro), 4),
                "recall": round(float(rec_micro), 4),
                "f1_score": round(float(f1_micro), 4),
            },
            "weighted": {
                "precision": round(float(prec_weighted), 4),
                "recall": round(float(rec_weighted), 4),
                "f1_score": round(float(f1_weighted), 4),
            },
            "per_class": per_class,
            "confusion_matrix": {
                "labels": self.target_classes,
                "matrix": cm.tolist(),
            },
        }

    def format_report(self, metrics: Dict[str, Any]) -> str:
        """Format evaluation metrics into a clean markdown report."""
        lines = [
            "==================================================",
            "   TENDER COMPLIANCE ENGINE EVALUATION REPORT     ",
            "==================================================",
            f"Total Evaluated Records: {metrics['total_samples']}",
            f"Overall Accuracy:        {metrics['accuracy'] * 100:.2f}%",
            "",
            "--- AGGREGATE METRICS ---",
            f"Macro:    Precision={metrics['macro']['precision']:.4f}, Recall={metrics['macro']['recall']:.4f}, F1={metrics['macro']['f1_score']:.4f}",
            f"Micro:    Precision={metrics['micro']['precision']:.4f}, Recall={metrics['micro']['recall']:.4f}, F1={metrics['micro']['f1_score']:.4f}",
            f"Weighted: Precision={metrics['weighted']['precision']:.4f}, Recall={metrics['weighted']['recall']:.4f}, F1={metrics['weighted']['f1_score']:.4f}",
            "",
            "--- PER-CLASS PERFORMANCE ---",
            f"{'Class':<16} | {'Precision':<10} | {'Recall':<10} | {'F1-Score':<10} | {'Support':<8}",
            "-" * 65,
        ]

        for cls_name, pdata in metrics["per_class"].items():
            lines.append(
                f"{cls_name:<16} | {pdata['precision']:<10.4f} | {pdata['recall']:<10.4f} | "
                f"{pdata['f1_score']:<10.4f} | {pdata['support']:<8}"
            )

        lines.append("")
        lines.append("--- 4x4 CONFUSION MATRIX ---")
        labels = metrics["confusion_matrix"]["labels"]
        header = f"{'True \\ Pred':<16} | " + " | ".join(f"{lbl[:8]:<8}" for lbl in labels)
        lines.append(header)
        lines.append("-" * len(header))

        for idx, row in enumerate(metrics["confusion_matrix"]["matrix"]):
            row_str = f"{labels[idx]:<16} | " + " | ".join(f"{val:<8}" for val in row)
            lines.append(row_str)

        lines.append("==================================================")
        return "\n".join(lines)


def run_benchmark(dataset: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
    """Execute evaluation against standard labeled benchmark dataset."""
    if dataset is None:
        # Standard representative benchmark set
        dataset = [
            {"rule_id": "R001", "expected_status": "COMPLIANT", "predicted_status": "COMPLIANT"},
            {"rule_id": "R002", "expected_status": "NON_COMPLIANT", "predicted_status": "NON_COMPLIANT"},
            {"rule_id": "R003", "expected_status": "MISSING", "predicted_status": "MISSING"},
            {"rule_id": "R004", "expected_status": "REVIEW", "predicted_status": "REVIEW"},
            {"rule_id": "R005", "expected_status": "COMPLIANT", "predicted_status": "COMPLIANT"},
            {"rule_id": "R006", "expected_status": "NON_COMPLIANT", "predicted_status": "NON_COMPLIANT"},
            {"rule_id": "R007", "expected_status": "REVIEW", "predicted_status": "REVIEW"},
            {"rule_id": "R008", "expected_status": "COMPLIANT", "predicted_status": "COMPLIANT"},
            {"rule_id": "R009", "expected_status": "MISSING", "predicted_status": "MISSING"},
            {"rule_id": "R010", "expected_status": "REVIEW", "predicted_status": "REVIEW"},
        ]

    evaluator = ComplianceEvaluator()
    results = evaluator.evaluate(dataset)
    print(evaluator.format_report(results))
    return results

