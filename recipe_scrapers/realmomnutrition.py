from ._abstract import AbstractScraper


class RealMomNutrition(AbstractScraper):

    @classmethod
    def host(cls):
        return "realmomnutrition.com"

    def equipment(self):
        return [
            item.get_text(strip=True)
            for item in self.soup.select(
                "ul.mv-create-products-list div.mv-create-products-product-name"
            )
        ]
