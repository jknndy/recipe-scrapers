from ._abstract import AbstractScraper


class TheCleverCarrot(AbstractScraper):

    @classmethod
    def host(cls):
        return "theclevercarrot.com"
