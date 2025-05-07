LANGUAGES = {
    "en": "English 🇬🇧",
    "uk": "Ukrainian 🇺🇦",
    "da": "Dansk 🇩🇰",
    "de": "Deutsch 🇩🇪",
    "es": "Español 🇪🇸",
    "pl": "Polski 🇵🇱",
    "tr": "Türkçe 🇹🇷",
    "kl": "Kalaallisut 🇬🇱"
}

MESSAGES = {
    "greeting": {
        "en": "Welcome, {name}! You are authorized.",
        "uk": "Вітаємо, {name}! Ви авторизовані.",
        "da": "Velkommen, {name}! Du er godkendt.",
        "de": "Willkommen, {name}! Sie sind autorisiert.",
        "es": "¡Bienvenido, {name}! Estás autorizado.",
        "pl": "Witamy, {name}! Jesteś autoryzowany.",
        "kl": "Tikilluarit, {name}! Akuersineqarpoq.",
        "tr": "Hoş geldiniz, {name}! Yetkilisiniz."
    },
    "invalid_name": {
        "en": "Invalid name or surname.",
        "uk": "Невалідне ім'я або прізвище.",
        "da": "Ugyldigt navn eller efternavn.",
        "de": "Ungültiger Vor- oder Nachname.",
        "es": "Nombre o apellido inválido.",
        "pl": "Nieprawidłowe imię lub nazwisko.",
        "kl": "Ateq nalunaarsorneqarsinnaanngilaq.",
        "tr": "Geçersiz ad veya soyad."
    },
    "choose_language": {
        "en": "Choose your language:",
        "uk": "Оберіть мову:",
        "da": "Vælg dit sprog:",
        "de": "Wähle deine Sprache:",
        "es": "Elige tu idioma:",
        "pl": "Wybierz swój język:",
        "kl": "Oqaasissaq toqqaruk:",
        "tr": "Dilini seç:"
    },
    "language_updated": {
        "en": "Language set to English.",
        "uk": "Мову змінено на українську.",
        "da": "Sprog ændret til dansk.",
        "de": "Sprache wurde auf Deutsch geändert.",
        "es": "Idioma cambiado a español.",
        "pl": "Język zmieniono na polski.",
        "kl": "Oqaasissaq kalaallisut pilersinneqarpoq.",
        "tr": "Dil Türkçe olarak ayarlandı."
    }
}


def get_message(key, lang) -> str:
    return MESSAGES.get(key, {}).get(lang, MESSAGES[key]["en"])
