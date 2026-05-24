# Change History System

The `/changes` workspace is a lightweight archive of every high-level modification ("Master Change") and the smaller steps ("Change Runs") that make it real. Each record is a Markdown report with structured metadata, conversational commentary, and traceable tags so ops, reviewers, and future agents can answer:

- What changed, why, and how does it support the roadmap?
- Which files were touched and how does it affect releases, tests, or automation?
- Which incremental runs produced the final outcome, and what validation protected it?

## Scope & separation

- **Reporting-only surface:** This framework is an auxiliary log for agents and operators to narrate work. It does _not_ replace Git history, release automation, or integrity tooling.
- **Agent-populated:** Prefer agents (like Copilot) to author/maintain entries when users request summaries. Humans can browse, but no other automation depends on the data.
- **No gating:** Pipelines, tests, and manifests continue to rely on the existing systems. `/changes` lives beside them purely as a storytelling aid.
- **Safe to ignore:** If you never touch this directory, nothing else breaks. When you do need a report, the template + CLI keep the format consistent without coupling to other workflows.

## Key concepts

| Term | Definition |
| --- | --- |
| **Master Change** | A complete unit of intent (e.g., "Release pipeline notes support") that may require multiple coding sessions. Stored as `changes/records/MC-*.md`. |
| **Change Run** | An ordered slice of work ("Update docs", "Add CLI flag") that rolls up into a master change. Runs are documented inside the parent record so readers can replay the sequence end-to-end. |
| **Tags** | Controlled vocabulary that marks the scope of each change (`release`, `docs`, `testing`, `integrity`, `new-feature`, `fix`, `tooling`, `workshop`, `frontend`, `backend`, `ops`, `infra`). Add more as needed, but keep them short and lowercase. |
| **Change Database** | The collection of Master Change files plus the helper CLI (`scripts/change_runs.py`) that can list, show, and scaffold records. |

## File layout

```
changes/
├─ README.md                         # This guide
├─ templates/
│  └─ master_change_template.md      # Fill-in-the-blanks outline for new records
└─ records/
   └─ MC-YYYY-MM-DD-xxx.md           # Individual master change reports
```

Each record begins with a JSON metadata block stored in an HTML comment so it stays human-friendly while remaining machine-parseable:

```
<!--
{
  "master_id": "MC-2025-11-20-001",
  "title": "Release pipeline notes support",
  "status": "complete",
  "started": "2025-11-20T10:05:00Z",
  "completed": "2025-11-20T12:15:00Z",
  "version": "1.0",
  "owner": "copilot",
  "tags": ["release", "docs", "tooling"],
  "change_runs": ["CR-2025-11-20-001", "CR-2025-11-20-002"],
  "related_master": null
}
-->
```

The body then follows the template sections:

1. **Overview & Reasoning** – conversational narrative, rationale, fit.
2. **High-Level Change Summary** – bullet list of goals, risks, validations.
3. **Change Run sections** – one per run with timestamps, file lists, reasons, validation, and commentary.
4. **Validation & Outcomes** – commands/tests run with results.
5. **Commentary** – first-person wrap-up to maintain the conversational history the user requested.

## CLI usage (`scripts/change_runs.py`)

| Command | Purpose |
| --- | --- |
| `python scripts/change_runs.py list` | Scan `changes/records/*.md` and print master id, title, status, tags, and completion date for quick triage. |
| `python scripts/change_runs.py show MC-2025-11-20-001` | Render the metadata + summarized runs for a specific record (outputs to stdout for reporting or pipelines). |
| `python scripts/change_runs.py new --title "..." --tags "release,docs" [--master-id ...] [--owner ...] [--runs cr1,cr2]` | Materialize `records/<master-id>.md` from the template with fields pre-filled so the author can focus on prose/details. |

All commands support `--records-dir` and `--template` overrides when scripting outside the repo root.

## PowerShell heredoc workaround for inline helpers

Agents frequently need one-off Python snippets (for example, mass search/replace across tracked files) while narrating a Change Run. PowerShell rejects the typical Unix-style heredoc syntax (`python - <<'PY' ...`) because the `<<` redirection operator expects a file path. The reliable pattern in this workspace is:

1. Capture the Python (or shell) snippet inside a PowerShell here-string.
2. Write it to a temporary file with `Set-Content`.
3. Execute the interpreter against that file.
4. Remove the temporary file afterwards.

Example:

```
$script = @'
from pathlib import Path
root = Path("release_artifacts/v1.0.3-control-capsules.20251118/notebooks")
for nb in root.glob('*.ipynb'):
   text = nb.read_text()
   updated = text.replace("kitchen.", "workshop.")
   if updated != text:
      nb.write_text(updated)
      print(f"updated {nb}")
'@
Set-Content -Path __tmp_script.py -Value $script
python __tmp_script.py
Remove-Item __tmp_script.py
```

Whenever you see prior runs referencing “heredoc workaround,” reuse this pattern. It keeps inline tooling ergonomic in PowerShell while staying cross-agent friendly (any Copilot/agent can rerun the exact sequence without rewriting commands).

## Workflow

1. **Plan** – Pick a master id (`MC-YYYY-MM-DD-###`) and optionally pre-plan run ids (`CR-...`).
2. **Scaffold** – Run the `new` command (or copy the template) to create a file under `changes/records/`.
3. **Document runs** – After each meaningful coding session, add a "Change Run" section with:
   - Summary + purpose
   - Files touched / commands executed
   - Tests/validation notes
   - Commentary on what happened, blockers, next step
4. **Close out** – Update the metadata `status`, `completed`, `version`, and `change_runs` list. Add a final commentary paragraph capturing assurance steps (tests, integrity, release commands, etc.).
5. **Reference** – Link the master change id inside PR descriptions, commit messages, or release entries so stakeholders can look up the detailed report.

## Automation assist: workflow harness logs

When you need to pair a Master Change entry with the guardrails (release dry-run, goals log stamp, rebrand rehearsal, integrity checkpoint), the `Ops workflow harness` command is the fastest path:

- `python scripts/workflow_harness.py --notes "Ops workflow harness" --goal-milestone "<milestone>" --goal-summary "<summary>" --goal-artifacts "`scripts/workflow_harness.py`" --change-title "<title>" --change-master-id MC-YYYY-MM-DD-### --timeline-json data/logs/workflow_harness/latest.json --timeline-jsonl data/logs/workflow_harness/history.jsonl`

The new timeline flags emit a machine-readable record of every step, so you can paste the JSON straight into a change run section, attach it to Ops Deck diagnostics, or feed it into MCP tooling without reinventing parsers. `latest.json` overwrites on each run (great for quick inspection) while `history.jsonl` appends a durable log line per run. Both paths live under `data/logs/workflow_harness/` so they remain inside the tracked data tree.

Each run also emits a tail log entry (source `workflow-harness` by default) and appends a JSON object to `data/logs/release.log`, so the Ops Deck and telemetry notebooks inherit the same context without extra plumbing. Use `--tail-log-message`/`--tail-log-source` for custom phrasing, or `--skip-tail-log` / `--skip-release-log` if you are experimenting locally and want to keep the logs clean.

## Viewing the database

- **Quick index**: `python scripts/change_runs.py list`
- **Single report**: `python scripts/change_runs.py show <master-id> > report.md`
- **Human browsing**: open the Markdown files in VS Code or render them through any Markdown viewer; the conversational sections are intentionally narrative.

## Versioning & grouping

- **Master Change ID** – unique handle for the complete change (“MC-2025-11-20-001”).
- **Change Run IDs** – monotonically increasing per Master Change ("CR-2025-11-20-001A") or globally unique if you prefer. The template suggests RFC-3339 + suffix but you can adapt.
- **Master Change Series** – link related work by setting `related_master` in the metadata; the CLI surfaces this relation when listing/showing records so multi-step epics stay connected.

Keeping this system up-to-date turns every medium or large change into a replayable story with explicit tests, impact, and rationale—exactly the reporting trail requested in the prompt.
