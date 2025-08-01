from ._abstract import AbstractScraper
from ._wprm import WPRMMixin


class AmazingRibs(WPRMMixin, AbstractScraper):
    @classmethod
    def host(cls):
        return "amazingribs.com"

    def equipment(self):
        equipment_items = [
            normalize_string(e.get_text())
            for e in self.soup.find_all("div", class_="wprm-recipe-equipment-name")
        ]
        return sorted(get_equipment(equipment_items))
