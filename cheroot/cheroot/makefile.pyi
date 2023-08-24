import io

SOCK_WRITE_BLOCKSIZE: int

class BufferedWriter(io.BufferedWriter):
    def write(self, b): ...

class MakeFile_PY2:
    bytes_read: int
    bytes_written: int
    def __init__(self, *args, **kwargs) -> None: ...
    def write(self, data) -> None: ...
    def send(self, data): ...
    def flush(self) -> None: ...
    def recv(self, size): ...
    def read(self, size: int = ...): ...
    def readline(self, size: int = ...): ...
    def has_data(self): ...

class StreamReader(io.BufferedReader):
    bytes_read: int
    def __init__(self, sock, mode: str = ..., bufsize=...) -> None: ...
    def read(self, *args, **kwargs): ...
    def has_data(self): ...

class StreamWriter(BufferedWriter):
    bytes_written: int
    def __init__(self, sock, mode: str = ..., bufsize=...) -> None: ...
    def write(self, val, *args, **kwargs): ...

def MakeFile(sock, mode: str = ..., bufsize=...): ...
