from ..shell.buffer_component import BufferToken

BASE_COLOR = (255, 255, 255)
STRING_LITERAL_COLOR = (190, 140, 100)
KEYWORD0_LITERAL_COLOR = (110, 110, 150)
KEYWORD1_LITERAL_COLOR = (190, 190, 100)
NUMBER_LITERAL_COLOR = (100, 190, 150)
COMMENT_COLOR = (130, 190, 100)


class BaseSyntaxHighlighter:
    def __init__(self):
        self.position = [0, 0]
        self.lines_of_code = []

    def reset_code(self, lines_of_code):
        self.position = [0, 0]
        self.lines_of_code = lines_of_code
    
    def prev_char(self):
        self.position[0] -= 1
        if self.position[0] < 0:
            self.position[0] = 0
            self.position[1] -= 1
            if self.position[1] < 0:
                self.position[1] = 0
            else:
                self.position[0] = len(self.lines_of_code[self.position[1]]) - 1
                if self.position[0] < 0:
                    self.position[0] = 0

    def next_char(self, step_further=True):
        if not self.lines_of_code[self.position[1]]:
            new_line = self.position[1] + 1 < len(self.lines_of_code)
            if step_further:
                self.position[1] += 1
            return "", self.position[1] >= len(self.lines_of_code) or (self.position[1] >= len(self.lines_of_code) and self.position[0] + 1 >= len(self.lines_of_code[self.position[1]])), new_line

        char = self.lines_of_code[self.position[1]][self.position[0]]
        is_new_line = False
        if step_further:
            self.position[0] += 1
            if self.position[0] >= len(self.lines_of_code[self.position[1]]):
                self.position[0] = 0
                self.position[1] += 1
                if self.position[1] >= len(self.lines_of_code):
                    return char, True, False
                is_new_line = True

        return char, self.position[1] >= len(self.lines_of_code) and self.position[0] + 1 >= len(self.lines_of_code[self.position[1]]), is_new_line

    def parse_code(self, lines_of_code):
        return [list(i) for i in lines_of_code]

    def parse_literal(self, checker, color, skip_last_character=False):
        tokens = []
        text, is_end, is_new_line = self.next_char()
        if is_new_line:
            tokens.append(BufferToken(text, color, is_new_line=True))
            text = ""
        elif is_end:
            tokens.append(BufferToken(text, color))
            return tokens, True
        while True:
            char, is_end, is_new_line = self.next_char()
            text += char
            if is_new_line:
                tokens.append(BufferToken(text, color, is_new_line=True))
                text = ""
            if is_end or checker(char):
                if skip_last_character and checker(char):
                    if is_new_line:
                        tokens[-1].value = tokens[-1].value[:-1]
                        tokens[-1].is_new_line = False
                    else:
                        text = text[:-1]
                    is_end = False
                    is_new_line = False
                    self.prev_char()
                break
        if text or is_end:
            tokens.append(BufferToken(text, color, is_new_line=is_new_line))
        return tokens, is_end

    def parse_singleline_comment(self, comment_sign=''):
        tokens = []
        text, is_end, is_new_line = self.next_char()
        text = comment_sign + text
        if is_new_line or is_end:
            tokens.append(BufferToken(text, COMMENT_COLOR, is_new_line=True))
            return tokens, is_end
        while True:
            char, is_end, is_new_line = self.next_char()
            text += char
            if is_new_line:
                tokens.append(BufferToken(text, COMMENT_COLOR, is_new_line=True))
                text = ""
            if is_end or is_new_line:
                break
        if text or is_end:
            tokens.append(BufferToken(text, COMMENT_COLOR, is_new_line=is_new_line))
        return tokens, is_end


def get_syntax_highlighter_for_filename(filename: str):
    from .c_syntax import CSyntaxHighlighter
    from .py_syntax import PySyntaxHighlighter
    from .json_syntax import JsonSyntaxHighlighter
    from .md_syntax import MarkdownSyntaxHighlighter

    if filename.endswith(".py"):
        return PySyntaxHighlighter(), "Python file"
    elif filename.endswith(".json"):
        return JsonSyntaxHighlighter(), "JSON file"
    elif filename.endswith(".md"):
        return MarkdownSyntaxHighlighter(), "Markdown file"
    elif filename.endswith(".c") \
        or filename.endswith(".cc") \
        or filename.endswith(".cpp") \
        or filename.endswith(".h") \
        or filename.endswith(".hpp"):
        file_type = "C/C++ file"
        if filename.endswith(".h") or filename.endswith(".hpp"):
            file_type = "C/C++ Header file"
        return CSyntaxHighlighter(), file_type
    
    return BaseSyntaxHighlighter(), "text file"
