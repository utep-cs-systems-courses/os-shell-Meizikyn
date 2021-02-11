#!/usr/bin/env python3

from os import read, write
import os, sys, tty, termios

class BananaShell(object):
    def __init__(self, readline=None):
        BananaShell.validate_python_version()
        self.env = os.environ.copy()
        self.readline = readline if readline else ReadlineFunctor()

        self.builtins_map = {}
        for command in filter(lambda cmd: '_cmd_' in cmd, self.__dict__.copy()):
            self.builtins_map[command.split('_cmd_')[1]] = self.__dict__[command]
    
    @staticmethod
    def validate_python_version():
        PY_MAJOR_VERSION = sys.version_info.major
        PY_MINOR_VERSION = sys.version_info.minor
    
        if not (PY_MAJOR_VERSION == 3 and PY_MINOR_VERSION >= 8):
            msg = f'Your python version is {PY_MAJOR_VERSION}.{PY_MINOR_VERSION}, please update to at least python 3.8!\n\n'
            raise InvalidPythonException(msg)

    def _cmd_echo(self, *args):
        line = ' '.join(args)
        write(1, (line+'\n\n').encode())
        sys.stdout.flush()
    
    def fork_and_exec(self, command, args):
        '''Fork and replace process in memory.
        Wrapper around exec libc call (for preprocessing hooks).
        libc handles PATH for us here.'''
        return self._fork_and_exec(command, args)

    def _fork_and_exec(self, command, args):
        if not os.fork():
            try:
                os.execve(command, args, self.env)
            except OSError:
                sys.exit(1)
            except ValueError:
                sys.exit(1)
        try:
            return os.wait()
        except ChildProcessError:
            return None

    def __call__(self):
        while (line := self.readline(f'[{os.getcwd()}]\n$ ')) not in (self.readline.eof, 'exit\n'):
            if line == '\n':
                print()
                continue
            
            tokens = line.split('\n')[0].split(' ')
            command = tokens[0]

            self.fork_and_exec(command, tokens)

            try:
                self.builtins_map[command](*arguments)
            except KeyError:
                print(f'BananaShell: command not found: \'{command}\'\n')

class ReadlineFunctor(object):
    '''A *very* primitive readline implementation using
    a functor to simulate static allocation in a C module.'''
    def __init__(self, max_bytes=4, eof='', include_newline=True):
        self.exclusion_index = 0 if include_newline else 1
        self.max_bytes = max_bytes
        self.eof   = eof
        self.limit = 0
        self.idx   = 0
        self.buf   = ''

    def getchar(self):
        '''Construct a buffer from stdin, returning one character
        at a time.'''
        if self.idx == self.limit:
            self.buf   += read(0, self.max_bytes).decode()
            self.limit += len(self.buf[self.idx:])
        if not self.limit:
            return self.eof
        c = self.buf[self.idx]
        self.idx += 1
        return c

    def getline(self):
        '''Flush the character buffer and return the line.'''
        s = self.buf[:self.idx - self.exclusion_index]
        self.buf = self.buf[self.idx:]
        self.limit -= self.idx
        self.idx = 0
        return s
    
    def __call__(self, prompt=''):
        '''Simulate a call to readline.'''
        write(self.iomap[1], prompt.encode())
        while (c := self.getchar()) not in ('\n', self.eof):
            pass
        return self.getline()


class AntiBuffer(object):
    def __init__(self):
        pass

    def __enter__(self):
        self.termconfig = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin)
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.termconfig)
        
        
        
    
class InvalidPythonException(Exception):
    def __init__(*args, **kwargs):
        super.__init__(*args, **kwargs)

if __name__ == '__main__':
    BananaShell()()
