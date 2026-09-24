#!/usr/bin/env bash
# Cloud Scheduler jobs that switch the Airbyte VM on before the sync and off after it.
# The VM only runs ~40 min/week instead of 24/7.
#
# The scheduler's service account needs the "Compute Instance Admin (v1)" role.
set -euo pipefail

PROJECT_ID="your-project-id"
ZONE="your-zone"                # e.g. asia-southeast1-b
INSTANCE="your-airbyte-vm"
SA_EMAIL="scheduler-sa@${PROJECT_ID}.iam.gserviceaccount.com"
TZ="Asia/Bangkok"
BASE="https://compute.googleapis.com/compute/v1/projects/${PROJECT_ID}/zones/${ZONE}/instances/${INSTANCE}"

# Sunday 11:50 - start VM (Airbyte auto-starts via airbyte.service)
gcloud scheduler jobs create http start-airbyte-vm \
  --schedule="50 11 * * 0" --time-zone="${TZ}" \
  --uri="${BASE}/start" --http-method=POST \
  --oauth-service-account-email="${SA_EMAIL}"

# Sunday 12:30 - stop VM (Airbyte sync scheduled at 12:00 inside Airbyte)
gcloud scheduler jobs create http stop-airbyte-vm \
  --schedule="30 12 * * 0" --time-zone="${TZ}" \
  --uri="${BASE}/stop" --http-method=POST \
  --oauth-service-account-email="${SA_EMAIL}"
