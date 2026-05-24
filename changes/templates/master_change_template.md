<!--
{{
  "master_id": "{MASTER_ID}",
  "title": "{TITLE}",
  "status": "{STATUS}",
  "started": "{STARTED}",
  "completed": "{COMPLETED}",
  "version": "{VERSION}",
  "owner": "{OWNER}",
  "tags": [{TAGS}],
  "change_runs": [{RUN_IDS}],
  "related_master": {RELATED}
}}
-->

# Master Change — {TITLE}

- **Master ID:** {MASTER_ID}
- **Status:** {STATUS}
- **Owner:** {OWNER}
- **Timeline:** {STARTED} → {COMPLETED}
- **Tags:** {TAGS_HUMAN}
- **Version:** {VERSION}
- **Related Master:** {RELATED_HUMAN}

## Overview

Describe the narrative for this change. What problem did it solve? How does it connect to manifests, automation, or product goals?

## High-Level Change Summary

| Item | Details |
| --- | --- |
| Intent | {INTENT} |
| Fit & impact | {FIT} |
| Tests/validation | {VALIDATION_PLAN} |
| Risks & mitigations | {RISKS} |

**Commentary:** _Capture any high-level thoughts before drilling into runs._

## Change Runs

> Document each run chronologically. Duplicate the following block per run.

### Change Run {RUN_EXAMPLE_ID} — {RUN_EXAMPLE_TITLE}
- **When:** {RUN_EXAMPLE_TIME}
- **Files touched:** _e.g., `scripts/release_pipeline.py`, `docs/README.md`_
- **Reason:** _Why was this run necessary?_
- **How it fits:** _Explain how this run supports the master change._
- **Validation:** _Commands/tests executed here._
- **Tags:** _Subset of tag list relevant to this run._

**Commentary:** _First-person reflection ("I started with ...")._

---

_Add as many change run sections as needed._

## Validation & Outcomes

- Tests/commands executed after all runs
- Integrity / release steps
- Observed impact on manifests, telemetry, or automation

**Commentary:** _Summarize confidence and next steps. Mention if this master change is part of a larger initiative._
