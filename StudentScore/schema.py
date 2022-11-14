from voluptuous import (
    All,
    Any,
    Coerce,
    ExactSequence,
    Match,
    Optional,
    Range,
    Replace,
    Required,
    Schema,
    Self,
)
from voluptuous.error import Invalid


class InvalidPoint(Invalid):
    """Invalid points."""


re_percent = r'(-?\d+(?:\.\d+)?)\%'

Percent = All(str,
              Match(re_percent),
              Replace(re_percent, r'\1'),
              Coerce(float),
              Range(-100, 100),
              lambda x: x/100
              )


class ValidPoints(object):
    """
    Verify the number of points given.
    """

    def __call__(self, v):
        obtained, total = v

        if total < 0 and obtained < total:
            raise InvalidPoint((
                f'Given points ({obtained}) cannot be smaller '
                f"than available penalty ({total})."))
        if total < 0 < obtained:
            raise InvalidPoint((
                f'Given points ({obtained}) cannot be bigger '
                f'than zero with penality criteria ({total}).'))
        if total > 0 > obtained:
            raise InvalidPoint(f'Given points ({obtained}) cannot be smaller than zero.')
        if obtained > total > 0:
            raise InvalidPoint(
                f'Given points ({obtained}) cannot be greater than available points ({total}).')
        if total == 0:
            raise InvalidPoint('No points given to this criteria.')

        return v


Pair = All(Any(
    ExactSequence([Any(int, float), int]),
    All(ExactSequence([Percent, int]), lambda x: [abs(x[0]) * x[1], x[1]])
), ValidPoints())

Section = Schema({
    str: Any({
        Required(Any('$points', '$bonus')): Pair,
        Required('$description', '$desc'): Any(str, [str]),
        Optional('$rationale'): Any(str, [str]),
        Optional('$test'): str
    }, Self)
})

Criteria = Schema({
    'criteria': Section
})
