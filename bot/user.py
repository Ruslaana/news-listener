import re


class User:
    def __init__(self, user_id, first_name, last_name, language="uk", is_authenticated=False):
        self.user_id = user_id
        self.first_name = first_name
        self.last_name = last_name
        self.language = language
        self.is_authenticated = is_authenticated

    def validate_name(self):
        name_pattern = r"^[A-ZА-ЯІЇЄҐ][a-zа-яіїєґ']+$"
        return (
            re.match(name_pattern, self.first_name) and
            re.match(name_pattern, self.last_name)
        )

    def authenticate(self):
        self.is_authenticated = True
        return self.is_authenticated
