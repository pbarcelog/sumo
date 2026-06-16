# Design — document-sumolib-traci-slice

## sumolib layers (orchestrator-facing)

```mermaid
flowchart TB
  subgraph init [sumolib.__init__]
    CB[checkBinary]
    CALL[call / saveConfiguration]
  end
  subgraph opts [sumolib.options]
    AP[ArgumentParser]
    PO[pullOptions]
  end
  subgraph io [sumolib.xml + files]
    WH[writeHeader]
    PARSE[parse / parse_fast]
    ADD[files.additional]
  end
  subgraph net [sumolib.net]
    RN[readNet]
    GEO[convertLonLat2XY]
    PATH[getShortestPath]
  end
  ORCH[GIS_Orchestrator] --> CB
  ORCH --> AP
  ORCH --> WH
  ORCH --> RN
```

### Reference script usage

| Concern | osmBuild | osmWebWizard |
|---|---|---|
| `checkBinary` | netconvert, polyconvert | sumo, sumo-gui |
| `ArgumentParser` | CLI | CLI |
| `readNet` | — | post-build edges for demand |
| `writeXMLHeader` | — | additional output config |
| `.sumocfg` | — | `sumo --save-configuration` |
| TraCI | No | No |

## TraCI vs subprocess (simulation)

```mermaid
flowchart LR
  BUILD[Build_phase_subprocess] --> ART[Artifacts]
  ART --> A[subprocess sumo -c]
  ART --> B[traci.start + step loop]
  ART --> C[libsumo in-process]
  A --> OUT[XML outputs]
  B --> MON[live getters]
  C --> MON
```

**As-built default for scenario tools:** subprocess path (A). TraCI (B) used by co-simulation tools (`drtOnline.py`, `fcdReplay.py`).

## GIS API scope boundary

| In scope (import) | Out of scope |
|---|---|
| checkBinary, ArgumentParser, writeHeader, readNet | scenario/, visualization/, output/convert |
| subprocess + save-configuration pattern | Modifying sumolib/traci |
| Document TraCI for ADR-015 workshop | Implement TraCI in API v1 |

## Non-goals

- Resolving ADR-015 (workshop)
- Libsumo packaging in API container image
- TraCI test harness (slice 7)
