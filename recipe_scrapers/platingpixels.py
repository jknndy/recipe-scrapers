from ._abstract import AbstractScraper


class PlatingPixels(AbstractScraper):

    @classmethod
    def host(cls):
        return "platingpixels.com"

    def author(self):
        author_tag = self.soup.find("strong", string="Author:")
        if author_tag and author_tag.next_sibling:
            return author_tag.next_sibling.strip()
        return "Plating Pixels"
