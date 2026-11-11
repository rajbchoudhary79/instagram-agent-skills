"""A small validator for the subset of JSON Schema this project uses.

Supported keywords: type (string or list), required, properties,
additionalProperties (bool), items, enum, minLength, maxLength, minimum,
maximum, minItems, maxItems, pattern.

validate(instance, schema) returns a list of "path: message" strings.
An empty list means valid.
"""

import re

_TYPES = {
    "object": dict,
    "array": list,
    "string": str,
    "boolean": bool,
    "null": type(None),
}


def _is_type(value, name):
    if name == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if name == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, _TYPES[name])


def validate(instance, schema, path="$"):
    errors = []
    types = schema.get("type")
    if types is not None:
        tlist = types if isinstance(types, list) else [types]
        if not any(_is_type(instance, t) for t in tlist):
            return ["%s: expected %s, got %s" % (path, "/".join(tlist), type(instance).__name__)]

    if "enum" in schema and instance not in schema["enum"]:
        errors.append("%s: %r is not one of %s" % (path, instance, schema["enum"]))

    if isinstance(instance, str):
        if "minLength" in schema and len(instance) < schema["minLength"]:
            errors.append("%s: shorter than %d characters" % (path, schema["minLength"]))
        if "maxLength" in schema and len(instance) > schema["maxLength"]:
            errors.append("%s: longer than %d characters" % (path, schema["maxLength"]))
        if "pattern" in schema and not re.search(schema["pattern"], instance):
            errors.append("%s: does not match %s" % (path, schema["pattern"]))

    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        if "minimum" in schema and instance < schema["minimum"]:
            errors.append("%s: below minimum %s" % (path, schema["minimum"]))
        if "maximum" in schema and instance > schema["maximum"]:
            errors.append("%s: above maximum %s" % (path, schema["maximum"]))

    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < schema["minItems"]:
            errors.append("%s: needs at least %d items" % (path, schema["minItems"]))
        if "maxItems" in schema and len(instance) > schema["maxItems"]:
            errors.append("%s: allows at most %d items" % (path, schema["maxItems"]))
        if "items" in schema:
            for i, item in enumerate(instance):
                errors.extend(validate(item, schema["items"], "%s[%d]" % (path, i)))

    if isinstance(instance, dict):
        for key in schema.get("required", []):
            if key not in instance:
                errors.append("%s: missing required field '%s'" % (path, key))
        props = schema.get("properties", {})
        for key, value in instance.items():
            if key in props:
                errors.extend(validate(value, props[key], "%s.%s" % (path, key)))
            elif schema.get("additionalProperties") is False:
                errors.append("%s: unexpected field '%s'" % (path, key))
    return errors
