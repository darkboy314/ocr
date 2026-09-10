import translate


class Canton:
    def __init__(self, to_lang):
        self.translator = translate.Translator(to_lang=to_lang, from_lang="zh")


    def start_translate(self, string:list, source=None) -> list:
        key = ""
        res = []
        translator = self.translator
        
        for str in string:
            translation = translator.translate(str)
            res.append(translation)
                    
        return res