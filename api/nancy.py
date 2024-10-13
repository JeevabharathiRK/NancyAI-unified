from meta_ai_api import MetaAI

class Nancy:
    def __init__(self):
        self.name = "Nancy"
        self.meta = MetaAI()
        self.meta.prompt("remember your name is Nancy")

    def prompt(self, msg):
        return self.meta.prompt(msg)['message']