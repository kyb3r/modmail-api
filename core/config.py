import json 
from box import Box

class Config:
    @staticmethod
    def from_json(fp):
        with open(fp) as f:
            cfg = Box(json.load(f))
        cfg.domain = None if cfg.development else cfg.domain
        return cfg