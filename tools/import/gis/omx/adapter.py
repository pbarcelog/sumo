# SPDX-License-Identifier: EPL-2.0 OR GPL-2.0-or-later

from __future__ import annotations

from pathlib import Path
import xml.sax.saxutils as saxutils


XSD = "http://sumo.dlr.de/xsd/datamode_file.xsd"


def write_taz_relation(
    omx_path: Path,
    output_path: Path,
    default_vtype: str = "DEFAULT_VEHTYPE",
) -> set[str]:
    import openmatrix as omx

    zone_ids: set[str] = set()
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<data xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" '
        f'xsi:noNamespaceSchemaLocation="{XSD}">',
    ]

    with omx.open_file(str(omx_path), "r") as f:
        for matrix_name in f.list_matrices():
            matrix = f[matrix_name]
            try:
                keymap = f.mapping(matrix_name)
            except LookupError:
                keymap = {str(i): i for i in range(matrix.shape[0])}
            labels = [None] * len(keymap)
            for label, index in keymap.items():
                labels[index] = str(label)
            vtype = default_vtype
            interval_id = matrix_name

            lines.append(f'    <interval id="{saxutils.escape(str(vtype))}" begin="0" end="86400">')
            for i, origin in enumerate(labels):
                for j, destination in enumerate(labels):
                    count = float(matrix[i, j])
                    if count <= 0:
                        continue
                    origin_id = str(origin)
                    dest_id = str(destination)
                    zone_ids.add(origin_id)
                    zone_ids.add(dest_id)
                    count_str = str(int(count) if count == int(count) else count)
                    lines.append(
                        f'      <tazRelation from="{saxutils.escape(origin_id)}" '
                        f'to="{saxutils.escape(dest_id)}" count="{count_str}"/>'
                    )
            lines.append("    </interval>")

    lines.append("</data>")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return zone_ids
