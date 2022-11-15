
import io
from collections import namedtuple
from math import ceil
import yaml

from .schema import Criteria

Points = namedtuple('Points', ['got', 'total', 'bonus'])


def round_up(n, decimals=0):
    """ Round up to the nearest integer. """
    multiplier = 10 ** decimals
    return ceil(n * multiplier) / multiplier


class Score:
    def __init__(self, data):
        if isinstance(data, io.TextIOBase):
            data = Criteria(yaml.load(data, Loader=yaml.FullLoader))
        elif isinstance(data, str):
            with open(data, 'rt', encoding='utf8') as f:
                data = Criteria(yaml.load(f, Loader=yaml.FullLoader))
        self.data = Criteria(data)

    @property
    def mark(self):
        if self.total == 0:
            raise ValueError('Total is zero points')
        return max(1.0, min(6.0, round_up(5. * self.got / self.total + 1., 1)))

    @property
    def points(self):
        return self._get_points(self.data)

    @property
    def total(self):
        return self.points.total

    @property
    def bonus(self):
        return self.points.bonus

    @property
    def got(self):
        return self.points.got

    @property
    def success(self):
        return self.mark >= 4.0

    def _get_points(self, u):
        got = 0
        total = 0
        bonus = 0
        for k, v in u.items():
            if isinstance(v, dict):
                pts = self._get_points(v)
                got += pts.got
                total += pts.total
                bonus += pts.bonus
            elif isinstance(v, list) and k in ['$points', '$pts']:
                _got, _total = v
                got += float(_got)
                total += float(_total) if float(_total) > 0 else 0
            elif isinstance(v, list) and k == '$bonus':
                _got, _total = v
                bonus += float(_got)
                got += float(_got)
        return Points(got=got, total=total, bonus=bonus)
