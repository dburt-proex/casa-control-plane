from collections import deque
from casa.policy_loader import load_policy



class DriftMonitor:
    def __init__(self):
        policy = load_policy()
        self.window_size = policy["drift_window"]
        self.threshold = policy["drift_threshold"]
        self.history = deque(maxlen=self.window_size)

    def add_score(self, score: float):
        self.history.append(score)

    def drift_detected(self) -> bool:
        if len(self.history) < self.window_size:
            return False

        avg = sum(self.history) / len(self.history)
        latest = self.history[-1]

        return abs(latest - avg) > self.threshold