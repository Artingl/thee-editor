from .syntax_highlighter import *


class PySyntaxHighlighter(BaseSyntaxHighlighter):
    KEYWORDS = ['if', 'elif', 'else', 'for', 'while', 'import', 'from', 'class', 'def', 'self', 'or', 'and', 'not',
                'in', 'lambda', 'match', 'case', 'break', 'continue', 'return', 'True', 'False', 'None', 'pass', 'with',
                'as', 'is']
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
            tokens, is_end = self.parse_literal(lambda x: x == char, STRING_LITERAL_COLOR)
        elif char.isalpha() or char == '@':
            checker = lambda x: not (x.isalpha() or x.isdigit() or x == '_')
            if char == '@':
                checker = lambda x: not (x.isalpha() or x.isdigit() or x == '_' or x == '@')
            tokens, is_end = self.parse_literal(
                checker,
                BASE_COLOR,
                skip_last_character=True
            )

            # Highlight different keywords with different color
            for token in tokens:
                if token.value in PySyntaxHighlighter.KEYWORDS:
                    token.color = KEYWORD0_LITERAL_COLOR
                elif token.value in PySyntaxHighlighter.RESERVED_NAMES_KEYWORDS or token.value.startswith("@"):
                    token.color = KEYWORD1_LITERAL_COLOR
        elif char.isdigit():
            tokens, is_end = self.parse_literal(lambda x: not x.isdigit(), NUMBER_LITERAL_COLOR, skip_last_character=True)
        elif char == '#':
            tokens, is_end = self.parse_singleline_comment()
        else:
            char, is_end, is_new_line = self.next_char()
            tokens = [Token(char, BASE_COLOR, (0, 0, 0), is_new_line=is_new_line)]

        return tokens, is_end
