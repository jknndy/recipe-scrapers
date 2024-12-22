from ._abstract import AbstractScraper
from ._utils import get_minutes
from ._grouping_utils import group_ingredients


class ReceitasNestleBR(AbstractScraper):
    @classmethod
    def host(cls):
        return "receitasnestle.com.br"

    def total_time(self):
        time_div = self.soup.find("div", class_="recipeDetail__infoItem--time")
        return get_minutes(time_div)

    def prep_time(self):
        return None

    def cook_time(self):
        return None

    def instructions(self):
        instructions = self.schema.instructions()
        if instructions.startswith("Modo de Preparo"):
            instructions = instructions.split("\n", 1)[-1]
        return instructions

    def ingredient_groups(self):
        groups = group_ingredients(
            self.ingredients(),
            self.soup,
            ".recipeDetail__ingredients h2",
            ".recipeDetail__ingredients label",
        )

        if (
            len(groups) == 1
            and groups[0].purpose
            and groups[0].purpose.lower() == "ingredientes"
        ):
            groups[0].purpose = None

        return groups
