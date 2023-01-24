class BaseCase:

    def __init__(self, name: str):
        self._name = name

    def __str__(self):
        return self._name
