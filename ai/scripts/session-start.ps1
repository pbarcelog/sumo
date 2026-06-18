# Session start — SUMO GIS API

$branch = git rev-parse --abbrev-ref HEAD 2>$null
if (-not $branch) { $branch = "(not a git repo)" }

Write-Host "=== SUMO GIS API ==="
Write-Host "Branch: $branch"
Write-Host ""

# Current focus from specs/coverage.md (light table parse)
$coveragePath = "specs/coverage.md"
if (Test-Path $coveragePath) {
    $focus = @{}
    $inFocus = $false
    foreach ($line in Get-Content $coveragePath -Encoding UTF8) {
        if ($line -match '^## Current focus') { $inFocus = $true; continue }
        if ($inFocus -and $line -match '^---') { break }
        if ($inFocus -and $line -match '^\|\s*\*\*([^*]+)\*\*\s*\|\s*(.+?)\s*\|') {
            $focus[$Matches[1].Trim()] = $Matches[2].Trim()
        }
    }
    if ($focus.Count -gt 0) {
        Write-Host "Focus (specs/coverage.md):"
        foreach ($key in @('Change', 'Next', 'Last completed', 'Blockers')) {
            if ($focus.ContainsKey($key)) {
                Write-Host "  $key`: $($focus[$key])"
            }
        }
        Write-Host ""
    }
}

# Uncommitted spec / AI / OpenSpec changes
$dirty = git status --short -- specs ai openspec 2>$null
if ($dirty) {
    Write-Host "Uncommitted spec/AI/OpenSpec:"
    $dirty | ForEach-Object { Write-Host "  $_" }
    Write-Host ""
}

Write-Host "Specs: specs/coverage.md (focus) | specs/adr-registry.md | specs/prd.md"
Write-Host "OpenSpec: openspec/changes/"
Write-Host ""
Write-Host "Commands: /opsx:* | /sumo-propose | /sumo-apply | /sumo-archive | /check-spec"
Write-Host "Personas: Codebase Analyst | Reconcile Reviewer | SUMO Spec Guard"
