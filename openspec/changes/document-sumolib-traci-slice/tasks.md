# Tasks — document-sumolib-traci-slice

## 1. Documentation

- [x] 1.1 Extend ADR-006 with sumolib API surface (binary, options, net, xml, files, shapes, geomhelper)
- [x] 1.2 Extend ADR-006 with TraCI vs Libsumo section and mermaid diagrams
- [x] 1.3 Update `specs/interfaces.md` with sumolib/TraCI rows and simulation sequences
- [x] 1.4 Update glossary (Libsumo, Libtraci, checkBinary, .sumocfg)
- [x] 1.5 Update `specs/coverage.md` slice 6 → Draft; focus → slice 7
- [x] 1.6 Write OpenSpec capability spec (`sumolib-traci-integration`)

## 2. Validation

- [x] 2.1 Cross-check ADR-006 against `tools/sumolib/__init__.py`, `options.py`, `net/__init__.py`, `traci/main.py`
- [x] 2.2 Verify osmBuild/osmWebWizard do not use TraCI (grep)
- [ ] 2.3 Run `openspec validate document-sumolib-traci-slice` (when CLI available)

## 3. Archive prep

- [ ] 3.1 Review with Pablo (open questions for Tier B)
- [ ] 3.2 `/opsx:archive document-sumolib-traci-slice` when approved
