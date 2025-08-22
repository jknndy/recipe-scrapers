from ._abstract import AbstractScraper


class Chefkoch(AbstractScraper):
    @classmethod
    def host(cls):
        return "chefkoch.de"

    def instructions(self):
        instruction_elements = self.soup.select(
            'span.instruction__text[data-testid="recipe-instruction"]'
        )
        steps = [element.get_text(strip=True) for element in instruction_elements]
        return "\n".join(steps)
