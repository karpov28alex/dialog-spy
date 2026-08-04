from __future__ import annotations

import ast
from pathlib import Path

VERSIONS_DIR = Path("alembic/versions")


def _metadata(path: Path) -> tuple[str, str | None]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    values: dict[str, str | None] = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name) or target.id not in {"revision", "down_revision"}:
            continue
        if isinstance(node.value, ast.Constant) and (
            isinstance(node.value.value, str) or node.value.value is None
        ):
            values[target.id] = node.value.value
    revision = values.get("revision")
    if not isinstance(revision, str):
        raise RuntimeError(f"Missing revision in {path}")
    return revision, values.get("down_revision")


def main() -> None:
    migrations = [_metadata(path) for path in sorted(VERSIONS_DIR.glob("*.py"))]
    revisions = {revision for revision, _ in migrations}
    if len(revisions) != len(migrations):
        raise RuntimeError("Duplicate Alembic revision detected")

    roots = [revision for revision, parent in migrations if parent is None]
    if len(roots) != 1:
        raise RuntimeError(f"Expected one Alembic root, found {roots}")

    children: dict[str, list[str]] = {revision: [] for revision in revisions}
    for revision, parent in migrations:
        if parent is None:
            continue
        if parent not in revisions:
            raise RuntimeError(f"Revision {revision} references missing parent {parent}")
        children[parent].append(revision)

    branches = {revision: rows for revision, rows in children.items() if len(rows) > 1}
    if branches:
        raise RuntimeError(f"Alembic branches detected: {branches}")

    heads = [revision for revision, rows in children.items() if not rows]
    if len(heads) != 1:
        raise RuntimeError(f"Expected one Alembic head, found {heads}")
    print(f"Alembic chain is linear: {roots[0]} -> {heads[0]} ({len(migrations)} revisions)")


if __name__ == "__main__":
    main()
