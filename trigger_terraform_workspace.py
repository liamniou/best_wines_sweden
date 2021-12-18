import json
import httpx
import os


def trigger_terraform(is_destroy, run_title):
    payload = {
        "data": {
            "attributes": {"is-destroy": is_destroy, "message": run_title},
            "type": "runs",
            "relationships": {
                "workspace": {
                    "data": {"type": "workspaces", "id": os.getenv("WORKSPACE_ID")}
                }
            },
        }
    }

    with httpx.Client() as client:
        headers = {
            "Authorization": "Bearer " + os.getenv("TF_CLOUD_TOKEN"),
            "Content-Type": "application/vnd.api+json",
        }
        r = client.post(
            "https://app.terraform.io/api/v2/runs", headers=headers, json=payload
        )
        print(r)


if __name__ == "__main__":
    trigger_terraform(
        os.getenv("IS_DESTROY"),
        f"Trigger from script, destroy = {os.getenv('IS_DESTROY')}",
    )
