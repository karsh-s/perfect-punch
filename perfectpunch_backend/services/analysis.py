from typing import Dict

class AnalysisService:
    """Simple analysis service that produces a friendly report from metrics.

    Replace with more advanced injury-risk algorithms and Taipy dashboard integration.
    """

    def generate_report(self, session_id: str, metrics: Dict[str, float]):
        # Basic heuristics for demonstration
        score = 0.0
        reasons = []
        if not metrics:
            reasons.append("No metrics provided; unable to analyze.")
        else:
            score = float(metrics.get("accuracy", 0.0)) * 100
            if metrics.get("impact_g", 0) > 80:
                reasons.append("High impact detected — elevated concussion risk.")
            if metrics.get("elbow_angle_deviation", 0) > 15:
                reasons.append("Elbow form deviation — fix technique to avoid strain.")
        return {"summary_score": score, "issues": reasons, "raw": metrics}
