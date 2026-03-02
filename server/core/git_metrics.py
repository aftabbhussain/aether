import pandas as pd

class GitProcessMetrics:
    def __init__(self, max_hist: int = 200, window_days: int = 90):
        self.max_hist = max_hist
        self.window_days = window_days
