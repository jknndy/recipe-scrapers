from ._abstract import AbstractScraper


class BlueJeanChef(AbstractScraper):

    @classmethod
    def host(cls):
        return "bluejeanchef.com"
