from .syntax_highlighter import *


class JsonSyntaxHighlighter(BaseSyntaxHighlighter):
    KEYWORDS = ['true', 'false', 'null']

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
        elif char.isalpha():
            tokens, is_end = self.parse_literal(
                lambda x: not (x.isalpha() or x.isdigit() or x == '_'),
                KEYWORD0_LITERAL_COLOR,
                skip_last_character=True
            )

            # Highlight different keywords with different color
            for token in tokens:
                if token.value not in JsonSyntaxHighlighter.KEYWORDS:
                    token.color = BASE_COLOR
        elif char.isdigit():
            tokens, is_end = self.parse_literal(lambda x: not x.isdigit(), NUMBER_LITERAL_COLOR, skip_last_character=True)
        else:
            char, is_end, is_new_line = self.next_char()
            tokens = [Token(char, BASE_COLOR, (0, 0, 0), is_new_line=is_new_line)]

        return tokens, is_end
