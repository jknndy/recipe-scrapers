from ._abstract import AbstractScraper


class IowaGirlEats(AbstractScraper):

    @classmethod
    def host(cls):
        return "iowagirleats.com"

    def author(self):
        return self.soup.find("meta", {"name": "author"})["content"]

    def instructions(self):
        instructions = self.soup.find_all(
            "div", {"class": "wprm-recipe-instruction-text"}
        )
        instruction_list = []
        for instruction in instructions:
            instruction_list.append(instruction.get_text().strip())
        return "\n".join(instruction_list)
