from __future__ import annotations


class IntelligenceError(Exception):
    def __init__(self, code: str, message: str, retryable: bool = False):
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable


class InvalidIntelligenceInput(IntelligenceError):
    def __init__(self, code: str, message: str):
        super().__init__(code, message, False)


class SubmissionNotFound(IntelligenceError):
    def __init__(self):
        super().__init__("submission_not_found", "面经提交不存在", False)


class InvalidSubmissionAction(IntelligenceError):
    pass
