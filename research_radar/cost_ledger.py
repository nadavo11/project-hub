"""Aggregate only the explicitly identified pilot and real acceptance campaigns."""

import json

from .core import ROOT, Store, now


def main():
    pilot = ROOT / "pilot"
    published = json.loads((pilot / "published-campaign.json").read_text())
    journey_path = pilot / "live-ui-journey.json"
    journey = json.loads(journey_path.read_text()) if journey_path.exists() else {}
    ids = [published["campaign_id"], "campaign-b9637d19b9c4"]
    live = journey.get("campaign_id")
    if live:
        ids.append(live)
    store = Store()
    campaigns = []
    for campaign_id in dict.fromkeys(ids):
        state = store.state(campaign_id)
        campaigns.append({
            "id": campaign_id, "name": store.campaign(campaign_id)["name"],
            "costs": state["costs"],
            "cli_process_starts": sum(event["kind"] == "agent_start" for event in state["events"]),
            "usage_receipts": sum(event["kind"] == "cost" and isinstance(event["data"].get("usage"), dict) for event in state["events"]),
        })
    result = {
        "at": now(), "campaigns": campaigns,
        "public_request_operations": sum(c["costs"]["http_requests"] for c in campaigns),
        "measured_download_bytes_lower_bound": sum(c["costs"]["download_bytes"] for c in campaigns),
        "recorded_work_seconds_partial": sum(c["costs"]["elapsed_seconds"] for c in campaigns),
        "recorded_cli_requests": sum(c["costs"].get("cli_requests") or 0 for c in campaigns),
        "recorded_cli_nano_aiu": sum(c["costs"].get("cli_nano_aiu") or 0 for c in campaigns),
        "recorded_model_input_tokens_including_cache": sum(c["costs"].get("model_input_tokens") or 0 for c in campaigns),
        "recorded_model_output_tokens": sum(c["costs"].get("model_output_tokens") or 0 for c in campaigns),
        "paid_external_api_calls": 0, "gpu_hours": 0, "total_usd": None,
        "limitations": [
            "This is not a complete monetary bill. Coordinating/research/UI agent billing is not exposed here.",
            "Nine operator web-fetch/search operations have known counts but unavailable byte/time measurements; tool-internal redirects are not separately measurable.",
            "Work durations combine separately measured research and runtime intervals, not a single non-overlapping wall-clock campaign duration.",
            "A terminated CLI process may not emit a usage receipt; issued process count and observed receipt count are shown separately.",
            "Software fixture tests use loopback and no public model/API. Their CPU time is in software-validation.json, not this public research ledger.",
        ],
    }
    (pilot / "cost-ledger.json").write_text(json.dumps(result, indent=2))
    print(json.dumps({key: value for key, value in result.items() if key not in {"campaigns", "limitations"}}, indent=2))


if __name__ == "__main__":
    main()
