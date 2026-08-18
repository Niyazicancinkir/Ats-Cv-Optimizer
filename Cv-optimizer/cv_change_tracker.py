import json


def _to_comparable(value):
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return value


def _flatten(data, prefix=""):
    rows = {}
    if isinstance(data, dict):
        for key, value in data.items():
            next_prefix = f"{prefix}.{key}" if prefix else key
            rows.update(_flatten(value, next_prefix))
        return rows

    if isinstance(data, list):
        for index, value in enumerate(data):
            next_prefix = f"{prefix}[{index}]"
            rows.update(_flatten(value, next_prefix))
        return rows

    rows[prefix] = data
    return rows


def _shorten(value, max_len=280):
    text = str(value)
    if len(text) <= max_len:
        return text
    return text[:max_len] + "..."


def build_cv_change_report(base_cv, optimized_cv):
    base_map = _flatten(base_cv)
    optimized_map = _flatten(optimized_cv)

    changed = []
    added = []
    removed = []

    for key, old_value in base_map.items():
        if key not in optimized_map:
            removed.append({"field": key, "before": _shorten(old_value), "after": ""})
            continue

        new_value = optimized_map[key]
        if _to_comparable(old_value) != _to_comparable(new_value):
            changed.append(
                {
                    "field": key,
                    "before": _shorten(old_value),
                    "after": _shorten(new_value),
                }
            )

    for key, new_value in optimized_map.items():
        if key not in base_map:
            added.append({"field": key, "before": "", "after": _shorten(new_value)})

    return {
        "summary": {
            "changed_count": len(changed),
            "added_count": len(added),
            "removed_count": len(removed),
        },
        "changed": changed,
        "added": added,
        "removed": removed,
    }
