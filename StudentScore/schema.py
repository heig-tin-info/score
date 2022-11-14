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


re_percent = r'(\d+(?:\.\d+)?)\%'

Percent = All(str, Match(re_percent), Replace(re_percent, r'\1'), Coerce(int), Range(0, 100))


class ValidPoints(object):
    """
    Verify the number of points given.
    """
    def __call__(self, v):
        obtained, total = v

        if total < 0 and obtained < total:
            raise InvalidPoint('Given points cannot be smaller than available penalty.')
        if total < 0 < obtained:
            raise InvalidPoint('Given points cannot be bigger than zero with penality criteria.')
        if total > 0 > obtained:
            raise InvalidPoint('Given points cannot be smaller than zero.')
        if obtained > total > 0:
            raise InvalidPoint('Given points cannot be greater than available points.')
        if total == 0:
            raise InvalidPoint('No points given to this criteria.')

        return v


Pair = All(Any(
    ExactSequence([Any(int, float), int]),
    All(ExactSequence([Percent, int]), lambda x: [x[0] * x[1] / 100, x[1]])
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
