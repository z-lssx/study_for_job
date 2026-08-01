class JobQueueError(Exception):
    pass


class IdempotencyConflict(JobQueueError):
    pass


class JobNotFound(JobQueueError):
    pass


class InvalidManualRetry(JobQueueError):
    pass


class JobExecutionError(Exception):
    def __init__(self, code: str, message: str, retryable: bool):
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable


class RetryableJobError(JobExecutionError):
    def __init__(self, code: str, message: str):
        super().__init__(code, message, True)


class PermanentJobError(JobExecutionError):
    def __init__(self, code: str, message: str):
        super().__init__(code, message, False)
