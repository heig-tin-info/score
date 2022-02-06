
from .schema import Criteria
from collections import namedtuple
import yaml 
import io

Points = namedtuple('Points', ['got', 'total', 'bonus'])

class Score:
    def __init__(self, data=None, file=None):
        if isinstance(file, io.TextIOBase):
            data = Criteria(yaml.load(file, Loader=yaml.FullLoader))
        elif isinstance(file, str):
            with open(file) as f:
                data = Criteria(yaml.load(f, Loader=yaml.FullLoader))
        self.data = Criteria(data)

    @property
    def mark(self):
        return self._note(self.points.got, self.points.total)

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
    def success(self):
        return self.mark >= 4.0

    def _note(got, total):
        return round(got / total * 5. + 1., 1)

    def _get_points(self, u):
        got = 0
        total = 0
        bonus = 0
        for k, v in u.items():
            if isinstance(v, dict):
                _bonus, _got, _total = self._get_points(v)
                got += _got
                total += _total
                bonus += _bonus
            elif isinstance(v, list) and k in ['$points', '$pts']:
                _got, _total = v
                got += float(_got)
                total += float(_total) if float(_total) > 0 else 0
            elif isinstance(v, list) and k == '$bonus':
                _got, _total = v
                bonus += float(_got)
                got += float(_got)
        return Points(got, total, bonus)

