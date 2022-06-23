from voluptuous import Invalid, Optional, Schema, Required, All, Any, Self, Length, Coerce
from ruamel.yaml import load, RoundTripLoader

Section = Schema({
    Optional(Any('$description', '$desc')): str,
    Coerce(str): Any({
        Required(Any('$points', '$bonus')): All([int], Length(2)),
        Required(Any('$description', '$desc')): str,
        Optional('$rationale'): str,
        Optional('$test'): str,
    }, Self)
})

Criteria = Schema({
    'criteria': Section
})


class Validate:
    def __init__(self, stream):
        self._yaml = load(stream, Loader=RoundTripLoader)
        return self.validate()

    def validate(self):
        try:
            self.data = Criteria(self._yaml)
        except Invalid as e:
            path = '/'.join(e.path)
            try:
                node = self._yaml
                for key in e.path:
                    if (hasattr(node[key], '_yaml_line_col')):
                        node = node[key]
                    else:
                        break
                print(
                    f"Error: validation failed on line {node._yaml_line_col.line}:{node._yaml_line_col.col} (/{path}): {e.error_message}")
            except:
                print(e)
        else:
            return self.data
