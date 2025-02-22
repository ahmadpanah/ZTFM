import time

class HybridLogicalClock:
    def __init__(self):
        self.logical = 0
        self.physical = time.time()

    def now(self) -> float:
        self.physical = max(self.physical, time.time())
        return self.physical + self.logical

    def update(self):
        self.logical += 1