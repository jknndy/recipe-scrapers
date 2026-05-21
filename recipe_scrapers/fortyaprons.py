from ._abstract import AbstractScraper
from ._wprm import WPRMMixin


class FortyAprons(WPRMMixin, AbstractScraper):

    @classmethod
    def host(cls):
        return "40aprons.com"
