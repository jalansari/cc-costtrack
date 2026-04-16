#!/usr/bin/env python3
"""
Uses the status line cache (written every second by `cc-statusline`) to get
the session's total_cost_usd as reported by Claude Code.
"""

import csv
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

CSV_DIR = os.path.expanduser("~/.claude/cc-costtrack")
CSV_FILE = os.path.join(CSV_DIR, "claude-token-usage.csv")
CACHE_DIR = os.path.join(os.environ.get("TMPDIR", "/tmp"), f"claude_status_cache_{os.getuid()}")

STATUS_CACHE_FILE_SUFFIX = "_cache_stdin.json"

class CostTrackError(Exception):
    def __init__(self, message: str):
        super().__init__(f"cc-costtrack: {message}")

class CostTrackNonFatalError(Exception):
    def __init__(self, message: str):
        super().__init__(f"cc-costtrack (non-terminal): {message}")

class CostTrack:
    def __init__(self, data: dict):
        self.session_id = data.get("session_id", "")
        self.transcript_path = data.get("transcript_path", "")
        self.cwd = data.get("cwd", "")

    def initialize(self):
        self.time_stamp = datetime.now(timezone.utc).isoformat()
        self.__branch()
        self.__cost()
        self.__token_usage()

    def __branch(self):
        self.git_branch = ""
        try:
            self.git_branch = subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                cwd=self.cwd or None, stderr=subprocess.DEVNULL, text=True).strip()
        except Exception:
            # If error, assume we're not in a git repo.  Leave branch blank.
            pass

    def __cost(self):
        self.cost_usd = 0.0
        cache_path = os.path.join(CACHE_DIR, f"{self.session_id}{STATUS_CACHE_FILE_SUFFIX}")
        try:
            with open(cache_path) as fl:
                cache_data = json.load(fl)
            self.cost_usd = cache_data.get("cost", {}).get("total_cost_usd", 0.0)
        except FileNotFoundError:
            raise CostTrackNonFatalError(f"status cache not found: {cache_path}")
        except (json.JSONDecodeError, KeyError) as exc:
            raise CostTrackError(f"failed to parse status cache {cache_path}: {exc}")

    def __token_usage(self):
        self.input_tokens = 0
        self.output_tokens = 0
        self.cache_creation = 0
        self.cache_read = 0
        self.__read_transcript()

    def __read_transcript(self):
        if not self.transcript_path:
            raise CostTrackError("no transcript_path in hook input")
        if not os.path.isfile(self.transcript_path):
            raise CostTrackError(f"transcript not found: {self.transcript_path}")
        with open(self.transcript_path) as fl_transcript:
            for line in fl_transcript:
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    entry = json.loads(stripped)
                    if entry.get("type") == "assistant":
                        usage = entry.get("message", {}).get("usage", {})
                        self.input_tokens += usage.get("input_tokens", 0)
                        self.output_tokens += usage.get("output_tokens", 0)
                        self.cache_creation += usage.get("cache_creation_input_tokens", 0)
                        self.cache_read += usage.get("cache_read_input_tokens", 0)
                except json.JSONDecodeError:
                    continue

CSV_HEADER = ["timestamp", "session_id", "cwd", "git_branch", "input_tokens", "output_tokens",
        "cache_creation_tokens", "cache_read_tokens", "cost_usd"]

def _archive_path(year_month: str) -> str:
    return os.path.join(CSV_DIR, f"claude-token-usage-{year_month}.csv")

def _read_csv_rows(path: str) -> list:
    if not os.path.isfile(path):
        return []
    with open(path, "r", newline="") as fl_r:
        reader = csv.reader(fl_r)
        next(reader, None)
        return list(reader)

def _write_csv_atomic(path: str, rows: list):
    fd, tmp_path = tempfile.mkstemp(dir=CSV_DIR, suffix=".csv")
    try:
        with os.fdopen(fd, "w", newline="") as fl_w:
            writer = csv.writer(fl_w)
            writer.writerow(CSV_HEADER)
            writer.writerows(rows)
        os.replace(tmp_path, path)
    except Exception:
        os.unlink(tmp_path)
        raise

def write_csv(cost_track: CostTrack):
    new_row = [cost_track.time_stamp, cost_track.session_id, cost_track.cwd, cost_track.git_branch,
            cost_track.input_tokens, cost_track.output_tokens, cost_track.cache_creation, cost_track.cache_read,
            f"{cost_track.cost_usd:.4f}"]

    current_month = datetime.now(timezone.utc).strftime("%Y-%m")

    # Read existing rows, filtering out any with the same session_id
    existing_rows = [r for r in _read_csv_rows(CSV_FILE) if r[1] != cost_track.session_id]

    # Partition into current month vs past months
    current_rows = []
    archive_groups = {}
    for row in existing_rows:
        ym = row[0][:7]  # YYYY-MM from ISO timestamp
        if ym == current_month:
            current_rows.append(row)
        else:
            archive_groups.setdefault(ym, []).append(row)

    os.makedirs(CSV_DIR, exist_ok=True)

    # Append past-month rows to their archive files
    for ym, rows in archive_groups.items():
        archive = _archive_path(ym)
        existing_archive = _read_csv_rows(archive)
        archived_ids = {r[1] for r in existing_archive}
        new_archive_rows = [r for r in rows if r[1] not in archived_ids]
        if new_archive_rows:
            _write_csv_atomic(archive, existing_archive + new_archive_rows)

    # Main file keeps only current month + new row
    current_rows.append(new_row)
    _write_csv_atomic(CSV_FILE, current_rows)

def cost_log():
    hook_input = json.load(sys.stdin)
    cost_track = CostTrack(hook_input)
    try:
        cost_track.initialize()
        write_csv(cost_track)
    except CostTrackNonFatalError:
        # Ignore non-fatal errors.
        pass


def main():
    cost_log()

if __name__ == "__main__":
    main()
