from ._abstract import AbstractScraper


class Chefnini(AbstractScraper):
    @classmethod
    def host(cls):
        return "chefnini.com"
