from ._abstract import AbstractScraper
from ._utils import get_minutes


class ReceitasNestleBR(AbstractScraper):
    @classmethod
    def host(cls):
        return "receitasnestle.com.br"

    def total_time(self):
        time_div = self.soup.find("div", class_="recipeDetail__infoItem--time")
        return get_minutes(time_div)

    def instructions(self):
        instructions = self.schema.instructions()
        if instructions.startswith("Modo de Preparo"):
            instructions = instructions.split("\n", 1)[-1]
        return instructions
