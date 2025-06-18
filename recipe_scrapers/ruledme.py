from ._abstract import AbstractScraper


class RuledMe(AbstractScraper):
    @classmethod
    def host(cls):
        return "ruled.me"
