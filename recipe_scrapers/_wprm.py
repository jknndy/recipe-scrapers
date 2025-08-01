from ._utils import get_equipment

class WPRMMixin:
    """Helper mixin for sites using the WP Recipe Maker plugin."""

    def equipment(self):
        equipment_items = [
            equip.get_text().rstrip("*").strip()
            for equip in self.soup.find_all("div", class_="wprm-recipe-equipment-name")
            if equip.get_text()
        ]
        return get_equipment(equipment_items)
