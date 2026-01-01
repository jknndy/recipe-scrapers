from ._abstract import AbstractScraper


class ThisJess(AbstractScraper):
    @classmethod
    def host(cls):
        return "thisjess.com"
