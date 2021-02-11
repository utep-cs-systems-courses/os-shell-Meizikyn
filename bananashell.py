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

        self.user_map = {
            'example_f': (('ls', '-la'), ('echo', 'look at me'))
        }
    
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

    def run_user_function(self, body):
        for tokens in body:
            command = tokens[0]
            self.attempt_exec(command, tokens)
        
        
    def attempt_exec(self, cmd, args):
        '''Fork and replace process in memory.
        Wrapper around exec libc call (for preprocessing hooks).
        libc handles PATH for us here.'''

        # Try to execute binary
        if not os.fork():
            try:
                os.execvpe(cmd, args, self.env)
            except OSError:
                pass

            try:
                self.run_user_function(self.user_map[cmd])
                sys.exit(0)
            except KeyError:
                pass
            
            try:
                self.builtins_map[cmd](*args)
                sys.exit(0)
            except KeyError:
                print(f'BananaShell: command not found: \'{cmd}\'')

            sys.exit(1)
        
        try:
            os.wait()
            print()
        except ChildProcessError:
            pass

    def __call__(self):
        while (line := self.readline(f'[{os.getcwd()}]\n$ ')) not in (self.readline.eof, 'exit\n'):
            if line == '\n':
                print()
                continue
            
            tokens = line.split('\n')[0].split(' ')
            while '' in tokens:
                tokens.remove('')
            command = tokens[0]
            
            self.attempt_exec(command, tokens)

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
        write(1, prompt.encode())
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
