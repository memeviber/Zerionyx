from .consts import *
from .errors import ExpectedCharError, IllegalCharError, InvalidSyntaxError
from .utils import Position, Token


class Lexer:
    __slots__ = ["fn", "text", "pos", "current_char", "tokens", "open_bracket_stack"]

    def __init__(self, fn, text):
        self.fn = fn
        self.text = text
        self.pos = Position(-1, 0, fn, text)
        self.current_char = None
        self.advance()
        self.tokens = []
        self.open_bracket_stack = []

    def advance(self, steps=1):
        for _ in range(steps):
            self.pos.advance(self.current_char)
            self.current_char = (
                self.text[self.pos.idx] if self.pos.idx < len(self.text) else None
            )

    def make_tokens(self):
        while self.current_char is not None:
            if self.current_char in " \t":
                self.advance()
            elif self.current_char == "#":
                self.skip_comment()
            elif self.current_char in ";\n":
                if self.open_bracket_stack:
                    self.advance()
                else:
                    if self.tokens and self.tokens[-1].type == TT_NEWLINE:
                        self.advance()
                        continue
                    newline_pos_start = self.pos.copy()
                    self.tokens.append(Token(TT_NEWLINE, pos_start=newline_pos_start))
                    self.advance()
            elif self.current_char in DIGITS:
                self.tokens.append(self.make_number())
            elif self.current_char in LETTERS + "_":
                self.tokens.append(self.make_identifier())
            elif self.current_char == '"' or self.current_char == "'":
                token, error = self.make_string()
                if error:
                    return [], error
                self.tokens.append(token)
            elif self.current_char == "+":
                self.handle_plus_or_augmented()
            elif self.current_char == "-":
                self.handle_minus_or_augmented()
            elif self.current_char == "*":
                self.handle_mul_or_dstar_or_augmented()
            elif self.current_char == "/":
                self.div_or_floordiv_or_augmented()
            elif self.current_char == "&":
                self.tokens.append(Token(TT_AND, pos_start=self.pos))
                self.advance()
            elif self.current_char == "\\":
                if self.peek_foward_steps(1) == "\n":
                    self.advance(2)
                else:
                    pos_start = self.pos.copy()
                    self.advance()
                    return [], IllegalCharError(
                        pos_start, self.pos, "Stray '\\' character in program"
                    )
            elif self.current_char == "^":
                self.handle_pow_or_augmented()
            elif self.current_char == "%":
                self.handle_mod_or_augmented()
            elif self.current_char == "=":
                self.tokens.append(self.make_equals())
            elif self.current_char == "(":
                pos_start = self.pos.copy()
                self.tokens.append(Token(TT_LPAREN, pos_start=pos_start))
                self.advance()
                self.tokens[-1].pos_end = self.pos.copy()
                self.open_bracket_stack.append((")", pos_start))
            elif self.current_char == ")":
                pos_start_closer = self.pos.copy()
                self.tokens.append(Token(TT_RPAREN, pos_start=pos_start_closer))
                self.advance()
                self.tokens[-1].pos_end = self.pos.copy()
                if not self.open_bracket_stack:
                    return [], ExpectedCharError(pos_start_closer, self.pos, "')'")
                expected_closer, _ = self.open_bracket_stack[-1]
                if expected_closer == ")":
                    self.open_bracket_stack.pop()
                else:
                    return [], ExpectedCharError(
                        pos_start_closer, self.pos, f"'{expected_closer}'"
                    )
            elif self.current_char == "[":
                pos_start = self.pos.copy()
                self.tokens.append(Token(TT_LSQUARE, pos_start=pos_start))
                self.advance()
                self.tokens[-1].pos_end = self.pos.copy()
                self.open_bracket_stack.append(("]", pos_start))
            elif self.current_char == "]":
                pos_start_closer = self.pos.copy()
                self.tokens.append(Token(TT_RSQUARE, pos_start=pos_start_closer))
                self.advance()
                self.tokens[-1].pos_end = self.pos.copy()
                if not self.open_bracket_stack:
                    return [], ExpectedCharError(pos_start_closer, self.pos, "']'")
                expected_closer, _ = self.open_bracket_stack[-1]
                if expected_closer == "]":
                    self.open_bracket_stack.pop()
                else:
                    return [], ExpectedCharError(
                        pos_start_closer, self.pos, f"'{expected_closer}'"
                    )
            elif self.current_char == "!":
                token, error = self.make_not_equals()
                if error:
                    return [], error
                self.tokens.append(token)
            elif self.current_char == "<":
                self.tokens.append(self.make_less_than())
            elif self.current_char == ">":
                self.tokens.append(self.make_greater_than())
            elif self.current_char == ".":
                self.tokens.append(Token(TT_DOT, pos_start=self.pos.copy()))
                self.advance()
            elif self.current_char == ",":
                self.tokens.append(Token(TT_COMMA, pos_start=self.pos.copy()))
                self.advance()
                self.tokens[-1].pos_end = self.pos.copy()
            elif self.current_char == "{":
                pos_start = self.pos.copy()
                self.tokens.append(Token(TT_LBRACE, pos_start=pos_start))
                self.advance()
                self.tokens[-1].pos_end = self.pos.copy()
                self.open_bracket_stack.append(("}", pos_start))
            elif self.current_char == "}":
                pos_start_closer = self.pos.copy()
                self.tokens.append(Token(TT_RBRACE, pos_start=pos_start_closer))
                self.advance()
                self.tokens[-1].pos_end = self.pos.copy()
                if not self.open_bracket_stack:
                    return [], ExpectedCharError(pos_start_closer, self.pos, "'}'")
                expected_closer, _ = self.open_bracket_stack[-1]
                if expected_closer == "}":
                    self.open_bracket_stack.pop()
                else:
                    return [], ExpectedCharError(
                        pos_start_closer, self.pos, f"'{expected_closer}'"
                    )
            elif self.current_char == ":":
                pos_start = self.pos.copy()
                self.tokens.append(Token(TT_COLON, pos_start=pos_start))
                self.advance()
            elif self.current_char == "$":
                pos_start = self.pos.copy()
                self.tokens.append(Token(TT_DOLLAR, pos_start=pos_start))
                self.advance()
            else:
                pos_start = self.pos.copy()
                char = self.current_char
                self.advance()
                return [], IllegalCharError(pos_start, self.pos, "'" + char + "'")

        if self.open_bracket_stack:
            expected_closer, opener_pos_start = self.open_bracket_stack[-1]
            return [], ExpectedCharError(
                opener_pos_start, self.pos, f"Expected '{expected_closer}'"
            )

        self.tokens.append(Token(TT_EOF, pos_start=self.pos))
        return self.tokens, None

    def make_number(self):
        num_str = ""
        dot_count = 0
        pos_start = self.pos.copy()
        while self.current_char is not None and self.current_char in DIGITS + ".":
            if self.current_char == ".":
                if dot_count == 1:
                    break
                dot_count += 1
            num_str += self.current_char
            self.advance()
        if dot_count == 0:
            return Token(TT_INT, int(num_str), pos_start, self.pos)
        return Token(TT_FLOAT, float(num_str), pos_start, self.pos)

    def make_string(self):
        quote_char = self.current_char
        return self._process_string_literal(quote_char)

    def _process_string_literal(self, quote_char):
        string_content = []
        pos_start = self.pos.copy()
        self.advance()
        is_multiline = False
        closing_sequence = quote_char

        if self.current_char == quote_char and self.peek_foward_steps(1) == quote_char:
            is_multiline = True
            closing_sequence = quote_char * 3
            self.advance(2)

        escape_character = False

        while self.current_char is not None:
            if escape_character:
                string_content.append(self.current_char)
                escape_character = False
                self.advance()
                continue

            if self.current_char == "\\":
                string_content.append("\\")
                escape_character = True
                self.advance()
                continue

            if is_multiline:
                if (
                    self.current_char == quote_char
                    and self.peek_foward_steps(1) == quote_char
                    and self.peek_foward_steps(2) == quote_char
                ):
                    self.advance(3)
                    break
            else:
                if self.current_char == quote_char:
                    self.advance()
                    break

            string_content.append(self.current_char)
            self.advance()
        else:
            return None, ExpectedCharError(pos_start, self.pos, f"'{closing_sequence}'")

        raw_string = "".join(string_content)
        try:
            processed_string = raw_string.encode("raw_unicode_escape").decode(
                "unicode_escape"
            )
        except UnicodeDecodeError:
            return None, IllegalCharError(
                pos_start, self.pos, "Invalid escape sequence in string"
            )

        return Token(TT_STRING, processed_string, pos_start, self.pos), None

    def peek_foward_steps(self, steps) -> str | None:
        peek_pos_idx = self.pos.idx + steps
        if 0 <= peek_pos_idx < len(self.text):
            return self.text[peek_pos_idx]
        return None

    def handle_plus_or_augmented(self):
        pos_start = self.pos.copy()
        self.advance()
        if self.current_char == "=":
            self.advance()
            self.tokens.append(
                Token(TT_PLUSEQ, pos_start=pos_start, pos_end=self.pos.copy())
            )
        else:
            self.tokens.append(
                Token(TT_PLUS, pos_start=pos_start, pos_end=self.pos.copy())
            )

    def handle_minus_or_augmented(self):
        pos_start = self.pos.copy()
        self.advance()
        if self.current_char == ">":
            self.advance()
            self.tokens.append(
                Token(TT_ARROW, pos_start=pos_start, pos_end=self.pos.copy())
            )
        elif self.current_char == "=":
            self.advance()
            self.tokens.append(
                Token(TT_MINUSEQ, pos_start=pos_start, pos_end=self.pos.copy())
            )
        else:
            self.tokens.append(
                Token(TT_MINUS, pos_start=pos_start, pos_end=self.pos.copy())
            )

    def handle_mul_or_dstar_or_augmented(self):
        pos_start = self.pos.copy()
        self.advance()
        if self.current_char == "*":
            self.advance()
            self.tokens.append(
                Token(TT_DOUBLE_STAR, pos_start=pos_start, pos_end=self.pos.copy())
            )
        elif self.current_char == "=":
            self.advance()
            self.tokens.append(
                Token(TT_MULEQ, pos_start=pos_start, pos_end=self.pos.copy())
            )
        else:
            self.tokens.append(
                Token(TT_MUL, pos_start=pos_start, pos_end=self.pos.copy())
            )

    def handle_pow_or_augmented(self):
        pos_start = self.pos.copy()
        self.advance()
        if self.current_char == "=":
            self.advance()
            self.tokens.append(
                Token(TT_POWEQ, pos_start=pos_start, pos_end=self.pos.copy())
            )
        else:
            self.tokens.append(
                Token(TT_POW, pos_start=pos_start, pos_end=self.pos.copy())
            )

    def handle_mod_or_augmented(self):
        pos_start = self.pos.copy()
        self.advance()
        if self.current_char == "=":
            self.advance()
            self.tokens.append(
                Token(TT_MODEQ, pos_start=pos_start, pos_end=self.pos.copy())
            )
        else:
            self.tokens.append(
                Token(TT_MOD, pos_start=pos_start, pos_end=self.pos.copy())
            )

    def div_or_floordiv_or_augmented(self):
        pos_start = self.pos.copy()
        self.advance()
        if self.current_char == "/":
            self.advance()
            if self.current_char == "=":
                self.advance()
                self.tokens.append(
                    Token(TT_FLOORDIVEQ, pos_start=pos_start, pos_end=self.pos.copy())
                )
            else:
                self.tokens.append(
                    Token(TT_FLOORDIV, pos_start=pos_start, pos_end=self.pos.copy())
                )
        elif self.current_char == "=":
            self.advance()
            self.tokens.append(
                Token(TT_DIVEQ, pos_start=pos_start, pos_end=self.pos.copy())
            )
        else:
            self.tokens.append(
                Token(TT_DIV, pos_start=pos_start, pos_end=self.pos.copy())
            )

    def make_identifier(self) -> Token:
        id_str = ""
        pos_start = self.pos.copy()
        while (
            self.current_char is not None and self.current_char in LETTERS_DIGITS + "_"
        ):
            id_str += self.current_char
            self.advance()
        tok_type = TT_KEYWORD if id_str in KEYWORDS else TT_IDENTIFIER
        return Token(tok_type, id_str, pos_start, self.pos.copy())

    def make_not_equals(self):
        pos_start = self.pos.copy()
        self.advance()
        if self.current_char == "=":
            self.advance()
            return Token(TT_NE, pos_start=pos_start, pos_end=self.pos.copy()), None
        return None, ExpectedCharError(pos_start, self.pos.copy(), "'=' (after '!')")

    def make_equals(self) -> Token:
        tok_type = TT_EQ
        pos_start = self.pos.copy()
        self.advance()
        if self.current_char == "=":
            self.advance()
            tok_type = TT_EE
        return Token(tok_type, pos_start=pos_start, pos_end=self.pos.copy())

    def make_less_than(self) -> Token:
        tok_type = TT_LT
        pos_start = self.pos.copy()
        self.advance()
        if self.current_char == "=":
            self.advance()
            tok_type = TT_LTE
        return Token(tok_type, pos_start=pos_start, pos_end=self.pos.copy())

    def make_greater_than(self) -> Token:
        tok_type = TT_GT
        pos_start = self.pos.copy()
        self.advance()
        if self.current_char == "=":
            self.advance()
            tok_type = TT_GTE
        return Token(tok_type, pos_start=pos_start, pos_end=self.pos.copy())

    def skip_comment(self) -> None:
        self.advance()
        while self.current_char is not None and self.current_char != "\n":
            self.advance()
