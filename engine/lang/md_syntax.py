from .syntax_highlighter import *
from ..shell import BufferToken


class MarkdownSyntaxHighlighter(BaseSyntaxHighlighter):
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

        if char == '#':
            tokens, is_end = self.parse_singleline_comment()
        elif char.isalpha():
            tokens, is_end = self.parse_literal(
                lambda x: not (x.isalpha() or x.isdigit() or x in ['-', '!', '[', ']', '_']),
                BASE_COLOR,
                skip_last_character=True
            )
        elif char in ['-', '!', '[', ']']:
            char, is_end, is_new_line = self.next_char()
            tokens = [BufferToken(char, KEYWORD0_LITERAL_COLOR, (0, 0, 0), is_new_line=is_new_line)]
        else:
            char, is_end, is_new_line = self.next_char()
            tokens = [BufferToken(char, BASE_COLOR, (0, 0, 0), is_new_line=is_new_line)]

        return tokens, is_end
