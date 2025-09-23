#!/bin/bash

set -e  # Exit immediately if a command exits with a non-zero status
set -x  # Print each command before executing it

# Parse command line arguments
APP_NAME="dspy-forge"  # Default app name
DATABRICKS_CONFIG_PROFILE=""  # Will be set if --profile is specified

while [[ $# -gt 0 ]]; do
  case $1 in
    --app)
      APP_NAME="$2"
      shift 2
      ;;
    --profile)
      DATABRICKS_CONFIG_PROFILE="$2"
      shift 2
      ;;
    *)
      echo "Unknown option: $1"
      echo "Usage: $0 [--app APP_NAME] [--profile PROFILE_NAME]"
      exit 1
      ;;
  esac
done

# Only export DATABRICKS_CONFIG_PROFILE if it was specified
if [[ -n "$DATABRICKS_CONFIG_PROFILE" ]]; then
  export DATABRICKS_CONFIG_PROFILE
fi

DATABRICKS_USERNAME=$(databricks current-user me | jq -r .userName)
APP_FOLDER_IN_WORKSPACE="/Workspace/Users/${DATABRICKS_USERNAME}/${APP_NAME}"

# UI build and import.
(
  cd "ui"
  npm install
  npm run build
  cd ".."
)

# Backend packaging. Swap in your /backend folder name if it's different here.
(
  databricks sync . "$APP_FOLDER_IN_WORKSPACE"
) &

# Wait for both background processes to finish
wait

# Check if app exists, create if it doesn't
echo "Checking if app '$APP_NAME' exists..."
if ! databricks apps get "$APP_NAME" &>/dev/null; then
  echo "App '$APP_NAME' does not exist. Creating it..."
  databricks apps create "$APP_NAME"
  echo "App '$APP_NAME' created successfully."
else
  echo "App '$APP_NAME' already exists."
fi

# Deploy the application
databricks apps deploy "$APP_NAME" --source-code-path "$APP_FOLDER_IN_WORKSPACE"
