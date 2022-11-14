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

        if obtained < total < 0:
            raise InvalidPoint((
                f'Given points ({obtained}) cannot be smaller '
                f"than available penalty ({total})."))
        if total < 0 < obtained:
            raise InvalidPoint((
                f'Given points ({obtained}) cannot be bigger '
                f'than zero with penalty criteria ({total}).'))
        if total > 0 > obtained:
            raise InvalidPoint(
                f'Given points ({obtained}) cannot be smaller than zero.')
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

DescriptionKey = Any('$description', '$desc')

Section = Schema({
    Optional(DescriptionKey): str,
    Coerce(str): Any({
        Required(Any('$points', '$bonus')): Pair,
        Required(DescriptionKey): Any(str, [str]),
        Optional('$rationale'): Any(str, [str]),
        Optional('$test'): str
    }, Self)
})

Criteria = Schema(Section)


# class Validate:
#     """ Validate schema. """

#     def __init__(self, stream):
#         self._yaml = yaml.load(stream, Loader=yaml.FullLoader)
#         return self.validate()

#     def validate(self):
#         """ Validate schema. """
#         try:
#             self.data = Criteria(self._yaml)
#         except Invalid as exept:
#             path = '/'.join(exept.path)
#             try:
#                 node = self._yaml
#                 for key in exept.path:
#                     if (hasattr(node[key], '_yaml_line_col')):
#                         node = node[key]
#                     else:
#                         break
#                 print(f"Error: validation failed on line"
#                       f"{node._yaml_line_col.line}:"
#                       f"{node._yaml_line_col.col} (/{path}): {exept.error_message}")
#             except Exception as ex:
#                 print(ex)

#         return self.data
