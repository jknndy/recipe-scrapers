from ._abstract import AbstractScraper


class SheLikesFood(AbstractScraper):

    @classmethod
    def host(cls):
        return "shelikesfood.com"
