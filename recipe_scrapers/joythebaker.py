from __future__ import annotations

from recipe_scrapers._exceptions import ElementNotFoundInHtml
from recipe_scrapers._grouping_utils import group_ingredients
from recipe_scrapers._utils import get_minutes

from ._abstract import AbstractScraper


class JoyTheBaker(AbstractScraper):
    @classmethod
    def host(cls):
        return "joythebaker.com"

    def total_time(self):
        recipe_time = self.soup.find("span", {"class": "tasty-recipes-total-time"})
        try:
            return get_minutes(recipe_time)
        except ElementNotFoundInHtml:
            return None

    def ingredient_groups(self):
        return group_ingredients(
            self.ingredients(),
            self.soup,
            ".tasty-recipes-ingredients-body p",
            ".tasty-recipes-ingredients-body ul li",
        )
