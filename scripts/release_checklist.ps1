param(
    [switch]$SkipFrontend,
    [switch]$SkipBackend,
    [switch]$SkipNotebooks,
    [switch]$SkipTelemetry
)

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$repoRoot = Resolve-Path (Join-Path $root "..")
Push-Location $repoRoot
try {
    $needsNotebookDeps = (-not $SkipTelemetry) -or (-not $SkipNotebooks)

    if (-not $SkipBackend) {
        Write-Host "[release] Running backend tests" -ForegroundColor Cyan
        pip install -r playground/backend/requirements.txt
        pytest playground/backend/tests -q
    }

    if ($needsNotebookDeps) {
        Write-Host "[release] Installing Kitchen notebook dependencies" -ForegroundColor Cyan
        pip install -r kitchen/requirements.txt
    }

    if (-not $SkipTelemetry) {
        Write-Host "[release] Hydrating search telemetry ledger" -ForegroundColor Cyan
        python -m scripts.search_telemetry ingest --log-path logs/search-history.jsonl --output data/search_telemetry.json `
            --runs-parquet data/search_telemetry-runs.parquet `
            --daily-parquet data/search_telemetry-daily.parquet
        if ($LASTEXITCODE -ne 0) {
            throw "Search telemetry ingestion failed with exit code $LASTEXITCODE"
        }

        $papermillOutputDir = "kitchen/notebooks/_papermill"
        if (-not (Test-Path $papermillOutputDir)) {
            New-Item -ItemType Directory -Path $papermillOutputDir -Force | Out-Null
        }
        $timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
        $outputNotebook = Join-Path $papermillOutputDir "search_telemetry-release-$timestamp.ipynb"

        Write-Host "[release] Running Papermill snapshot -> $outputNotebook" -ForegroundColor Cyan
        python -m papermill `
            kitchen/notebooks/search_telemetry.ipynb `
            $outputNotebook `
            -p SEARCH_LEDGER_PATH data/search_telemetry.json `
            -p TELEMETRY_LOG_PATH logs/search-history.jsonl
        if ($LASTEXITCODE -ne 0) {
            throw "Papermill search_telemetry notebook failed with exit code $LASTEXITCODE"
        }
    }

    if (-not $SkipNotebooks) {
        Write-Host "[release] Running notebook tests" -ForegroundColor Cyan
        pytest tests/test_notebooks.py -q
    }
    if (-not $SkipFrontend) {
        Write-Host "[release] Running frontend checks" -ForegroundColor Cyan
        Push-Location playground/frontend
        try {
            npm install
            npm run lint
            npm run test
            npm run test:playground
            npm run build
            npm run storybook:build
            npm run storybook:playground
        } finally { Pop-Location }
    }
}
finally {
    Pop-Location
}
