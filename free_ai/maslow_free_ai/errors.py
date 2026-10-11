class FreeAIError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code, self.message = code, message

    def as_dict(self):
        return {"code": self.code, "message": self.message}
