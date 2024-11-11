# IF things in this file continue get messy (I'd say 300+ lines) it may be time to
# find a package that parses https://schema.org/Recipe properly (or create one ourselves).
from __future__ import annotations

from itertools import chain

import extruct

from recipe_scrapers.settings import settings

from ._exceptions import SchemaOrgException
from ._utils import (
    csv_to_tags,
    format_diet_name,
    get_minutes,
    get_yields,
    normalize_string,
)

SCHEMA_ORG_HOST = "schema.org"

SYNTAXES = ["json-ld", "microdata"]


class SchemaOrg:
    @staticmethod
    def _contains_schematype(item, schematype):
        itemtype = item.get("@type", "")
        itemtypes = itemtype if isinstance(itemtype, list) else [itemtype]
        return schematype.lower() in "\n".join(itemtypes).lower()

    def _find_entity(self, item, schematype):
        if self._contains_schematype(item, schematype):
            return item
        for graph in item.get("@graph", []):
            for node in graph if isinstance(graph, list) else [graph]:
                if self._contains_schematype(node, schematype):
                    return node

    def __init__(self, page_data):
        self.format = None
        self.data = {}
        self.people = {}
        self.ratingsdata = {}
        self.website_name = None

        # Extract structured data
        extracted_data = self._extract_structured_data(page_data)

        # Extract website data
        self._extract_website_data(extracted_data)

        # Extract person references
        self._extract_person_references(extracted_data)

        # Extract ratings data
        self._extract_ratings_data(extracted_data)

        # Extract recipe data
        self._extract_recipe_data(extracted_data)

    def _extract_structured_data(self, page_data):
        return extruct.extract(
            page_data,
            syntaxes=SYNTAXES,
            errors="log" if settings.LOG_LEVEL <= 10 else "ignore",
            uniform=True,
        )

    def _extract_website_data(self, data):
        for syntax in SYNTAXES:
            for item in data.get(syntax, []):
                if website := self._find_entity(item, "WebSite"):
                    self.website_name = website.get("name")
                    return

    def _extract_person_references(self, data):
        for syntax in SYNTAXES:
            for item in data.get(syntax, []):
                if person := self._find_entity(item, "Person"):
                    key = person.get("@id") or person.get("url")
                    if key:
                        self.people[key] = person

    def _extract_ratings_data(self, data):
        for syntax in SYNTAXES:
            for item in data.get(syntax, []):
                if rating := self._find_entity(item, "AggregateRating"):
                    rating_id = rating.get("@id")
                    if rating_id:
                        self.ratingsdata[rating_id] = rating

    def _extract_recipe_data(self, data):
        for syntax in SYNTAXES:
            syntax_data = data.get(syntax, [])
            try:
                index = next(
                    i
                    for i, x in enumerate(syntax_data)
                    if x.get("@type", "") == "Recipe"
                )
                syntax_data.insert(0, syntax_data.pop(index))
            except StopIteration:
                pass

            for item in syntax_data:
                if SCHEMA_ORG_HOST not in item.get("@context", ""):
                    continue

                if recipe := self._find_entity(item, "Recipe"):
                    self.format = syntax
                    self.data = recipe
                    return

                if self._contains_schematype(item, "WebPage"):
                    main_entity = item.get("mainEntity", {})
                    if self._contains_schematype(main_entity, "Recipe"):
                        self.format = syntax
                        self.data = main_entity
                        return

    def site_name(self):
        if not self.website_name:
            raise SchemaOrgException("Site name not found in SchemaOrg")

        return normalize_string(self.website_name)

    def language(self):
        return self.data.get("inLanguage") or self.data.get("language")

    def title(self):
        return normalize_string(self.data.get("name"))

    def category(self):
        category = self.data.get("recipeCategory")
        return ",".join(category) if isinstance(category, list) else category

    def author(self):
        author = self.data.get("author") or self.data.get("Author")
        if isinstance(author, list) and author and isinstance(author[0], dict):
            author = author[0]
        if isinstance(author, dict):
            author_key = author.get("@id") or author.get("url")
            if author_key and author_key in self.people:
                author = self.people[author_key]
            author = author.get("name")
        return author.strip() if author else None

    def _read_duration_field(self, k: str) -> int | None:
        v = self.data.get(k)
        if v is None:
            return None
        if isinstance(v, str):
            return get_minutes(v)
        # Workaround: strictly speaking schema.org does not provide for minValue and maxValue properties on objects of type Duration; they are however present on objects with type QuantitativeValue
        # Refs:
        #  - https://schema.org/Duration
        #  - https://schema.org/QuantitativeValue
        if isinstance(v, dict) and v.get("maxValue"):
            return get_minutes(v["maxValue"])
        return None

    def total_time(self):
        if not (self.data.keys() & {"totalTime", "prepTime", "cookTime"}):
            raise SchemaOrgException("Cooking time information not found in SchemaOrg")

        total_time = self._read_duration_field("totalTime")
        if total_time:
            return total_time

        prep_time = self._read_duration_field("prepTime") or 0
        cook_time = self._read_duration_field("cookTime") or 0
        return prep_time + cook_time if prep_time or cook_time else None

    def cook_time(self):
        if not (self.data.keys() & {"cookTime"}):
            raise SchemaOrgException("Cooktime information not found in SchemaOrg")
        return self._read_duration_field("cookTime")

    def prep_time(self):
        if "prepTime" not in self.data:
            raise SchemaOrgException("Preptime information not found in SchemaOrg")
        return self._read_duration_field("prepTime")

    def yields(self):
        if not (self.data.keys() & {"recipeYield", "yield"}):
            raise SchemaOrgException("Servings information not found in SchemaOrg")
        yield_data = self.data.get("recipeYield") or self.data.get("yield")
        if isinstance(yield_data, list):
            yield_data = yield_data[0]
        return get_yields(str(yield_data)) if yield_data else None

    def image(self):
        image = self.data.get("image")

        if image is None:
            raise SchemaOrgException("Image not found in SchemaOrg")

        if isinstance(image, list):
            # Could contain a dict
            image = image[0]

        if isinstance(image, dict):
            image = image.get("url")

        if "http://" not in image and "https://" not in image:
            # Some sites use relative image paths;
            # prefer generic image retrieval code in those cases.
            image = ""

        return image

    def ingredients(self):
        ingredients = (
            self.data.get("recipeIngredient") or self.data.get("ingredients") or []
        )

        if ingredients and isinstance(ingredients[0], list):
            ingredients = list(chain.from_iterable(ingredients))

        if isinstance(ingredients, str):
            ingredients = [ingredients]

        return [
            normalize_string(ingredient) for ingredient in ingredients if ingredient
        ]

    def nutrients(self):
        nutrients = self.data.get("nutrition", {})
        return {
            normalize_string(key): normalize_string(str(val))
            for key, val in nutrients.items()
            if key and not key.startswith("@") and val
        }

    def _extract_howto_instructions_text(self, schema_item):
        instructions_gist = []
        if isinstance(schema_item, str):
            instructions_gist.append(schema_item)
        elif schema_item.get("@type") == "HowToStep":
            if schema_item.get("name") and not schema_item.get("text").startswith(
                schema_item.get("name").rstrip(".")
            ):
                instructions_gist.append(schema_item.get("name"))
            if schema_item.get("itemListElement"):
                schema_item = schema_item.get("itemListElement")
            instructions_gist.append(schema_item.get("text"))
        elif schema_item.get("@type") == "HowToSection":
            name = schema_item.get("name") or schema_item.get("Name")
            if name:
                instructions_gist.append(name)
            for item in schema_item.get("itemListElement"):
                instructions_gist.extend(self._extract_howto_instructions_text(item))
        return instructions_gist

    def instructions(self):
        instructions = self.data.get("recipeInstructions") or ""

        if isinstance(instructions, list) and isinstance(instructions[0], list):
            instructions = list(chain.from_iterable(instructions))

        if isinstance(instructions, dict):
            instructions = instructions.get("itemListElement")

        if isinstance(instructions, list):
            instructions_gist = []
            for schema_instruction_item in instructions:
                instructions_gist.extend(
                    self._extract_howto_instructions_text(schema_instruction_item)
                )

            return "\n".join(
                normalize_string(instruction) for instruction in instructions_gist
            )

        return instructions

    def ratings(self):
        ratings = self.data.get("aggregateRating") or self._find_entity(
            self.data, "AggregateRating"
        )
        if isinstance(ratings, dict):
            rating_id = ratings.get("@id")
            if rating_id and rating_id in self.ratingsdata:
                ratings = self.ratingsdata[rating_id]
            ratings = ratings.get("ratingValue")
        if ratings:
            return round(float(ratings), 2)
        raise SchemaOrgException("No ratingValue in SchemaOrg.")

    def ratings_count(self):
        ratings = self.data.get("aggregateRating") or self._find_entity(
            self.data, "AggregateRating"
        )
        if isinstance(ratings, dict):
            rating_id = ratings.get("@id")
            if rating_id:
                ratings = self.ratingsdata.get(rating_id, ratings)
            ratings = ratings.get("ratingCount") or ratings.get("reviewCount")
        if ratings:
            return int(float(ratings)) if float(ratings) != 0 else None
        raise SchemaOrgException("No ratingCount in SchemaOrg.")

    def cuisine(self):
        cuisine = self.data.get("recipeCuisine")
        if cuisine is None:
            raise SchemaOrgException("No cuisine data in SchemaOrg.")
        return ",".join(cuisine) if isinstance(cuisine, list) else cuisine

    def description(self):
        description = self.data.get("description")
        if description is None:
            raise SchemaOrgException("No description data in SchemaOrg.")
        if isinstance(description, list):
            description = description[0]
        return normalize_string(description)

    def cooking_method(self):
        cooking_method = self.data.get("cookingMethod")
        if cooking_method is None:
            raise SchemaOrgException("No cooking method data in SchemaOrg")
        if isinstance(cooking_method, list):
            cooking_method = cooking_method[0]
        return normalize_string(cooking_method)

    def keywords(self):
        keywords = self.data.get("keywords")
        if keywords is None:
            raise SchemaOrgException("No keywords data in SchemaOrg")
        if isinstance(keywords, list):
            keywords = ", ".join(keywords)
        keywords = normalize_string(keywords)
        return csv_to_tags(keywords)

    def dietary_restrictions(self):
        dietary_restrictions = self.data.get("suitableForDiet")
        if dietary_restrictions is None:
            raise SchemaOrgException("No dietary restrictions data in SchemaOrg.")
        if not isinstance(dietary_restrictions, list):
            dietary_restrictions = [dietary_restrictions]

        formatted_diets = [format_diet_name(diet) for diet in dietary_restrictions]
        formatted_diets = ", ".join(formatted_diets)
        return csv_to_tags(formatted_diets)
