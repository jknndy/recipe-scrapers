from ._abstract import AbstractScraper


class FavFamilyRecipes(AbstractScraper):
    @classmethod
    def host(cls):
        return "favfamilyrecipes.com"
