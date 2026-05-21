from ._abstract import AbstractScraper


class KitchenDreaming(AbstractScraper):

    @classmethod
    def host(cls):
        return "kitchendreaming.com"
