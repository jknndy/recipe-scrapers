from ._abstract import AbstractScraper


class PolishFoodies(AbstractScraper):

    @classmethod
    def host(cls):
        return "polishfoodies.com"
