# Design — document-orchestration-slice

## osmBuild pattern (as-built)

```mermaid
flowchart TD
  Start[ParseArgs] --> Validate[ValidateInputs]
  Validate --> NCfg[BuildNetconvertOpts]
  NCfg --> SaveNC[SaveNetccfg]
  SaveNC --> RunNC[RunNetconvert]
  RunNC --> CheckTM{TypemapSet?}
  CheckTM -->|yes| PCfg[BuildPolyconvertOpts]
  PCfg --> SavePC[SavePolycfg]
  SavePC --> RunPC[RunPolyconvert]
  CheckTM -->|no| Done[ArtifactsReady]
  RunPC --> Done
```

### Key implementation details

| Concern | osmBuild approach |
|---|---|
| Binary resolution | `sumolib.checkBinary('netconvert', bindir)` |
| Options | Comma-split defaults + CLI overrides |
| Reproducibility | `--save-configuration` → `.netccfg` / `.polycfg` |
| Working directory | `subprocess.call(..., cwd=output_directory)` |
| Relative paths | `getRelative(dirname, option)` |
| Early failure | typemap file check before long netconvert run |

Source: [`tools/osmBuild.py`](../../../tools/osmBuild.py)

## Target API pipeline (MVP)

Extends osmBuild with normalization and demand:

```mermaid
flowchart TD
  Ingest[API_Ingest] --> Norm[GIS_Normalize_ADR011]
  Norm --> NC[netconvert]
  NC --> Net[net.xml]
  Norm --> PC[polyconvert]
  PC --> Poly[poly.xml]
  Ingest --> OMX[OMX_Adapter_ADR012]
  OMX --> TazRel[tazRelation.xml]
  Norm --> TAZ[TAZ_Derive_ADR014]
  TAZ --> Tazs[tazs.xml]
  TazRel --> OD[od2trips]
  Tazs --> OD
  Net --> OD
  OD --> Trips[trips.xml]
  Trips --> DR[duarouter]
  Net --> DR
  DR --> Routes[routes.xml]
  Routes --> SIM[sumo_ADR015]
```

## Design decisions (documented, not implemented here)

1. **Reuse subprocess + sumocfg pattern** — do not embed libsumo in v1 (ADR-015).
2. **Config files per step** — each binary invocation saves configuration for audit trail.
3. **Job status** — API tracks step completion (netconvert → polyconvert → omx → od2trips → duarouter → sumo).
4. **osmWebWizard** — reference for full scenario (demand + GUI) but not MVP API template.

## Non-goals

- Implementing HTTP API (ADR-008)
- OMX adapter code (ADR-012)
- Modifying osmBuild.py
