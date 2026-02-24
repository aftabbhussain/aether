import os

class AppConfig:
    def __init__(self):
        self.host = os.getenv('HOST', '127.0.0.1')
        self.port = int(os.getenv('PORT', '8000'))

cfg = AppConfig()
