from collections import deque, defaultdict
import threading

class FixedWindowRateLimiter:
    """
    No more than R requests over the last T seconds

    Design 1:
        For each window(round to the closest nearly 60s),
            track the counts within that window
        Update window periodically
        Pros: Easy to implement
        Cons: Not accurate


    Design 2A:
        Real window Log
        Store <ClientId, Deque<Timestamp>
        Pros: Very accurate, Easy to Extend for more requirments
        Cons: Memory heavy + Worst case: High qps needs to cleanup many logs

    Design 2B:
        Sliding window counter -- approximation
        Store <ClientId, (CurrentWindowStart, CurrentWindowCnt, PrevWindowStart, PrevWindowCnt)>
        Weighted Average to approximate
        Pros: Accurate enough + Efficient
        Cons: Still can't handle bursty traffic

    Design 2C:
        Token Buckets
        Each client has:
            capacity (max tokens)
            refillRate (tokens per second)
            currentTokens
            lastRefillTimestamp
        On each request, refill tokens → then consume one token if possible.
        Pros: Very accurate, smooth bursts, O(1) per request, easy to scale

    """
    def __init__(self, max_requests, window_size):
        self.max_requests = max_requests
        self.window_size = window_size

        self.request_logs = defaultdict(deque)

    def allowRequest(self, clientId, curr_time):

        # update
        while self.request_logs[clientId] and (curr_time - self.request_logs[clientId][0]) >= self.window_size:
            self.request_logs[clientId].popleft()

        # check validity
        valid = len(self.request_logs[clientId]) < self.max_requests

        # update the latest request
        if valid:
            self.request_logs[clientId].append(curr_time)
        return valid


def test_basic_allow_and_deny():
    rl = FixedWindowRateLimiter(2, 2)
    assert rl.allowRequest(1, 1) == True
    assert rl.allowRequest(1, 2) == True
    assert rl.allowRequest(1, 2) == False
    assert rl.allowRequest(1, 3) == True


def test_cleanup_after_window():
    rl = FixedWindowRateLimiter(2, 5)
    assert rl.allowRequest("A", 1)
    assert rl.allowRequest("A", 2)
    assert rl.allowRequest("A", 7)  # cleanup 1,2 → window fully expired

def test_multiple_clients():
    rl = FixedWindowRateLimiter(1, 2)
    assert rl.allowRequest("A", 1)
    assert rl.allowRequest("B", 1)

    assert rl.allowRequest("A", 1) == False
    assert rl.allowRequest("B", 1) == False


def test_exact_window_boundary():
    rl = FixedWindowRateLimiter(2, 10)

    rl.allowRequest("A", 1)
    rl.allowRequest("A", 2)

    # At t=11, old timestamps 1 and 2 should be expired
    assert rl.allowRequest("A", 11) == True


if __name__ == "__main__":
    test_basic_allow_and_deny()
    test_cleanup_after_window()
    test_multiple_clients()
    test_exact_window_boundary()
