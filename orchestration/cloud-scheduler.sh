#!/usr/bin/env bash
# Cloud Scheduler jobs that switch the Airbyte VM on before the sync and off after it,
# so the VM does not run 24/7.
#
# The scheduler's service account needs the "Compute Instance Admin (v1)" role.
set -euo pipefail

PROJECT_ID="your-project-id"
ZONE="your-zone"                # e.g. asia-southeast1-b
INSTANCE="your-airbyte-vm"
SA_EMAIL="scheduler-sa@${PROJECT_ID}.iam.gserviceaccount.com"
TZ="Asia/Bangkok"
START_CRON="your-start-cron"    # before the Airbyte sync time
STOP_CRON="your-stop-cron"      # after the Airbyte sync has finished
BASE="https://compute.googleapis.com/compute/v1/projects/${PROJECT_ID}/zones/${ZONE}/instances/${INSTANCE}"

# Start VM (Airbyte auto-starts via airbyte.service)
gcloud scheduler jobs create http start-airbyte-vm \
  --schedule="${START_CRON}" --time-zone="${TZ}" \
  --uri="${BASE}/start" --http-method=POST \
  --oauth-service-account-email="${SA_EMAIL}"

# Stop VM
gcloud scheduler jobs create http stop-airbyte-vm \
  --schedule="${STOP_CRON}" --time-zone="${TZ}" \
  --uri="${BASE}/stop" --http-method=POST \
  --oauth-service-account-email="${SA_EMAIL}"
