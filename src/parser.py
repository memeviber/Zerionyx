import os

from .consts import *
from .errors import InvalidSyntaxError
from .nodes import *
from .utils import Token


class ParseResult:
    def __init__(self):
        self.error = None
        self.node = None
        self.last_registered_advance_count = 0
        self.advance_count = 0
        self.to_reverse_count = 0

    def register_advancement(self):
        self.last_registered_advance_count = 1
        self.advance_count += 1

    def register(self, res):
        self.last_registered_advance_count = res.advance_count
        self.advance_count += res.advance_count
        if res.error:
            self.error = res.error
        return res.node

    def try_register(self, res):
        if res.error:
            self.to_reverse_count = res.advance_count
            return None
        return self.register(res)

    def success(self, node):
        self.node = node
        return self

    def failure(self, error):
        if not self.error or self.last_registered_advance_count == 0:
            self.error = error
        return self


class Parser:
    __slots__ = ("tokens", "tok_idx", "current_tok")

    def __init__(self, tokens):
        self.tokens = tokens
        self.tok_idx = -1
        self.current_tok = None
        self.advance()

    def advance(self):
        self.tok_idx += 1
        self.update_current_tok()
        return self.current_tok

    def reverse(self, amount=1):
        self.tok_idx -= amount
        self.update_current_tok()
        return self.current_tok

    def update_current_tok(self):
        if self.tok_idx >= 0 and self.tok_idx < len(self.tokens):
            self.current_tok: Token = self.tokens[self.tok_idx]
        else:
            self.current_tok = None

    def skip_newlines(self) -> ParseResult:
        res = ParseResult()
        while self.current_tok and self.current_tok.type == TT_NEWLINE:
            res.register_advancement()
            self.advance()
        return res

    def parse(self):
        self.skip_newlines()
        res = self.statements()
        if not res.error and self.current_tok.type != TT_EOF:
            return res.failure(
                InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    f"Unexpected token '{self.current_tok.type}'",
                )
            )
        return res

    def statements(self):
        res = ParseResult()
        statements = []
        pos_start = self.current_tok.pos_start.copy()

        self.skip_newlines()

        res.register(self.skip_newlines())

        statement = res.register(self.statement())
        if res.error:
            return res
        statements.append(statement)

        more_statements = True
        while True:
            newline_count = 0
            while self.current_tok.type == TT_NEWLINE:
                res.register_advancement()
                self.advance()
                newline_count += 1

            if newline_count == 0:
                more_statements = False

            if not more_statements:
                break

            self.skip_newlines()
            statement = res.try_register(self.statement())

            if not statement:
                self.reverse(res.to_reverse_count)
                more_statements = False
                continue

            statements.append(statement)

        return res.success(
            ListNode(statements, pos_start, self.current_tok.pos_end.copy())
        )

    def statement(self):
        res = ParseResult()
        pos_start = self.current_tok.pos_start.copy()

        if self.current_tok.type == TT_AND:
            decorator_nodes = []
            while self.current_tok.type == TT_AND:
                res.register_advancement()
                self.advance()
                decorator_nodes.append(res.register(self.expr(allow_assignment=False)))
                if res.error:
                    return res
                self.skip_newlines()

            if not self.current_tok.matches(TT_KEYWORD, "defun"):
                return res.failure(
                    InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        "Expected 'defun' after decorator(s)",
                    )
                )

            func_def_node = res.register(self.func_def())
            if res.error:
                return res

            func_def_node.decorator_nodes = decorator_nodes
            return res.success(func_def_node)

        if self.current_tok.matches(TT_KEYWORD, "using"):
            return self.using_expr()

        if self.current_tok.matches(TT_KEYWORD, "del"):
            return self.del_expr()

        if self.current_tok.matches(TT_KEYWORD, "defun"):
            return self.func_def()

        if self.current_tok.matches(TT_KEYWORD, "return"):
            res.register_advancement()
            self.advance()

            expr = None
            if self.current_tok.type not in (
                TT_NEWLINE,
                TT_EOF,
            ) and not self.current_tok.matches(TT_KEYWORD, "done"):
                expr = res.try_register(self.expr(allow_assignment=False))
                if res.error:
                    return res

            return res.success(
                ReturnNode(expr, pos_start, self.current_tok.pos_start.copy())
            )

        if self.current_tok.matches(TT_KEYWORD, "continue"):
            res.register_advancement()
            self.advance()
            return res.success(
                ContinueNode(pos_start, self.current_tok.pos_start.copy())
            )

        if self.current_tok.matches(TT_KEYWORD, "break"):
            res.register_advancement()
            self.advance()
            return res.success(BreakNode(pos_start, self.current_tok.pos_start.copy()))

        expr = res.register(self.expr())
        if res.error:
            return res.failure(
                InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected 'return', 'continue', 'break', 'if', 'for', 'while', 'defun', int, float, identifier, '+', '-', '(', '[', '{' or 'not'",
                )
            )
        return res.success(expr)

    def peek_tok(self) -> Token:
        if self.tok_idx + 1 >= len(self.tokens):
            return None
        return self.tokens[self.tok_idx + 1]

    def peek_tok_back(self) -> Token:
        if self.tok_idx - 1 < 0:
            return None
        return self.tokens[self.tok_idx - 1]

    def expr(self, allow_assignment=True):
        res = ParseResult()

        node = res.register(self.assignment_expr(allow_assignment))

        if res.error:
            return res.failure(
                InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected 'if', 'for', 'while', 'defun', int, float, identifier, '+', '-', '(', '[', '{' or 'not'",
                )
            )

        return res.success(node)

    def assignment_expr(self, allow_assignment=True):
        res = ParseResult()

        if allow_assignment:
            if self.current_tok.type == TT_IDENTIFIER:
                var_name_tok = self.current_tok
                res.register_advancement()
                self.advance()

                aug_ops = {
                    TT_PLUSEQ: TT_PLUS,
                    TT_MINUSEQ: TT_MINUS,
                    TT_MULEQ: TT_MUL,
                    TT_DIVEQ: TT_DIV,
                    TT_FLOORDIVEQ: TT_FLOORDIV,
                    TT_MODEQ: TT_MOD,
                    TT_POWEQ: TT_POW,
                }

                if self.current_tok.type == TT_EQ:
                    res.register_advancement()
                    self.advance()
                    value_node = res.register(self.expr())
                    if res.error:
                        return res
                    return res.success(VarAssignNode(var_name_tok, value_node))

                elif self.current_tok.type in aug_ops:
                    op_type = aug_ops[self.current_tok.type]
                    op_tok = Token(
                        op_type,
                        pos_start=self.current_tok.pos_start.copy(),
                        pos_end=self.current_tok.pos_end.copy(),
                    )
                    res.register_advancement()
                    self.advance()

                    value_node = res.register(self.expr())
                    if res.error:
                        return res

                    left_node = VarAccessNode(var_name_tok)
                    bin_op = BinOpNode(left_node, op_tok, value_node)
                    return res.success(VarAssignNode(var_name_tok, bin_op))

                self.reverse(res.advance_count)

        if self.current_tok.matches(TT_KEYWORD, "load"):
            res.register_advancement()
            self.advance()
            if self.current_tok.type != TT_STRING:
                return res.failure(
                    InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        "Expected string",
                    )
                )
            module = self.current_tok
            raw_path = module.value.replace(".", os.sep)
            if raw_path.endswith(("\\", "/")):
                raw_path = raw_path[:-1]
            raw_path += ".zyx"
            candidates = []
            if module.value.startswith("libs."):
                candidates.append(raw_path)
            elif module.value.startswith("local."):
                if self.current_tok.pos_start.fn == "<stdin>":
                    local_path = os.path.join(
                        os.path.dirname(os.path.abspath(__file__)), raw_path[6:]
                    )
                else:
                    local_path = os.path.join(
                        os.path.dirname(os.path.abspath(self.current_tok.pos_start.fn)),
                        raw_path[6:],
                    )
                candidates.append(local_path)
            else:
                return res.failure(
                    InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        "Paths must start with 'libs.' or 'local.'",
                    )
                )
            chosen_path = None
            for path in candidates:
                if os.path.exists(path):
                    chosen_path = path
                    break
            module.value = os.path.normpath(chosen_path or candidates[0])
            res.register_advancement()
            self.advance()
            return res.success(LoadNode(module))

        node = res.register(
            self.bin_op(self.comp_expr, ((TT_KEYWORD, "and"), (TT_KEYWORD, "or")))
        )

        if res.error:
            return res

        if isinstance(node, BinOpNode) and node.op_tok.type == TT_DOLLAR:

            aug_ops = {
                TT_PLUSEQ: TT_PLUS,
                TT_MINUSEQ: TT_MINUS,
                TT_MULEQ: TT_MUL,
                TT_DIVEQ: TT_DIV,
                TT_FLOORDIVEQ: TT_FLOORDIV,
                TT_MODEQ: TT_MOD,
                TT_POWEQ: TT_POW,
            }

            if self.current_tok.type == TT_EQ:
                res.register_advancement()
                self.advance()

                value_node = res.register(self.expr())
                if res.error:
                    return res

                return res.success(
                    IndexAssignNode(node.left_node, node.right_node, value_node)
                )

            elif self.current_tok.type in aug_ops:
                op_type = aug_ops[self.current_tok.type]
                op_tok = Token(
                    op_type,
                    pos_start=self.current_tok.pos_start.copy(),
                    pos_end=self.current_tok.pos_end.copy(),
                )
                res.register_advancement()
                self.advance()

                value_node = res.register(self.expr())
                if res.error:
                    return res

                bin_op = BinOpNode(node, op_tok, value_node)
                return res.success(
                    IndexAssignNode(node.left_node, node.right_node, bin_op)
                )

        return res.success(node)

    def comp_expr(self):
        res = ParseResult()

        if self.current_tok.matches(TT_KEYWORD, "not"):
            op_tok = self.current_tok
            res.register_advancement()
            self.advance()
            node = res.register(self.comp_expr())
            if res.error:
                return res
            return res.success(UnaryOpNode(op_tok, node))

        node = res.register(
            self.bin_op(self.arith_expr, (TT_EE, TT_NE, TT_LT, TT_GT, TT_LTE, TT_GTE))
        )

        if res.error:
            return res.failure(
                InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected int, float, identifier, '+', '-', '(', '[', '{', 'if', 'for', 'while', 'defun' or 'not'",
                )
            )

        return res.success(node)

    def arith_expr(self):
        return self.bin_op(self.term, (TT_PLUS, TT_MINUS))

    def term(self):
        return self.bin_op(self.factor, (TT_MUL, TT_DIV, TT_FLOORDIV, TT_MOD))

    def factor(self):
        res = ParseResult()
        tok = self.current_tok

        if tok.type in (TT_PLUS, TT_MINUS):
            res.register_advancement()
            self.advance()
            factor = res.register(self.factor())
            if res.error:
                return res
            return res.success(UnaryOpNode(tok, factor))

        elif tok.type == TT_MUL:
            res.register_advancement()
            self.advance()
            node_to_unpack = res.register(self.factor())
            if res.error:
                return res
            return res.success(VargsUnpackNode(node_to_unpack))

        elif tok.type == TT_DOUBLE_STAR:
            res.register_advancement()
            self.advance()
            node_to_unpack = res.register(self.factor())
            if res.error:
                return res
            return res.success(KargsUnpackNode(node_to_unpack))

        return self.dollar_op()

    def power(self):
        return self.bin_op(self.call, (TT_POW,))

    def dot_op(self):
        return self.bin_op(self.power, (TT_DOT,))

    def dollar_op(self):
        return self.bin_op(self.dot_op, (TT_DOLLAR,))

    def call(self):
        res = ParseResult()
        node = res.register(self.atom())
        if res.error:
            return res

        while self.current_tok.type == TT_DOT:
            res.register_advancement()
            self.advance()

            if self.current_tok.type != TT_IDENTIFIER:
                return res.failure(
                    InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        "Expected identifier",
                    )
                )

            member_name_tok = self.current_tok
            res.register_advancement()
            self.advance()
            node = MemberAccessNode(
                node,
                member_name_tok.value,
                node.pos_start,
                self.current_tok.pos_end.copy(),
            )

        if self.current_tok.type == TT_LPAREN:
            res.register_advancement()
            self.advance()
            arg_nodes = []
            if self.current_tok.type == TT_RPAREN:
                res.register_advancement()
                self.advance()
            else:
                while True:
                    self.skip_newlines()
                    if (
                        self.current_tok.type == TT_IDENTIFIER
                        and self.peek_tok()
                        and self.peek_tok().type == TT_EQ
                    ):
                        var_name_tok = self.current_tok
                        res.register_advancement()
                        self.advance()

                        res.register_advancement()
                        self.advance()

                        value_node = res.register(self.expr(allow_assignment=False))
                        if res.error:
                            return res
                        arg_nodes.append(VarAssignNode(var_name_tok, value_node))
                    else:
                        arg_nodes.append(
                            res.register(self.expr(allow_assignment=False))
                        )
                        if res.error:
                            return res.failure(
                                InvalidSyntaxError(
                                    self.current_tok.pos_start,
                                    self.current_tok.pos_end,
                                    "Expected ')', 'if', 'for', 'while', 'defun', int, float, identifier, '+', '-', '(', '[', '{' or 'not'",
                                )
                            )
                    self.skip_newlines()
                    if self.current_tok.type == TT_RPAREN:
                        res.register_advancement()
                        self.advance()
                        break
                    elif self.current_tok.type == TT_COMMA:
                        res.register_advancement()
                        self.advance()
                    else:
                        return res.failure(
                            InvalidSyntaxError(
                                self.current_tok.pos_start,
                                self.current_tok.pos_end,
                                "Expected ',' or ')'",
                            )
                        )
            return res.success(CallNode(node, arg_nodes))

        return res.success(node)

    def using_expr(self):
        res = ParseResult()
        pos_start = self.current_tok.pos_start.copy()

        res.register_advancement()
        self.advance()

        if self.current_tok.matches(TT_IDENTIFIER, "parent"):
            res.register_advancement()
            self.advance()

            node_class = UsingParentNode
            err_msg = "Expected identifier after 'using parent'"
        else:
            node_class = UsingNode
            err_msg = "Expected identifier after 'using'"

        if self.current_tok.type != TT_IDENTIFIER:
            return res.failure(
                InvalidSyntaxError(
                    self.current_tok.pos_start, self.current_tok.pos_end, err_msg
                )
            )

        var_name_toks = [self.current_tok]
        res.register_advancement()
        self.advance()

        while self.current_tok.type == TT_COMMA:
            res.register_advancement()
            self.advance()
            if self.current_tok.type != TT_IDENTIFIER:
                return res.failure(
                    InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        "Expected identifier",
                    )
                )
            var_name_toks.append(self.current_tok)
            res.register_advancement()
            self.advance()

        return res.success(
            node_class(var_name_toks, pos_start, self.current_tok.pos_end.copy())
        )

    def del_expr(self):
        res = ParseResult()
        pos_start = self.current_tok.pos_start.copy()

        res.register_advancement()
        self.advance()

        if self.current_tok.type != TT_IDENTIFIER:
            return res.failure(
                InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected identifier after 'del'",
                )
            )

        var_name_toks = [self.current_tok]
        res.register_advancement()
        self.advance()

        while self.current_tok.type == TT_COMMA:
            res.register_advancement()
            self.advance()
            if self.current_tok.type != TT_IDENTIFIER:
                return res.failure(
                    InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        "Expected identifier",
                    )
                )
            var_name_toks.append(self.current_tok)
            res.register_advancement()
            self.advance()

        return res.success(
            DelNode(var_name_toks, pos_start, self.current_tok.pos_end.copy())
        )

    def atom(self):
        res = ParseResult()
        tok = self.current_tok

        if tok.type in (TT_INT, TT_FLOAT):
            res.register_advancement()
            self.advance()
            return res.success(NumberNode(tok))
        elif tok.type == TT_STRING:
            res.register_advancement()
            self.advance()
            return res.success(StringNode(tok))
        elif tok.type == TT_IDENTIFIER:
            res.register_advancement()
            self.advance()
            return res.success(VarAccessNode(tok))
        elif tok.type == TT_LPAREN:
            res.register_advancement()
            self.advance()
            expr = res.register(self.expr(allow_assignment=False))
            if res.error:
                return res
            if self.current_tok.type == TT_RPAREN:
                res.register_advancement()
                self.advance()
                return res.success(expr)
            else:
                return res.failure(
                    InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        "Expected ')'",
                    )
                )
        elif tok.type == TT_LSQUARE:
            list_expr = res.register(self.list_expr())
            if res.error:
                return res
            return res.success(list_expr)
        elif tok.matches(TT_KEYWORD, "if"):
            if_expr = res.register(self.if_expr())
            if res.error:
                return res
            return res.success(if_expr)
        elif tok.matches(TT_KEYWORD, "for"):
            for_expr = res.register(self.for_expr())
            if res.error:
                return res
            return res.success(for_expr)
        elif tok.matches(TT_KEYWORD, "while"):
            while_expr = res.register(self.while_expr())
            if res.error:
                return res
            return res.success(while_expr)
        elif tok.matches(TT_KEYWORD, "defun"):
            func_def = res.register(self.func_def())
            if res.error:
                return res
            return res.success(func_def)
        elif tok.matches(TT_KEYWORD, "namespace"):
            namespace = res.register(self.namespace())
            if res.error:
                return res
            return res.success(namespace)
        elif tok.type == TT_LBRACE:
            hashmap_expr = res.register(self.hashmap_expr())
            if res.error:
                return res
            return res.success(hashmap_expr)

        return res.failure(
            InvalidSyntaxError(
                tok.pos_start,
                tok.pos_end,
                "Expected int, float, identifier, '+', '-', '(', '[', '{', 'if', 'for', 'while', 'defun' or 'namespace'",
            )
        )

    def namespace(self):
        res = ParseResult()
        pos_start = self.current_tok.pos_start.copy()

        if not self.current_tok.matches(TT_KEYWORD, "namespace"):
            return res.failure(
                InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected 'namespace'",
                )
            )
        res.register_advancement()
        self.advance()

        if self.current_tok.type != TT_IDENTIFIER:
            return res.failure(
                InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected identifier",
                )
            )
        namespace_name = self.current_tok.value
        res.register_advancement()
        self.advance()

        if self.current_tok.type != TT_NEWLINE:
            return res.failure(
                InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected newline",
                )
            )
        res.register_advancement()
        self.advance()

        statements = []
        while not self.current_tok.matches(TT_KEYWORD, "done"):
            self.skip_newlines()
            stmt = res.register(self.statement())
            if res.error:
                return res
            statements.append(stmt)
            self.skip_newlines()

        statements_node = ListNode(
            statements, pos_start, self.current_tok.pos_start.copy()
        )

        if not self.current_tok.matches(TT_KEYWORD, "done"):
            return res.failure(
                InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected 'done'",
                )
            )
        res.register_advancement()
        self.advance()

        return res.success(
            NameSpaceNode(
                namespace_name,
                statements_node,
                pos_start,
                self.current_tok.pos_end.copy(),
            )
        )

    def hashmap_expr(self) -> ParseResult:
        res = ParseResult()
        pairs = []
        pos_start = self.current_tok.pos_start.copy()

        if self.current_tok.type != TT_LBRACE:
            return res.failure(
                InvalidSyntaxError(
                    self.current_tok.pos_start, self.current_tok.pos_end, "Expected '{'"
                )
            )

        res.register_advancement()
        self.advance()
        self.skip_newlines()

        if self.current_tok.type == TT_RBRACE:
            res.register_advancement()
            self.advance()
            return res.success(
                HashMapNode([], pos_start, self.current_tok.pos_end.copy())
            )

        key = res.register(self.expr(allow_assignment=False))
        if res.error:
            return res

        if self.current_tok.type != TT_COLON:
            return res.failure(
                InvalidSyntaxError(
                    self.current_tok.pos_start, self.current_tok.pos_end, "Expected ':'"
                )
            )
        res.register_advancement()
        self.advance()

        value = res.register(self.expr(allow_assignment=False))
        if res.error:
            return res
        pairs.append((key, value))

        while self.current_tok.type == TT_COMMA:
            res.register_advancement()
            self.advance()
            self.skip_newlines()

            key = res.register(self.expr(allow_assignment=False))
            if res.error:
                return res
            self.skip_newlines()

            if self.current_tok.type != TT_COLON:
                return res.failure(
                    InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        "Expected ':'",
                    )
                )
            res.register_advancement()
            self.advance()
            self.skip_newlines()

            value = res.register(self.expr(allow_assignment=False))
            if res.error:
                return res
            self.skip_newlines()
            pairs.append((key, value))

        self.skip_newlines()
        if self.current_tok.type != TT_RBRACE:
            return res.failure(
                InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected ',' or '}'",
                )
            )
        res.register_advancement()
        self.advance()

        return res.success(
            HashMapNode(pairs, pos_start, self.current_tok.pos_end.copy())
        )

    def list_expr(self):
        res = ParseResult()
        element_nodes = []
        pos_start = self.current_tok.pos_start.copy()

        if self.current_tok.type != TT_LSQUARE:
            return res.failure(
                InvalidSyntaxError(
                    self.current_tok.pos_start, self.current_tok.pos_end, "Expected '['"
                )
            )
        res.register_advancement()
        self.advance()

        if self.current_tok.type == TT_RSQUARE:
            res.register_advancement()
            self.advance()
            return res.success(
                ListNode(element_nodes, pos_start, self.current_tok.pos_end.copy())
            )

        first_element = res.register(self.expr(allow_assignment=False))
        if res.error:
            return res

        element_nodes.append(first_element)
        while self.current_tok.type == TT_COMMA:
            res.register_advancement()
            self.advance()
            element_nodes.append(res.register(self.expr(allow_assignment=False)))
            if res.error:
                return res

        if self.current_tok.type != TT_RSQUARE:
            return res.failure(
                InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected ',' or ']'",
                )
            )
        res.register_advancement()
        self.advance()

        return res.success(
            ListNode(element_nodes, pos_start, self.current_tok.pos_end.copy())
        )

    def if_expr(self):
        res = ParseResult()
        cases = []
        else_case = None
        is_multiline_structure = False

        if not self.current_tok.matches(TT_KEYWORD, "if"):
            return res.failure(
                InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected 'if'",
                )
            )
        res.register_advancement()
        self.advance()

        condition = res.register(self.expr(allow_assignment=False))
        if res.error:
            return res

        if not self.current_tok.matches(TT_KEYWORD, "do"):
            return res.failure(
                InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected 'do'",
                )
            )
        res.register_advancement()
        self.advance()

        if self.current_tok.type == TT_NEWLINE:
            is_multiline_structure = True
            res.register_advancement()
            self.advance()
            body = res.register(self.statements())
            if res.error:
                return res
            cases.append((condition, body, True))
        else:
            body = res.register(self.statement())
            if res.error:
                return res
            cases.append((condition, body, False))

        while self.current_tok.matches(TT_KEYWORD, "elif"):
            res.register_advancement()
            self.advance()

            condition = res.register(self.expr(allow_assignment=False))
            if res.error:
                return res

            if not self.current_tok.matches(TT_KEYWORD, "do"):
                return res.failure(
                    InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        "Expected 'do'",
                    )
                )
            res.register_advancement()
            self.advance()

            if self.current_tok.type == TT_NEWLINE:
                is_multiline_structure = True
                res.register_advancement()
                self.advance()
                body = res.register(self.statements())
                if res.error:
                    return res
                cases.append((condition, body, True))
            else:
                if is_multiline_structure:
                    return res.failure(
                        InvalidSyntaxError(
                            self.current_tok.pos_start,
                            self.current_tok.pos_end,
                            "Can't mix single-line and multi-line blocks in an if-elif-else chain",
                        )
                    )
                body = res.register(self.statement())
                if res.error:
                    return res
                cases.append((condition, body, False))

        if self.current_tok.matches(TT_KEYWORD, "else"):
            res.register_advancement()
            self.advance()

            if not self.current_tok.matches(TT_KEYWORD, "do"):
                return res.failure(
                    InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        "Expected 'do'",
                    )
                )
            res.register_advancement()
            self.advance()

            if self.current_tok.type == TT_NEWLINE:
                is_multiline_structure = True
                res.register_advancement()
                self.advance()
                body = res.register(self.statements())
                if res.error:
                    return res
                else_case = (body, True)
            else:
                if is_multiline_structure:
                    return res.failure(
                        InvalidSyntaxError(
                            self.current_tok.pos_start,
                            self.current_tok.pos_end,
                            "Can't mix single-line and multi-line blocks in an if-elif-else chain",
                        )
                    )
                body = res.register(self.statement())
                if res.error:
                    return res
                else_case = (body, False)

        if is_multiline_structure:
            if not self.current_tok.matches(TT_KEYWORD, "done"):
                return res.failure(
                    InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        "Expected 'done'",
                    )
                )
            res.register_advancement()
            self.advance()

        return res.success(IfNode(cases, else_case))

    def for_expr(self):
        res = ParseResult()
        pos_start = self.current_tok.pos_start.copy()

        if not self.current_tok.matches(TT_KEYWORD, "for"):
            return res.failure(
                InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected 'for'",
                )
            )
        res.register_advancement()
        self.advance()

        if self.current_tok.type != TT_IDENTIFIER:
            return res.failure(
                InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected identifier",
                )
            )

        first_var_name_tok = self.current_tok
        res.register_advancement()
        self.advance()

        if self.current_tok.type == TT_COMMA or self.current_tok.matches(
            TT_KEYWORD, "in"
        ):
            var_name_toks = [first_var_name_tok]
            while self.current_tok.type == TT_COMMA:
                res.register_advancement()
                self.advance()
                if self.current_tok.type != TT_IDENTIFIER:
                    return res.failure(
                        InvalidSyntaxError(
                            self.current_tok.pos_start,
                            self.current_tok.pos_end,
                            "Expected identifier",
                        )
                    )
                var_name_toks.append(self.current_tok)
                res.register_advancement()
                self.advance()

            if not self.current_tok.matches(TT_KEYWORD, "in"):
                return res.failure(
                    InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        "Expected 'in' after variable(s) in for-in loop",
                    )
                )

            res.register_advancement()
            self.advance()

            iterable_node = res.register(self.expr(allow_assignment=False))
            if res.error:
                return res

            if not self.current_tok.matches(TT_KEYWORD, "do"):
                return res.failure(
                    InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        "Expected 'do'",
                    )
                )
            res.register_advancement()
            self.advance()

            if self.current_tok.type == TT_NEWLINE:
                res.register_advancement()
                self.advance()
                body = res.register(self.statements())
                if res.error:
                    return res
                if not self.current_tok.matches(TT_KEYWORD, "done"):
                    return res.failure(
                        InvalidSyntaxError(
                            self.current_tok.pos_start,
                            self.current_tok.pos_end,
                            "Expected 'done'",
                        )
                    )
                res.register_advancement()
                self.advance()
                return res.success(
                    ForInNode(
                        var_name_toks,
                        iterable_node,
                        body,
                        True,
                        pos_start,
                        body.pos_end,
                    )
                )

            body = res.register(self.statement())
            if res.error:
                return res
            return res.success(
                ForInNode(
                    var_name_toks, iterable_node, body, False, pos_start, body.pos_end
                )
            )
        
        elif self.current_tok.type == TT_EQ or self.current_tok.matches(
            TT_KEYWORD, "to"
        ) or self.current_tok.matches(TT_KEYWORD, "until"):
            loop_specs = []
            var_name_tok = first_var_name_tok

            while True:
                start_value_node = None
                end_value_node = None
                step_value_node = None
                until = False

                if self.current_tok.matches(TT_KEYWORD, "to") or self.current_tok.matches(TT_KEYWORD, "until"):
                    until = self.current_tok.matches(TT_KEYWORD, "until")
                    zero_tok = Token(
                        TT_INT, 0, var_name_tok.pos_start, var_name_tok.pos_end
                    )
                    start_value_node = NumberNode(zero_tok)

                    res.register_advancement()
                    self.advance()

                    end_value_node = res.register(self.expr(allow_assignment=False))
                    if res.error:
                        return res

                elif self.current_tok.type == TT_EQ:
                    res.register_advancement()
                    self.advance()
                    start_value_node = res.register(self.expr(allow_assignment=False))
                    if res.error:
                        return res
                    
                    if not self.current_tok.matches(TT_KEYWORD, "to") and not self.current_tok.matches(TT_KEYWORD, "until"):
                        return res.failure(
                            InvalidSyntaxError(
                                self.current_tok.pos_start,
                                self.current_tok.pos_end,
                                "Expected 'to' or 'until'",
                            )
                        )
                    until = self.current_tok.matches(TT_KEYWORD, "until")
                    res.register_advancement()
                    self.advance()

                    end_value_node = res.register(self.expr(allow_assignment=False))
                    if res.error:
                        return res
                else:
                    return res.failure(
                        InvalidSyntaxError(
                            self.current_tok.pos_start,
                            self.current_tok.pos_end,
                            "Expected '=', 'to' or 'until'",
                        )
                    )

                if self.current_tok.matches(TT_KEYWORD, "step"):
                    res.register_advancement()
                    self.advance()
                    step_value_node = res.register(self.expr(allow_assignment=False))
                    if res.error:
                        return res

                loop_specs.append(
                    (var_name_tok, start_value_node, end_value_node, step_value_node, until)
                )

                if self.current_tok.type != TT_COMMA:
                    break

                res.register_advancement()
                self.advance()

                if self.current_tok.type != TT_IDENTIFIER:
                    return res.failure(
                        InvalidSyntaxError(
                            self.current_tok.pos_start,
                            self.current_tok.pos_end,
                            "Expected identifier after ',' in for loop",
                        )
                    )
                var_name_tok = self.current_tok
                res.register_advancement()
                self.advance()

            if not self.current_tok.matches(TT_KEYWORD, "do"):
                return res.failure(
                    InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        "Expected 'do'",
                    )
                )
            res.register_advancement()
            self.advance()

            is_multiline = False
            body_node = None
            if self.current_tok.type == TT_NEWLINE:
                is_multiline = True
                res.register_advancement()
                self.advance()
                body_node = res.register(self.statements())
                if res.error:
                    return res

                if not self.current_tok.matches(TT_KEYWORD, "done"):
                    return res.failure(
                        InvalidSyntaxError(
                            self.current_tok.pos_start,
                            self.current_tok.pos_end,
                            "Expected 'done'",
                        )
                    )
                res.register_advancement()
                self.advance()
            else:
                is_multiline = False
                body_node = res.register(self.statement())
                if res.error:
                    return res

            final_node = body_node
            for var, start, end, step, loop_until in reversed(loop_specs):
                final_node = ForNode(var, start, end, step, final_node, is_multiline, loop_until)

            return res.success(final_node)

        else:
            return res.failure(
                InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected 'in', '=', 'to' or 'until' after for loop variable",
                )
            )

    def while_expr(self):
        res = ParseResult()

        if not self.current_tok.matches(TT_KEYWORD, "while"):
            return res.failure(
                InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    f"Expected 'while'",
                )
            )
        res.register_advancement()
        self.advance()

        condition = res.register(self.expr(allow_assignment=False))
        if res.error:
            return res

        if not self.current_tok.matches(TT_KEYWORD, "do"):
            return res.failure(
                InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    f"Expected 'do'",
                )
            )
        res.register_advancement()
        self.advance()

        if self.current_tok.type == TT_NEWLINE:
            res.register_advancement()
            self.advance()
            body = res.register(self.statements())
            if res.error:
                return res
            if not self.current_tok.matches(TT_KEYWORD, "done"):
                return res.failure(
                    InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        f"Expected 'done'",
                    )
                )
            res.register_advancement()
            self.advance()
            return res.success(WhileNode(condition, body, True))

        body = res.register(self.statement())
        if res.error:
            return res
        return res.success(WhileNode(condition, body, False))

    def func_def(self):
        res = ParseResult()
        pos_start = self.current_tok.pos_start.copy()

        if not self.current_tok.matches(TT_KEYWORD, "defun"):
            return res.failure(
                InvalidSyntaxError(
                    pos_start, self.current_tok.pos_end, "Expected 'defun'"
                )
            )
        res.register_advancement()
        self.advance()

        var_name_tok = None
        if self.current_tok.type == TT_IDENTIFIER:
            var_name_tok = self.current_tok
            res.register_advancement()
            self.advance()

        if self.current_tok.type != TT_LPAREN:
            return res.failure(
                InvalidSyntaxError(
                    self.current_tok.pos_start, self.current_tok.pos_end, "Expected '('"
                )
            )
        res.register_advancement()
        self.advance()

        arg_name_toks = []
        defaults = []
        vargs_name_tok = None
        kargs_name_tok = None
        parsing_stage = "args"

        while self.current_tok.type != TT_RPAREN:
            if self.current_tok.type == TT_MUL:
                if parsing_stage != "args":
                    return res.failure(
                        InvalidSyntaxError(
                            self.current_tok.pos_start,
                            self.current_tok.pos_end,
                            "Unexpected '*'",
                        )
                    )
                res.register_advancement()
                self.advance()
                if self.current_tok.type != TT_IDENTIFIER:
                    return res.failure(
                        InvalidSyntaxError(
                            self.current_tok.pos_start,
                            self.current_tok.pos_end,
                            "Expected identifier after '*'",
                        )
                    )
                vargs_name_tok = self.current_tok
                parsing_stage = "vargs"
                res.register_advancement()
                self.advance()

            elif self.current_tok.type == TT_DOUBLE_STAR:
                if parsing_stage == "kargs":
                    return res.failure(
                        InvalidSyntaxError(
                            self.current_tok.pos_start,
                            self.current_tok.pos_end,
                            "Unexpected '**'",
                        )
                    )
                res.register_advancement()
                self.advance()
                if self.current_tok.type != TT_IDENTIFIER:
                    return res.failure(
                        InvalidSyntaxError(
                            self.current_tok.pos_start,
                            self.current_tok.pos_end,
                            "Expected identifier after '**'",
                        )
                    )
                kargs_name_tok = self.current_tok
                parsing_stage = "kargs"
                res.register_advancement()
                self.advance()

            elif self.current_tok.type == TT_IDENTIFIER:
                if parsing_stage in ("vargs", "kargs"):
                    return res.failure(
                        InvalidSyntaxError(
                            self.current_tok.pos_start,
                            self.current_tok.pos_end,
                            "Positional argument cannot follow *vargs or **kargs",
                        )
                    )

                arg_name_toks.append(self.current_tok)
                res.register_advancement()
                self.advance()

                if self.current_tok.type == TT_EQ:
                    res.register_advancement()
                    self.advance()

                    default_value = res.register(self.expr(allow_assignment=False))
                    if res.error:
                        return res
                    defaults.append(default_value)
                else:
                    defaults.append(None)

            else:
                return res.failure(
                    InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        "Expected identifier, '*' or '**'",
                    )
                )

            if self.current_tok.type == TT_COMMA:
                res.register_advancement()
                self.advance()
            elif self.current_tok.type != TT_RPAREN:
                return res.failure(
                    InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        "Expected ',' or ')'",
                    )
                )

        res.register_advancement()
        self.advance()

        if self.current_tok.type == TT_ARROW:
            res.register_advancement()
            self.advance()
            body = res.register(self.expr())
            if res.error:
                return res
            return res.success(
                FuncDefNode(
                    var_name_tok,
                    arg_name_toks,
                    defaults,
                    vargs_name_tok,
                    kargs_name_tok,
                    body,
                    True,
                    [],
                )
            )
        elif self.current_tok.type == TT_NEWLINE:
            res.register_advancement()
            self.advance()
            body = res.register(self.statements())
            if res.error:
                return res
            if not self.current_tok.matches(TT_KEYWORD, "done"):
                return res.failure(
                    InvalidSyntaxError(
                        self.current_tok.pos_start,
                        self.current_tok.pos_end,
                        "Expected 'done' after function body",
                    )
                )
            res.register_advancement()
            self.advance()
            return res.success(
                FuncDefNode(
                    var_name_tok,
                    arg_name_toks,
                    defaults,
                    vargs_name_tok,
                    kargs_name_tok,
                    body,
                    False,
                    [],
                )
            )
        else:
            return res.failure(
                InvalidSyntaxError(
                    self.current_tok.pos_start,
                    self.current_tok.pos_end,
                    "Expected '->' or newline after function parameters",
                )
            )

    def bin_op(self, func_a, ops, func_b=None):
        if func_b is None:
            func_b = func_a

        res = ParseResult()
        left = res.register(func_a())
        if res.error:
            return res

        while self.current_tok and (
            self.current_tok.type in ops
            or (self.current_tok.type, self.current_tok.value) in ops
        ):
            op_tok = self.current_tok
            res.register_advancement()
            self.advance()

            right = res.register(func_b())
            if res.error:
                return res

            left = BinOpNode(left, op_tok, right)

        return res.success(left)
