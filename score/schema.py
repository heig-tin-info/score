from voluptuous import Invalid, Optional, Schema, Required, All, Any, Self, Length
from ruamel.yaml import load, RoundTripLoader

Section = Schema({
    str: Any({
        Required(Any('$points', '$bonus')): All([int], Length(2)),
        Required('$description', '$desc'): str,
        Optional('$rationale'): str
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
                print(f"Error: validation failed on line {node._yaml_line_col.line}:{node._yaml_line_col.col} (/{path}): {e.error_message}")
            except:
                print(e)
        else:
            return self.data