import pygame
import sys

from threading import Thread
from subprocess import Popen, PIPE
from queue import Queue, Empty

from engine.lang import BaseSyntaxHighlighter
from .buffer_component import BufferViewportComponent
from .buffer_mode import BufferMode


class TerminalViewportComponent(BufferViewportComponent):
    def __init__(self, app, shell_arguments):
        super().__init__(app)
        print(shell_arguments)
        self.shell_arguments = shell_arguments
        self.pipe = Popen(
            self.shell_arguments,
            stdout=PIPE,
            stderr=PIPE,
            # stdin=PIPE,
            # shell=True,
            bufsize=1
        )
        self.read_queue = Queue()
        self.buffer_id = f"terminal_process_{self.pipe.pid}"
        self.output = ""
        self.exit_code = -1

        self.threads = [
            Thread(target=self.__enqueue_output, args=(self.pipe.stdout,)),
            Thread(target=self.__enqueue_output, args=(self.pipe.stderr,)),
        ]

        for thread in self.threads:
            thread.daemon = True
            thread.start()

        self.syntax_highlighter = BaseSyntaxHighlighter()
        # self.token_lines = self.syntax_highlighter.parse_code(self.base_lines)
        # TODO: implement a better way to execute shell commands
        # output = os.popen(' '.join(args)).read()
        # output = output.strip()
        # for i in output.split("\n"):
        #     print(i)

    def __enqueue_output(self, out):
        for c in iter(lambda: out.read1(), b""):
            self.read_queue.put(c)
        out.close()

    def cleanup(self):
        print(f"Terminating process {self.pipe.pid}...")
        self.pipe.terminate()
        return super().cleanup()

    def update(self, dt):
        try:
            self.output += self.read_queue.get_nowait().decode("utf-8")

            self.base_lines = self.output.split("\n")
            self.token_lines = self.generate_tokens()
        except Empty:
            # Hasn't got any output yet
            ...

        try:
            code = self.pipe.wait(0)
            if self.exit_code == -1:
                self.exit_code = code
                self.output += f"\n\nProcess finished with exit code {self.exit_code}"
                self.base_lines = self.output.split("\n")
                self.token_lines = self.generate_tokens()
        except:
            # The process hasn't finished yet
            ...

        if self.base_lines and self.get_mode() == BufferMode.INSERT:
            splitted_lines = self.output.split("\n")
            self.caret_position[0] = max(self.caret_position[0], len(splitted_lines[-1]))
            self.caret_position[1] = len(splitted_lines) - 1

        return super().update(dt)

    def update_buffer(self, key, unicode, modifier, skip_letter_insert=False, is_text_updated=False):
        if self.base_lines and key == pygame.K_RETURN and self.get_mode() == BufferMode.INSERT:
            self.output += "\n"
            splitted_lines = self.output.split("\n")
            buffer = self.base_lines[-1][len(splitted_lines[-1]) - 1:]
            print(buffer)
            self.pipe.stdin.write((buffer + "\n").encode())

        return super().update_buffer(key, unicode, modifier, skip_letter_insert, is_text_updated)

    def generate_tokens(self):
        return self.syntax_highlighter.parse_code(self.base_lines)
