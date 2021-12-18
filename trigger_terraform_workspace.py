import json
import os
import urllib3


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

    encoded_data = json.dumps(payload).encode("utf-8")

    http = urllib3.PoolManager()

    r = http.request(
        "POST",
        "https://app.terraform.io/api/v2/runs",
        body=encoded_data,
        headers={
            "Authorization": "Bearer " + os.getenv("TF_CLOUD_TOKEN"),
            "Content-Type": "application/vnd.api+json",
        },
    )

    print(r.data)


if __name__ == "__main__":
    trigger_terraform(
        os.getenv("IS_DESTROY"),
        f"Trigger from script, destroy = {os.getenv('IS_DESTROY')}",
    )
