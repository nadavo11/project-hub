"""Transparent ordinal judgments, not acceptance probabilities."""

DIMENSIONS = (
    "novelty", "significance", "technical_depth", "experimental_feasibility",
    "evaluation_strength", "venue_fit", "risk_manageability", "time_to_first_evidence",
)


def rank(opportunities, weights):
    results = []
    for idea in opportunities:
        dimensions = idea.get("assessment_dimensions", {})
        active = [key for key in DIMENSIONS if weights.get(key, 1) > 0]
        missing = [key for key in active if not isinstance(dimensions.get(key), dict)
                   or type(dimensions[key].get("score")) is not int
                   or not 0 <= dimensions[key]["score"] <= 4 or not dimensions[key].get("reason")]
        score = None
        if active and not missing:
            score = round(sum(weights.get(k, 1) * dimensions[k]["score"] for k in active)
                          / sum(weights.get(k, 1) for k in active), 2)
        results.append({"opportunity_id": idea["id"], "score": score, "scale": "0-4 ordinal judgment",
                        "missing": missing, "dimensions": dimensions, "weights": weights,
                        "interpretation": "Subjective prioritization only; not a calibrated probability or evidence of novelty"})
    return sorted(results, key=lambda row: (row["score"] is None, -(row["score"] or 0)))
