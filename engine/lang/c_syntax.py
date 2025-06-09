from .syntax_highlighter import *
from ..shell import BufferToken


class CSyntaxHighlighter(BaseSyntaxHighlighter):
    KEYWORDS = ['int', 'char', 'const', 'void', 'short', 'struct', 'return', 'if', 'else', 'while', 'for',
                'do', 'goto', 'double', 'float', 'long', 'break', 'continue', 'switch', 'case', 'size_t',
                'uint8_t', 'uint16_t', 'uint32_t', 'uint64_t', 'int8_t', 'int16_t', 'int32_t', 'int64_t',
                'size_t', 'unsigned', 'static', 'extern']
    RESERVED_NAMES_KEYWORDS = ['NULL', 'true', 'false']


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

        if char in ['"', "'"]:#, '<']:
            tokens, is_end = self.parse_literal(lambda x: x == ('>' if char == '<' else char), STRING_LITERAL_COLOR)
        elif char.isalpha() or char == '#':
            checker = lambda x: not (x.isalpha() or x.isdigit() or x == '_')
            if char == '#':
                checker = lambda x: not (x.isalpha() or x.isdigit() or x == '_' or x == '#')
            tokens, is_end = self.parse_literal(
                checker,
                BASE_COLOR,
                skip_last_character=True
            )

            # Highlight different keywords with different color
            for token in tokens:
                if token.value in CSyntaxHighlighter.KEYWORDS:
                    token.color = KEYWORD0_LITERAL_COLOR
                elif token.value in CSyntaxHighlighter.RESERVED_NAMES_KEYWORDS or token.value.startswith("#"):
                    token.color = KEYWORD1_LITERAL_COLOR
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
                    tokens = [BufferToken(char, BASE_COLOR, (0, 0, 0), is_new_line=is_new_line)]
            else:
                tokens = [BufferToken(char, BASE_COLOR, (0, 0, 0), is_new_line=is_new_line)]
        else:
            char, is_end, is_new_line = self.next_char()
            tokens = [BufferToken(char, BASE_COLOR, (0, 0, 0), is_new_line=is_new_line)]

        return tokens, is_end