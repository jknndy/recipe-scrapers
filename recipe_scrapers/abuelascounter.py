from ._abstract import AbstractScraper


class AbuelasCounter(AbstractScraper):

    @classmethod
    def host(cls):
        return "abuelascounter.com"
