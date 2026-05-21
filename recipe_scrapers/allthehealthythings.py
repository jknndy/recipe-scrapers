from ._abstract import AbstractScraper


class AllTheHealthyThings(AbstractScraper):

    @classmethod
    def host(cls):
        return "allthehealthythings.com"
