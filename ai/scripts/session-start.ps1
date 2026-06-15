# Session start — SUMO GIS API

$branch = git rev-parse --abbrev-ref HEAD 2>$null
if (-not $branch) { $branch = "(not a git repo)" }

Write-Host "=== SUMO GIS API ==="
Write-Host "Branch: $branch"
Write-Host ""
Write-Host "Specs: specs/coverage.md (focus) | specs/adr-registry.md | specs/prd.md"
Write-Host "OpenSpec: openspec/changes/"
Write-Host ""
Write-Host "Commands: /opsx:* | /sumo-propose | /sumo-apply | /sumo-archive | /check-spec"
Write-Host "Personas: Codebase Analyst | Reconcile Reviewer | SUMO Spec Guard"
