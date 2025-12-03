from ._abstract import AbstractScraper
from ._exceptions import FieldNotProvidedByWebsiteException


class AnitasTableTalk(AbstractScraper):
    @classmethod
    def host(cls):
        return "anitastabletalk.com"

    def total_time(self):
        raise FieldNotProvidedByWebsiteException(return_value=None)

    def yields(self):
        raise FieldNotProvidedByWebsiteException(return_value=None)
