
class Vocabulary:

    def __init__(
            self,
            name_english: str,
            name_chinese: str,
            phonetic: str,
            voice: str,
            status: str = 'undo'
    ):
        self._name_english = name_english
        self._name_chinese = name_chinese
        self._phonetic = phonetic
        self._voice = voice
        self._status = status

    def __repr__(self):
        return f"【name_english: {self._name_english}, phonetic: {self._phonetic}, name_chinese: {self._name_chinese}, voice: {self._voice}】"

    def do_dump(self):
        elements = [one for one in dir(self) if not (one.startswith('__') or one.startswith('_') or one.startswith('do_'))]
        data = {}
        for name in elements:
            data[name] = getattr(self, name, None)
        data['_id'] = self._name_english
        return data

    @property
    def name_english(self):
        return self._name_english

    @name_english.setter
    def name_english(self, value):
        self._name_english = value

    @property
    def name_chinese(self):
        return self._name_chinese

    @name_chinese.setter
    def name_chinese(self, value):
        self._name_chinese = value

    @property
    def phonetic(self):
        return self._phonetic

    @phonetic.setter
    def phonetic(self, value):
        self._phonetic = value

    @property
    def voice(self):
        return self._voice

    @voice.setter
    def voice(self, value):
        self._voice = value

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        self._status = value

