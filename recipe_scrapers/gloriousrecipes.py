from ._abstract import AbstractScraper


class GloriousRecipes(AbstractScraper):

    @classmethod
    def host(cls):
        return "gloriousrecipes.com"
