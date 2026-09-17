import translate


def start_translate(
    string: list,
    from_lang: str = "zh",
    to_lang: str = "en",
    source=None
    ) -> list:
    key = ""
    res = []
    translator = translate.Translator(to_lang=to_lang, from_lang=from_lang)
    
    for str in string:
        translation = translator.translate(str)
        res.append(translation)
                
    return res