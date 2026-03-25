#!/usr/bin/env bash
# setup_weekly_clean_unix.sh
# Adds a weekly cron job that runs 'cull' on your dev folder.
# Tested on macOS and Linux.
#
# Usage:
#   ./setup_weekly_clean_unix.sh [path] [older-than-days] [min-size-mb]
#
# Defaults: $HOME/projects, 90 days, no size filter.

set -e

SCAN_PATH="${1:-$HOME/projects}"
OLDER_THAN="${2:-90}"
MIN_SIZE="${3:-0}"

CULL=$(command -v cull 2>/dev/null || true)
if [ -z "$CULL" ]; then
    echo "cull not found. Run: pip install devcull" >&2
    exit 1
fi

ARGS="--older-than $OLDER_THAN"
[ "$MIN_SIZE" -gt 0 ] && ARGS="$ARGS --min-size $MIN_SIZE"
ARGS="$ARGS --delete $SCAN_PATH"

# Sunday at 9am
CRON_LINE="0 9 * * 0 $CULL $ARGS >> $HOME/.cull.log 2>&1"

# add only if not already there
( crontab -l 2>/dev/null | grep -vF "devcull"; echo "$CRON_LINE" ) | crontab -

echo "Cron job added: cull runs every Sunday at 9am on $SCAN_PATH"
echo "Logs: $HOME/.cull.log"
echo "To remove: crontab -e (delete the cull line)"
