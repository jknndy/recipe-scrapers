from ._abstract import AbstractScraper
from ._grouping_utils import group_ingredients


class Chefnini(AbstractScraper):
    @classmethod
    def host(cls):
        return "chefnini.com"

    def ingredient_groups(self):
        return group_ingredients(
            self.ingredients(),
            self.soup,
            "h3:not([itemprop='recipeYield'])",
            "ul li[itemprop='ingredients']",
        )
