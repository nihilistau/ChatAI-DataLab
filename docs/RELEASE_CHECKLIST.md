# Release Checklist

Use this checklist any time you prepare an internal drop or GitHub release. It codifies the automation already wired into CI plus the integrity tooling that ships with the repo.

## 1. Update metadata

- [ ] Review `CHANGELOG.md` and add an entry that captures user-facing changes.
- [ ] Run `python scripts/project_integrity.py status` and ensure only intentional files are dirty.
- [ ] If new assets or configs were added, run `python scripts/project_integrity.py checkpoint --tag release --reason "vX.Y.Z"` to snapshot them.

## 2. Verify automation locally

```bash
# Backend + notebooks
python -m pip install -r chatai/backend/requirements.txt
python -m pip install -r datalab/requirements.txt
python -m pytest chatai/backend/tests -q
python -m pytest tests/test_notebooks.py -q

# Frontend
cd chatai/frontend
npm install
npm run lint
npm run test
npm run test:playground
npm run build
npm run storybook:build
npm run storybook:playground
```

## 3. Collect artifacts

- [ ] Copy the freshly executed notebooks from `datalab/notebooks/_papermill/` into the release notes (CI also uploads them automatically).
- [ ] Capture screenshots/GIFs of the Playground UI or Storybook stories if visual changes were made.

## 4. Git + GitHub hygiene

- [ ] Ensure the `scripts/git-hooks/pre-push.sh` hook is installed locally (`cp scripts/git-hooks/pre-push.sh .git/hooks/pre-push`).
- [ ] Rebase against `origin/main` and rerun the Full Test Suite if the diff is non-trivial.
- [ ] Tag the release with `git tag -a vX.Y.Z -m "Release notes"` and push via `git push origin main --tags`.

Example for Framework v1.0.0:

```bash
git checkout main
git pull --ff-only
python scripts/project_integrity.py status
git status
git tag -a v1.0.0 -m "Framework v1.0.0"
git push origin main
git push origin v1.0.0
```

Equivalent PowerShell shortcut:

```powershell
pwsh -File scripts/lab-control.ps1 -ReleaseVersion 1.0.0 -ReleasePush
```

## 5. Publish

- [ ] Draft a GitHub release pointing at the new tag. Paste the `CHANGELOG` entry plus any notebook artifacts or screenshots.
- [ ] Mark the release as "Latest" once CI passes.

Following these steps keeps GitHub releases reproducible and aligned with the automation wired into this repository.
