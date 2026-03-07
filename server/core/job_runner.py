class JobAbortedError(Exception):
    pass

class JobRunner:
    def __init__(self, pipe, hist=None, workers: int = 2):
        self.pipe = pipe
        self.hist = hist
        self.workers = workers
