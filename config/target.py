
class Target:

    def __init__(
            self,
            bank_name: str,
            type_main: str,
            type_next: str,
            url: str,
            selectors: list = None
    ):
        self._bank_name = bank_name
        self._type_main = type_main
        self._type_next = type_next
        self._url = url
        self._selectors = selectors

    def __repr__(self):
        return f"【bank_name: {self._bank_name}, type_main: {self._type_main}, url: {self._url}】"

    def do_dump(self):
        elements = [one for one in dir(self) if not (one.startswith('__') or one.startswith('_') or one.startswith('do_'))]
        data = {}
        for name in elements:
            data[name] = getattr(self, name, None)
        return data

    @property
    def url(self):
        return self._url

    @url.setter
    def url(self, value):
        self._url = value

    @property
    def bank_name(self):
        return self._bank_name

    @bank_name.setter
    def bank_name(self, value):
        self._bank_name = value

    @property
    def type_main(self):
        return self._type_main

    @type_main.setter
    def type_main(self, value):
        self._type_main = value

    @property
    def type_next(self):
        return self._type_next

    @type_next.setter
    def type_next(self, value):
        self._type_next = value

    @property
    def selectors(self):
        return self._selectors

    @selectors.setter
    def selectors(self, value):
        self._selectors = value

