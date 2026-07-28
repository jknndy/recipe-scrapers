import unittest
from unittest import mock

from recipe_scrapers._abstract import AbstractScraper


class _HtmlSelectorScraper(AbstractScraper):
    """Minimal scraper whose title/ingredients/instructions avoid SchemaOrg."""

    @classmethod
    def host(cls):
        return "lazy-schema.test"

    def title(self):
        return self.soup.find("h1").get_text(strip=True)

    def ingredients(self):
        return [li.get_text(strip=True) for li in self.soup.select(".ingredient")]

    def instructions(self):
        return "\n".join(
            li.get_text(strip=True) for li in self.soup.select(".instruction")
        )

    def category(self):
        return self.schema.category()

    def description(self):
        return self.schema.description()


HTML = """
<html>
  <body>
    <h1>Lazy Schema Soup</h1>
    <ul>
      <li class="ingredient">1 onion</li>
      <li class="ingredient">2 carrots</li>
    </ul>
    <ol>
      <li class="instruction">Chop vegetables</li>
      <li class="instruction">Cook gently</li>
    </ol>
  </body>
</html>
"""


class TestLazySchemaOrg(unittest.TestCase):
    def test_schema_constructed_lazily_and_cached(self):
        schema_instance = mock.Mock(name="SchemaOrgInstance")
        schema_instance.category.return_value = "Side"
        schema_instance.description.return_value = "A simple dish"

        schema_cls = mock.Mock(return_value=schema_instance)

        with mock.patch.object(_HtmlSelectorScraper, "_schema_cls", schema_cls):
            scraper = _HtmlSelectorScraper(HTML, "https://lazy-schema.test/recipe")

            schema_cls.assert_not_called()
            self.assertNotIn("schema", scraper.__dict__)

            self.assertEqual(scraper.title(), "Lazy Schema Soup")
            self.assertEqual(scraper.ingredients(), ["1 onion", "2 carrots"])
            self.assertEqual(
                scraper.instructions_list(), ["Chop vegetables", "Cook gently"]
            )
            schema_cls.assert_not_called()
            self.assertNotIn("schema", scraper.__dict__)

            self.assertEqual(scraper.category(), "Side")
            schema_cls.assert_called_once_with(HTML)
            self.assertIs(scraper.schema, schema_instance)

            self.assertEqual(scraper.description(), "A simple dish")
            schema_cls.assert_called_once_with(HTML)
            self.assertIs(scraper.schema, schema_instance)


if __name__ == "__main__":
    unittest.main()
