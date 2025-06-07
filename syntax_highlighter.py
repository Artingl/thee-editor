# Bullshit code is written here.
# Wanted to make a PoC syntax highlighter, that's why it is so poorly written.

BASE_COLOR = (255, 255, 255)
STRING_LITERAL_COLOR = (190, 140, 100)
KEYWORD0_LITERAL_COLOR = (100, 100, 150)
KEYWORD1_LITERAL_COLOR = (190, 190, 100)
NUMBER_LITERAL_COLOR = (100, 190, 150)
COMMENT_COLOR = (100, 190, 100)


class SyntaxHighlighter:
    def __init__(self, editor):
        self.editor = editor
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
            tokens.append(Token(text, color, is_new_line=True))
            text = ""
        elif is_end:
            tokens.append(Token(text, color))
            return tokens, True
        while True:
            char, is_end, is_new_line = self.next_char()
            text += char
            if is_new_line:
                tokens.append(Token(text, color, is_new_line=True))
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
            tokens.append(Token(text, color, is_new_line=is_new_line))
        return tokens, is_end

    def parse_singleline_comment(self, comment_sign=''):
        tokens = []
        text, is_end, is_new_line = self.next_char()
        text = comment_sign + text
        if is_new_line or is_end:
            tokens.append(Token(text, COMMENT_COLOR, is_new_line=True))
            return tokens, is_end
        while True:
            char, is_end, is_new_line = self.next_char()
            text += char
            if is_new_line:
                tokens.append(Token(text, COMMENT_COLOR, is_new_line=True))
                text = ""
            if is_end or is_new_line:
                break
        if text or is_end:
            tokens.append(Token(text, COMMENT_COLOR, is_new_line=is_new_line))
        return tokens, is_end


class Token:
    def __init__(self, value, color, background=(0, 0, 0), is_new_line=False):
        self.value = value
        self.color = color
        self.background = background
        self.is_new_line = is_new_line

    def __repr__(self):
        return f"Token[{self.value}, {self.color}, {self.background}, {self.is_new_line}]"


class CSyntaxHighlighter(SyntaxHighlighter):
    KEYWORDS = ['int', 'char', 'const', 'void', 'short', 'struct', 'return', 'if', 'else', 'while', 'for',
                'do', 'goto', 'double', 'float', 'long']


    def parse_code(self, lines_of_code):
        self.reset_code(lines_of_code)
        result = []
        line = []
        while True:
            tokens, is_end = self.parse_tokens()

            for token in tokens:
                line.append(token)
                if token.is_new_line:
                    result.append(line)
                    line = []
            
            if is_end:
                break
        if line:
            result.append(line)

        return result

    def parse_tokens(self):
        tokens = None
        char, is_end, is_new_line = self.next_char(step_further=False)

        if char in ['"', "'", '<']:
            tokens, is_end = self.parse_literal(lambda x: x == ('>' if char == '<' else char), STRING_LITERAL_COLOR)
        elif char.isalpha():
            tokens, is_end = self.parse_literal(
                lambda x: not (x.isalpha() or x.isdigit() or x == '_'),
                KEYWORD0_LITERAL_COLOR,
                skip_last_character=True
            )

            # Highlight different keywords with different color
            for token in tokens:
                if token.value not in CSyntaxHighlighter.KEYWORDS:
                    token.color = BASE_COLOR
        elif char.isdigit():
            tokens, is_end = self.parse_literal(lambda x: not x.isdigit(), NUMBER_LITERAL_COLOR, skip_last_character=True)
        elif char == '/':
            _, is_end, is_new_line = self.next_char()
            if not is_end:
                second_char, is_end, _ = self.next_char(step_further=False)

                if second_char == '/':
                    # We give only a single slash as the comment sign to the parser function, because
                    # it'll fetch the other one on next call to self.next_char()
                    tokens, is_end = self.parse_singleline_comment('/')
                else:
                    tokens = [Token(char, BASE_COLOR, (0, 0, 0), is_new_line=is_new_line)]
            else:
                tokens = [Token(char, BASE_COLOR, (0, 0, 0), is_new_line=is_new_line)]
        else:
            char, is_end, is_new_line = self.next_char()
            tokens = [Token(char, BASE_COLOR, (0, 0, 0), is_new_line=is_new_line)]

        return tokens, is_end

class PySyntaxHighlighter(SyntaxHighlighter):
    KEYWORDS = ['if', 'elif', 'else', 'for', 'while', 'import', 'from', 'class', 'def', 'self']
    RESERVED_NAMES_KEYWORDS = ['print', '__init__', 'str', 'int', 'float', 'bool', 'input']

    def parse_code(self, lines_of_code):
        self.reset_code(lines_of_code)
        result = []
        line = []
        while True:
            tokens, is_end = self.parse_tokens()

            for token in tokens:
                line.append(token)
                if token.is_new_line:
                    result.append(line)
                    line = []
            
            if is_end:
                break
        if line:
            result.append(line)

        return result

    def parse_tokens(self):
        tokens = None
        char, is_end, is_new_line = self.next_char(step_further=False)

        if char in ['"', "'"]:
            tokens, is_end = self.parse_literal(lambda x: x == ('>' if char == '<' else char), STRING_LITERAL_COLOR)
        elif char.isalpha():
            tokens, is_end = self.parse_literal(
                lambda x: not (x.isalpha() or x.isdigit() or x == '_'),
                BASE_COLOR,
                skip_last_character=True
            )

            # Highlight different keywords with different color
            for token in tokens:
                if token.value in PySyntaxHighlighter.KEYWORDS:
                    token.color = KEYWORD0_LITERAL_COLOR
                elif token.value in PySyntaxHighlighter.RESERVED_NAMES_KEYWORDS:
                    token.color = KEYWORD1_LITERAL_COLOR
        elif char.isdigit():
            tokens, is_end = self.parse_literal(lambda x: not x.isdigit(), NUMBER_LITERAL_COLOR, skip_last_character=True)
        elif char == '#':
            tokens, is_end = self.parse_singleline_comment()
        else:
            char, is_end, is_new_line = self.next_char()
            tokens = [Token(char, BASE_COLOR, (0, 0, 0), is_new_line=is_new_line)]

        return tokens, is_end

