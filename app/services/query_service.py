def extract_keywords(message: str):

    stop_words = {
        "bir",
        "ve",
        "ile",
        "için",
        "istiyorum",
        "arıyorum",
        "lazım",
        "bana",
        "göster",
        "öner",
        "olan",
        "var",
        "mı",
        "mi",
        "mu",
        "mü"
    }

    words = []

    for word in message.lower().split():

        word = word.strip()

        if len(word) < 2:
            continue

        if word in stop_words:
            continue

        words.append(word)

    return words