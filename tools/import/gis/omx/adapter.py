# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later

"""OMX matrix → SUMO ``tazRelation.xml`` (ADR-012).

Reads the named zone mapping (default ``NO``), emits one ``interval`` per
requested core with ``id`` equal to the target vType, and skips deferred cores
(e.g. ``PUT`` in v1).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import xml.sax.saxutils as saxutils

XSD = "http://sumo.dlr.de/xsd/datamode_file.xsd"

DEFAULT_CORE_VTYPE: dict[str, str] = {
    "Car": "passenger",
    "HVG": "truck",
}

DEFAULT_CORES: tuple[str, ...] = ("Car", "HVG")


@dataclass
class OmxAdapterOptions:
    mapping_name: str = "NO"
    cores: tuple[str, ...] = DEFAULT_CORES
    core_vtype: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_CORE_VTYPE))
    skip_cores: tuple[str, ...] = ("PUT",)
    emit_intrazonal: bool = True
    interval_begin: float = 0.0
    interval_end: float = 86400.0
    fail_on_missing_mapping: bool = True


@dataclass
class OmxAdapterResult:
    zone_ids: set[str] = field(default_factory=set)
    relation_counts: dict[str, int] = field(default_factory=dict)
    skipped_cores: list[str] = field(default_factory=list)
    unmapped_cores: list[str] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)


def _labels_from_mapping(f, mapping_name: str) -> list[str]:
    keymap = f.mapping(mapping_name)
    size = max(keymap.values()) + 1 if keymap else 0
    labels: list[str | None] = [None] * size
    for label, index in keymap.items():
        labels[index] = str(label)
    if any(item is None for item in labels):
        raise ValueError(f"OMX mapping {mapping_name!r} has gaps in index coverage")
    return [str(item) for item in labels]


def _should_emit_relation(
    origin_id: str,
    dest_id: str,
    i: int,
    j: int,
    opts: OmxAdapterOptions,
    zone_access: dict[str, tuple[bool, bool]] | None,
    result: OmxAdapterResult,
) -> bool:
    if i == j:
        if not opts.emit_intrazonal:
            return False
        if zone_access is not None:
            has_source, has_sink = zone_access.get(origin_id, (False, False))
            if not (has_source and has_sink):
                result.messages.append(
                    f"dropped intrazonal demand for zone {origin_id} (no spawn/absorb path)"
                )
                return False
        return True

    if zone_access is not None:
        has_source, _ = zone_access.get(origin_id, (False, False))
        _, has_sink = zone_access.get(dest_id, (False, False))
        if not has_source or not has_sink:
            missing = "tazSource" if not has_source else "tazSink"
            zone = origin_id if not has_source else dest_id
            raise ValueError(
                f"OMX relation {origin_id}->{dest_id} has demand but zone {zone} "
                f"has no resolvable {missing}"
            )
    return True


def write_taz_relation(
    omx_path: Path,
    output_path: Path,
    options: OmxAdapterOptions | str | None = None,
    *,
    zone_access: dict[str, tuple[bool, bool]] | None = None,
) -> OmxAdapterResult:
    """Write ``tazRelation.xml`` from an OMX file.

    When ``options`` is a ``str`` (legacy GIS API path), all matrices are written
    into one interval with that vType id.
    """
    import openmatrix as omx

    if isinstance(options, str):
        legacy = OmxAdapterOptions(
            cores=tuple(),
            core_vtype={},
            skip_cores=tuple(),
            fail_on_missing_mapping=False,
        )
        return _write_legacy_taz_relation(omx_path, output_path, options, legacy)

    opts = options or OmxAdapterOptions()
    result = OmxAdapterResult()

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<data xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
        f'xsi:noNamespaceSchemaLocation="{XSD}">',
    ]

    with omx.open_file(str(omx_path), "r") as f:
        mappings = f.list_mappings()
        if opts.mapping_name in mappings:
            labels = _labels_from_mapping(f, opts.mapping_name)
        elif opts.fail_on_missing_mapping:
            raise ValueError(
                f"OMX file {omx_path} has no mapping {opts.mapping_name!r}; "
                f"available: {mappings}"
            )
        else:
            matrix = f[f.list_matrices()[0]]
            labels = [str(i) for i in range(matrix.shape[0])]
            result.messages.append(
                f"missing mapping {opts.mapping_name!r}; fell back to 0-based indices"
            )

        for core in opts.cores:
            if core in opts.skip_cores:
                result.skipped_cores.append(core)
                result.messages.append(f"skipped core {core!r}")
                continue
            if core not in f.list_matrices():
                result.unmapped_cores.append(core)
                result.messages.append(f"core {core!r} not in OMX file")
                continue
            vtype = opts.core_vtype.get(core)
            if not vtype:
                result.unmapped_cores.append(core)
                result.messages.append(f"no vType mapping for core {core!r}")
                continue

            matrix = f[core]
            count = 0
            lines.append(
                f'    <interval id="{saxutils.escape(vtype)}" '
                f'begin="{opts.interval_begin:g}" end="{opts.interval_end:g}">'
            )
            for i, origin in enumerate(labels):
                for j, destination in enumerate(labels):
                    value = float(matrix[i, j])
                    if value <= 0:
                        continue
                    origin_id = str(origin)
                    dest_id = str(destination)
                    if not _should_emit_relation(
                        origin_id, dest_id, i, j, opts, zone_access, result
                    ):
                        continue
                    result.zone_ids.add(origin_id)
                    result.zone_ids.add(dest_id)
                    count_str = str(int(value) if value == int(value) else value)
                    lines.append(
                        f'      <tazRelation from="{saxutils.escape(origin_id)}" '
                        f'to="{saxutils.escape(dest_id)}" count="{count_str}"/>'
                    )
                    count += 1
            lines.append("    </interval>")
            result.relation_counts[core] = count

        for core in opts.skip_cores:
            if core in f.list_matrices() and core not in result.skipped_cores:
                result.skipped_cores.append(core)
                result.messages.append(f"skipped core {core!r}")

    lines.append("</data>")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result


def write_taz_relation_for_core(
    omx_path: Path,
    output_path: Path,
    core: str,
    options: OmxAdapterOptions | None = None,
    *,
    zone_access: dict[str, tuple[bool, bool]] | None = None,
) -> OmxAdapterResult:
    """Write a single-core ``tazRelation`` file (one interval / one vType)."""
    opts = options or OmxAdapterOptions()
    per_core = OmxAdapterOptions(
        mapping_name=opts.mapping_name,
        cores=(core,),
        core_vtype=dict(opts.core_vtype),
        skip_cores=tuple(c for c in opts.skip_cores if c != core),
        emit_intrazonal=opts.emit_intrazonal,
        interval_begin=opts.interval_begin,
        interval_end=opts.interval_end,
        fail_on_missing_mapping=opts.fail_on_missing_mapping,
    )
    return write_taz_relation(omx_path, output_path, per_core, zone_access=zone_access)


def _write_legacy_taz_relation(
    omx_path: Path,
    output_path: Path,
    default_vtype: str,
    opts: OmxAdapterOptions,
) -> OmxAdapterResult:
    import openmatrix as omx

    result = OmxAdapterResult()
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<data xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
        f'xsi:noNamespaceSchemaLocation="{XSD}">',
    ]

    with omx.open_file(str(omx_path), "r") as f:
        for matrix_name in f.list_matrices():
            matrix = f[matrix_name]
            try:
                labels = _labels_from_mapping(f, opts.mapping_name)
            except (LookupError, ValueError):
                labels = [str(i) for i in range(matrix.shape[0])]
                result.messages.append(
                    f"legacy path: mapping {opts.mapping_name!r} unavailable; using indices"
                )
            lines.append(
                f'    <interval id="{saxutils.escape(default_vtype)}" '
                f'begin="{opts.interval_begin:g}" end="{opts.interval_end:g}">'
            )
            count = 0
            for i, origin in enumerate(labels):
                for j, destination in enumerate(labels):
                    value = float(matrix[i, j])
                    if value <= 0:
                        continue
                    origin_id = str(origin)
                    dest_id = str(destination)
                    result.zone_ids.add(origin_id)
                    result.zone_ids.add(dest_id)
                    count_str = str(int(value) if value == int(value) else value)
                    lines.append(
                        f'      <tazRelation from="{saxutils.escape(origin_id)}" '
                        f'to="{saxutils.escape(dest_id)}" count="{count_str}"/>'
                    )
                    count += 1
            lines.append("    </interval>")
            result.relation_counts[matrix_name] = count

    lines.append("</data>")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result
