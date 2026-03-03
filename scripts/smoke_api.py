"""Operational script for smoke api.
Provides command-line helpers for local setup, security, or smoke-validation workflows.
"""
import json
import time

import httpx

BASE_URL = "http://127.0.0.1:8000"


def wait_for_health() -> None:
    """Execute the wait for health workflow. This function is part of the module-level runtime flow."""
    for _ in range(60):
        try:
            res = httpx.get(f"{BASE_URL}/health", timeout=2)
            if res.status_code == 200:
                return
        except Exception:
            pass
        time.sleep(1)
    raise RuntimeError("API health check did not become ready")


def main() -> None:
    """Execute the main workflow. This function is part of the module-level runtime flow."""
    wait_for_health()

    with httpx.Client(timeout=30.0) as client:
        login = client.post(
            f"{BASE_URL}/auth/login",
            json={"email": "demo@launchpad.ai", "password": "demo1234"},
        )
        login.raise_for_status()
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        campaigns = client.get(f"{BASE_URL}/campaigns", headers=headers)
        campaigns.raise_for_status()
        campaign_id = campaigns.json()[0]["id"]

        result = {
            "health": client.get(f"{BASE_URL}/health").status_code,
            "generate": client.post(f"{BASE_URL}/campaigns/{campaign_id}/generate-variants", headers=headers).status_code,
            "simulate": client.post(f"{BASE_URL}/campaigns/{campaign_id}/simulate-batch", headers=headers).status_code,
            "propose": client.post(f"{BASE_URL}/campaigns/{campaign_id}/propose-improvements", headers=headers).status_code,
        }

        recs = client.get(f"{BASE_URL}/campaigns/{campaign_id}/recommendations", headers=headers)
        recs.raise_for_status()
        rec_list = recs.json()
        result["recommendations"] = len(rec_list)

        if rec_list:
            rid = rec_list[0]["id"]
            result["approve"] = client.post(f"{BASE_URL}/recommendations/{rid}/approve", headers=headers).status_code
            result["apply"] = client.post(f"{BASE_URL}/recommendations/{rid}/apply", headers=headers).status_code

        trace = client.get(f"{BASE_URL}/campaigns/{campaign_id}/lift-trace", headers=headers)
        trace.raise_for_status()
        result["lift_trace_events"] = len(trace.json())

        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
