# C++ Coding Standards — SUMO GIS API Fork

## Canonical upstream (do not duplicate)

| Topic | Location |
|---|---|
| Code style | [docs/web/docs/Developer/CodeStyle.md](../../docs/web/docs/Developer/CodeStyle.md) |
| C++ file template | [docs/web/docs/Developer/CppFileTemplate.md](../../docs/web/docs/Developer/CppFileTemplate.md) |
| Header template | [docs/web/docs/Developer/HFileTemplate.md](../../docs/web/docs/Developer/HFileTemplate.md) |
| Contributing / EPL | [src/README_Contributing.md](../../src/README_Contributing.md) |
| Style check | `tools/build_config/checkStyle.py --fix <file>` |

## Fork delta

New C++ in SUMO core is **out of scope for v1** unless an accepted ADR explicitly approves it.
Prefer Python orchestration in the API layer. If core changes become necessary (e.g. GPKG in netconvert), follow upstream templates and EPL requirements.
