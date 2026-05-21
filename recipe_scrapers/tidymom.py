from ._abstract import AbstractScraper


class TidyMom(AbstractScraper):

    @classmethod
    def host(cls):
        return "tidymom.net"
