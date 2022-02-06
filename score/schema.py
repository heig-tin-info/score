from voluptuous import Optional, Schema, Required, All, Any, Self, Length

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
