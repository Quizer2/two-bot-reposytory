"""A minimal YAML loader used when PyYAML is unavailable.

The helper understands the subset of YAML exercised by the repository's
configuration files (mappings, nested mappings, lists and inline entries).
When PyYAML is present we delegate to it to keep behaviour identical to
production deployments.
"""
from __future__ import annotations

from typing import Any, Iterable, Tuple

import json

try:  # pragma: no cover - exercised indirectly in environments with PyYAML
    from yaml import safe_load as _yaml_safe_load  # type: ignore
except Exception:  # pragma: no cover - PyYAML not installed in tests
    _yaml_safe_load = None


def safe_load(stream: Any) -> Any:
    """Parse *stream* into Python primitives.

    The function mirrors :func:`yaml.safe_load` but falls back to a tiny parser
    whenever PyYAML is not present.  ``stream`` may be a string, bytes object or
    any object exposing ``read``.
    """
    if stream is None:
        return None

    if hasattr(stream, "read"):
        stream = stream.read()

    if isinstance(stream, bytes):
        stream = stream.decode("utf-8")

    if not isinstance(stream, str):
        raise TypeError("safe_load expects a string, bytes or file-like object")

    if _yaml_safe_load is not None:
        return _yaml_safe_load(stream)

    text = stream.strip()
    if not text:
        return None

    lines = _prepare_lines(text.splitlines())
    result, _ = _parse_block(lines, 0, 0)
    return result


# ---------------------------------------------------------------------------
# Minimal YAML parsing helpers
# ---------------------------------------------------------------------------

def _prepare_lines(raw_lines: Iterable[str]) -> Tuple[Tuple[int, str], ...]:
    processed = []
    for line in raw_lines:
        if not line.strip():
            continue
        stripped = line.lstrip()
        if stripped.startswith("#"):
            continue
        indent = len(line) - len(stripped)
        processed.append((indent, stripped))
    return tuple(processed)


def _parse_block(lines: Tuple[Tuple[int, str], ...], index: int, indent: int) -> Tuple[Any, int]:
    container: Any = None
    while index < len(lines):
        cur_indent, content = lines[index]
        if cur_indent < indent:
            break
        if cur_indent > indent:
            # Nested content is consumed by the previous iteration
            raise ValueError(f"Unexpected indentation at line {index + 1}: {content}")

        if content.startswith("- "):
            if container is None:
                container = []
            elif not isinstance(container, list):
                raise ValueError("Mixed mapping/list structure is not supported")

            item_text = content[2:].strip()
            index += 1
            if item_text == "":
                child, index = _parse_block(lines, index, indent + 2)
                container.append({} if child is None else child)
            else:
                value: Any
                if ":" in item_text and not item_text.startswith("{"):
                    key, value_part = item_text.split(":", 1)
                    value = {key.strip(): _parse_scalar(value_part.strip())}
                else:
                    value = _parse_scalar(item_text)
                # Merge nested block if present
                if index < len(lines) and lines[index][0] > indent:
                    child, index = _parse_block(lines, index, indent + 2)
                    if isinstance(value, dict) and isinstance(child, dict):
                        value.update(child)
                    elif child is None:
                        pass
                    else:
                        raise ValueError("Unsupported nested structure inside list item")
                container.append(value)
            continue

        if ":" in content:
            key, value_text = content.split(":", 1)
            key = key.strip()
            value_text = value_text.strip()
            if container is None:
                container = {}
            elif not isinstance(container, dict):
                raise ValueError("Mixed list/mapping structure is not supported")

            index += 1
            if value_text == "":
                child, index = _parse_block(lines, index, indent + 2)
                container[key] = {} if child is None else child
            else:
                value = _parse_scalar(value_text)
                if index < len(lines) and lines[index][0] > indent:
                    child, index = _parse_block(lines, index, indent + 2)
                    if isinstance(value, dict) and isinstance(child, dict):
                        value.update(child)
                    elif child is None:
                        pass
                    else:
                        raise ValueError("Unsupported nested scalar structure for key '%s'" % key)
                container[key] = value
            continue

        raise ValueError(f"Unable to parse line {index + 1}: {content}")

    return container, index


def _parse_scalar(text: str) -> Any:
    if text.startswith("{") and text.endswith("}"):
        return _parse_inline_dict(text[1:-1])
    if text.startswith("[") and text.endswith("]"):
        return _parse_inline_list(text[1:-1])

    lower = text.lower()
    if lower in {"null", "none", "~"}:
        return None
    if lower == "true":
        return True
    if lower == "false":
        return False

    # Numeric detection (ints and floats)
    try:
        if any(ch in text for ch in (".", "e", "E")):
            return float(text)
        return int(text)
    except ValueError:
        pass

    if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
        return text[1:-1]

    return text


def _split_top_level(text: str) -> Tuple[str, ...]:
    parts = []
    buf = []
    depth = 0
    in_single = False
    in_double = False
    for char in text:
        if char == "'" and not in_double:
            in_single = not in_single
        elif char == '"' and not in_single:
            in_double = not in_double
        elif char in "[{" and not in_single and not in_double:
            depth += 1
        elif char in "}]" and not in_single and not in_double:
            depth = max(depth - 1, 0)
        if char == "," and depth == 0 and not in_single and not in_double:
            parts.append("".join(buf).strip())
            buf = []
            continue
        buf.append(char)
    if buf:
        parts.append("".join(buf).strip())
    return tuple(p for p in parts if p)


def _parse_inline_dict(text: str) -> dict:
    result = {}
    if not text.strip():
        return result
    for chunk in _split_top_level(text):
        if ":" not in chunk:
            raise ValueError(f"Invalid inline mapping chunk: {chunk}")
        key, value = chunk.split(":", 1)
        result[key.strip()] = _parse_scalar(value.strip())
    return result


def _parse_inline_list(text: str) -> list:
    if not text.strip():
        return []
    return [_parse_scalar(chunk) for chunk in _split_top_level(text)]


def safe_dump(data: Any, **kwargs: Any) -> str:
    """Minimal replacement for :func:`yaml.safe_dump` used in a few utilities."""
    if _yaml_safe_load is not None:
        from yaml import safe_dump as _yaml_safe_dump  # type: ignore

        return _yaml_safe_dump(data, **kwargs)
    return json.dumps(data, **({"indent": 2} | kwargs))


__all__ = ["safe_load", "safe_dump"]
