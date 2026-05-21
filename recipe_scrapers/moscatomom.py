from ._abstract import AbstractScraper


class MoscatoMom(AbstractScraper):

    @classmethod
    def host(cls):
        return "moscatomom.com"
