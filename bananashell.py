#!/usr/bin/env python3

from os import read, write
import os, sys, tty, termios

class BananaShell(object):
    def __init__(self, readline=None):
        BananaShell.validate_python_version()
        self.env = os.environ.copy()
        self.readline = readline if readline else ReadlineFunctor()
        self.builtins = {}
        self.functions = {}

        self.configure_builtins()
    
    @staticmethod
    def validate_python_version():
        PY_MAJOR_VERSION = sys.version_info.major
        PY_MINOR_VERSION = sys.version_info.minor
    
        if not (PY_MAJOR_VERSION == 3 and PY_MINOR_VERSION >= 8):
            msg = f'Your python version is {PY_MAJOR_VERSION}.{PY_MINOR_VERSION}, please update to at least python 3.8!\n\n'
            raise InvalidPythonException(msg)

    def configure_builtins(self):
        for builtin in filter(lambda builtin: '_cmd_' in builtin, self.__dir__()):
            self.builtins[builtin.split('_cmd_')[1]] = eval('self.' + builtin)
        
        
    def _cmd_echo(self, args):
        line = ' '.join(args)
        write(1, (line+'\n\n').encode())
        sys.stdout.flush()

    def _cmd_def(self, args):
        if args[2] == '{':
            readline = ReadlineFunctor()
            while (line := readline('')) not in (readline.eof, '}\n'):
                if line == '\n':
                    continue
                name = args[1]
                cmd = Command(line)
                self.functions[name] = self.functions[name] + [cmd] if name in self.functions else [cmd]

    def parse_function(self, func):
        for cmd in func:
            self.run(cmd)
                
    def run(self, cmd):
        if cmd.in_env():
            self.exec(cmd)
            return
            
        try:
            self.parse_function(self.functions[cmd.name])
            return
        except KeyError:
            pass
        except IndexError:
            pass
            
        try:
            self.builtins[cmd.name](cmd.args)
        except KeyError:
            print(f'BananaShell: command not found: \'{cmd}\'')
        
        
    def exec(self, cmd):
        '''Fork and replace process in memory.
        Wrapper around exec libc call (for preprocessing hooks).'''
        
        # Try to execute binary
        if not os.fork():
            try:
                os.execve(cmd.in_env(), cmd.args, os.environ)
            except OSError as e:
                print('OSError:', e)
            sys.exit(1)
        
        try:
            os.wait()
        except ChildProcessError:
            pass
        
        
    def __call__(self):
        while (line := self.readline(f'[{os.getcwd()}]\n$ ')) not in (self.readline.eof, 'exit\n'):
            if line == '\n':
                print()
                continue
            self.run(Command(line))
            print()


class Command(object):
    def __init__(self, line):
        line = self.sanitize(line)
        tokens = line.split('\n')[0].split(' ')
        self.name = tokens[0]
        self.args = tokens

    def in_env(self):
        try:
            for base in reversed(os.environ['PATH'].split(':')):
                if self.name in os.listdir(base):
                    return base + '/' + self.name
        except KeyError:
            pass
        return None

    def can_execute(self):
        try:
            owner, group, mask = self.stat()
            exec_mask = [x % 2 for x in mask]
            if exec_mask[2]:
                return True
            if group in os.getgroups() and exec_mask[1]:
                return True
            if owner == os.getuid() and exec_mask[0]:
                return True
        except Exception:
            pass
        return False

    def stat(self):
        stat = os.stat(self.in_env())
        owner = stat.st_uid
        group = stat.st_gid
        mask = [int(x) for x in oct(stat.st_mode)[4:]]
        return owner, group, mask

    def sanitize(self, line):
        for invalid in ('\t'):
            line = ''.join(line.split(invalid))
        return line

    def __repr__(self):
        return ' '.join(self.args)

    def __str__(self):
        return repr(self)
        
                
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
