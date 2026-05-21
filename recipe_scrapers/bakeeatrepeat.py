from ._abstract import AbstractScraper


class BakeEatRepeat(AbstractScraper):

    @classmethod
    def host(cls):
        return "bake-eat-repeat.com"
