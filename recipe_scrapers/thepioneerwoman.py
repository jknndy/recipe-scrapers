from ._abstract import AbstractScraper


class ThePioneerWoman(AbstractScraper):

    @classmethod
    def host(cls):
        return "thepioneerwoman.com"

    def instructions(self):
        instructions = self.schema.instructions()
        if instructions == "":
            instructions_element = self.soup.select_one(".directions")
            if instructions_element:
                instructions = instructions_element.get_text(separator="\n")
        return instructions
