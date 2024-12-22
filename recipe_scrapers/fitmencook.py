from ._abstract import AbstractScraper
from ._utils import get_yields, normalize_string


class FitMenCook(AbstractScraper):
    @classmethod
    def host(cls):
        return "fitmencook.com"

    def yields(self):
        yields = None
        for h4 in self.soup.findAll("h4"):
            raw_yield = h4.text
            for word in raw_yield.split():
                if word.isdigit():
                    yields = word

        if yields:
            return get_yields(f"{yields} servings")

    def ingredients(self):
        ingredients_parent = self.soup.find("div", {"class": "fmc_ingredients"})
        ingredients = ingredients_parent.findAll("li")
        return [
            normalize_string(ingredient.get_text())
            for ingredient in ingredients
            if ingredient.find("strong") is None
        ]
