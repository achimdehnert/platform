"""Non-destructive docstring insertion via libcst.

Inserts generated docstrings into Python source files while
preserving all existing formatting, comments, and whitespace.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class InsertionResult:
    """Result of a docstring insertion."""

    file_path: Path
    items_inserted: int
    items_skipped: int
    original_source: str
    modified_source: str

    @property
    def changed(self) -> bool:
        """Whether the source was modified."""
        return self.original_source != self.modified_source


def insert_docstrings(
    file_path: Path,
    docstrings: dict[str, str],
    *,
    dry_run: bool = True,
) -> InsertionResult:
    """Insert docstrings into a Python file using libcst.

    Args:
        file_path: Path to the Python file.
        docstrings: Mapping of item name → docstring text.
        dry_run: If True, do not write changes to disk.

    Returns:
        InsertionResult with original and modified source.
    """
    import libcst as cst

    original = file_path.read_text(encoding="utf-8")

    try:
        tree = cst.parse_module(original)
    except cst.ParserSyntaxError as exc:
        logger.warning("Cannot parse %s: %s", file_path, exc)
        return InsertionResult(
            file_path=file_path,
            items_inserted=0,
            items_skipped=len(docstrings),
            original_source=original,
            modified_source=original,
        )

    transformer = _DocstringInserter(docstrings)
    modified_tree = transformer.transform(tree)
    modified_source = modified_tree.code

    result = InsertionResult(
        file_path=file_path,
        items_inserted=transformer.inserted,
        items_skipped=transformer.skipped,
        original_source=original,
        modified_source=modified_source,
    )

    if not dry_run and result.changed:
        file_path.write_text(modified_source, encoding="utf-8")
        logger.info(
            "Wrote %d docstrings to %s",
            transformer.inserted, file_path,
        )

    return result


class _DocstringInserter:
    """Manual CST transformer that inserts docstrings."""

    def __init__(self, docstrings: dict[str, str]) -> None:
        self.docstrings = docstrings
        self.inserted = 0
        self.skipped = 0

    def transform(self, tree: object) -> object:
        """Transform the CST tree by inserting docstrings."""
        import libcst as cst

        if not isinstance(tree, cst.Module):
            return tree

        # Module-level docstring
        module_name = None
        for name in self.docstrings:
            if "." not in name and name == name.lower():
                module_name = name
                break

        new_body = list(tree.body)

        if module_name and module_name in self.docstrings:
            if not _has_docstring_node(new_body):
                ds = self.docstrings[module_name]
                new_body = [_make_docstring_stmt(ds)] + new_body
                self.inserted += 1
            else:
                self.skipped += 1

        # Process classes and functions
        processed_body = []
        for stmt in new_body:
            processed_body.append(
                self._process_statement(stmt)
            )

        return tree.with_changes(body=processed_body)

    def _process_statement(self, stmt: object) -> object:
        """Process a single statement, inserting docstrings."""
        import libcst as cst

        if isinstance(stmt, (cst.ClassDef, cst.FunctionDef)):
            name = stmt.name.value
            if name in self.docstrings and not _body_has_docstring(stmt):
                new_body = _prepend_docstring(
                    stmt.body, self.docstrings[name]
                )
                self.inserted += 1
                stmt = stmt.with_changes(body=new_body)
            elif name in self.docstrings:
                self.skipped += 1

            # Recurse into class body for methods
            if isinstance(stmt, cst.ClassDef):
                stmt = self._process_class_body(stmt)

        return stmt

    def _process_class_body(self, class_def: object) -> object:
        """Process class body to insert method docstrings."""
        import libcst as cst

        if not isinstance(class_def, cst.ClassDef):
            return class_def

        body = class_def.body
        if not isinstance(body, cst.IndentedBlock):
            return class_def

        new_stmts = []
        for stmt in body.body:
            new_stmts.append(self._process_statement(stmt))

        return class_def.with_changes(
            body=body.with_changes(body=new_stmts)
        )


def _has_docstring_node(body: list) -> bool:
    """Check if a body list starts with a docstring."""
    import libcst as cst

    if not body:
        return False
    first = body[0]
    if isinstance(first, cst.SimpleStatementLine):
        for stmt in first.body:
            if isinstance(stmt, cst.Expr) and isinstance(
                stmt.value,
                (cst.SimpleString, cst.ConcatenatedString, cst.FormattedString),
            ):
                return True
    return False


def _body_has_docstring(node: object) -> bool:
    """Check if a class/function def has a docstring."""
    import libcst as cst

    if not hasattr(node, "body"):
        return False
    body = node.body
    if isinstance(body, cst.IndentedBlock) and body.body:
        first = body.body[0]
        if isinstance(first, cst.SimpleStatementLine):
            for stmt in first.body:
                if isinstance(stmt, cst.Expr) and isinstance(
                    stmt.value, (cst.SimpleString, cst.ConcatenatedString)
                ):
                    return True
    return False


def _make_docstring_stmt(docstring: str) -> object:
    """Create a CST docstring statement."""
    import libcst as cst

    escaped = docstring.replace('\\', '\\\\').replace('"', '\\"')
    return cst.SimpleStatementLine(
        body=[
            cst.Expr(
                value=cst.SimpleString(f'"""{escaped}"""')
            )
        ]
    )


def _prepend_docstring(body: object, docstring: str) -> object:
    """Prepend a docstring to an indented block."""
    import libcst as cst

    if not isinstance(body, cst.IndentedBlock):
        return body

    ds_stmt = cst.SimpleStatementLine(
        body=[
            cst.Expr(
                value=cst.SimpleString(f'"""{docstring}"""')
            )
        ]
    )

    new_body = [ds_stmt] + list(body.body)
    return body.with_changes(body=new_body)
