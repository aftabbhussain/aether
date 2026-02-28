from pathlib import Path

class GitClient:
    def __init__(self, root_dir=None, ttl: int = 300):
        self.root_dir = Path(root_dir or 'temp_repos')
        self.ttl = ttl
