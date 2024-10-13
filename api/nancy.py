from meta_ai_api import MetaAI

class Nancy:
    def __init__(self):
        self.name = "Nancy"
        # self.proxy = { 
        # 'http': '47.178.24.220:80',
        # 'https': '198.24.187.93:8001'
        # }
        # self.meta = MetaAI(proxy=self.proxy)
        self.meta = MetaAI()
        self.meta.prompt("remember your name is Nancy")

    def prompt(self, msg):
        return self.meta.prompt(msg)['message']
