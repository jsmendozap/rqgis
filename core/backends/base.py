class BaseBackend:
    def __init__(self, args, cwd):
        self.args = args
        self.cwd = cwd
        self.process = None
        self.stdin = None
        self.stdout = None

    def start(self): 
        raise NotImplementedError

    def terminate(self):
        raise NotImplementedError
    
    def readline(self):
        raise NotImplementedError
    
    def wait(self, timeout=None):
        raise NotImplementedError
    
    def kill(self):
        raise NotImplementedError
    
    def is_running(self):
        return self.process is not None and self.process.poll() is None