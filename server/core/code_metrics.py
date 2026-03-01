import pandas as pd

class CodeMetricsExtractor:
    VALID_EXTS = {'.java', '.py', '.cpp', '.cc', '.cxx', '.hpp', '.h', '.hh'}
    def is_valid_file(self, fpath: str) -> bool:
        return any(fpath.endswith(ext) for ext in self.VALID_EXTS)
