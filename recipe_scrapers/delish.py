from ._abstract import AbstractScraper


class Delish(AbstractScraper):

    @classmethod
    def host(cls):
        return "delish.com"
