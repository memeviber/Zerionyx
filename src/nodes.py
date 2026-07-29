class NumberNode:
    __slots__ = ["tok", "pos_start", "pos_end"]

    def __init__(self, tok):
        self.tok = tok
        self.pos_start = self.tok.pos_start
        self.pos_end = self.tok.pos_end

    def __repr__(self):
        return f"{self.tok}"

    def __str__(self):
        return f"NumberNode({self.tok.value})"


class StringNode:
    __slots__ = ["tok", "pos_start", "pos_end"]

    def __init__(self, tok):
        self.tok = tok
        self.pos_start = self.tok.pos_start
        self.pos_end = self.tok.pos_end

    def __repr__(self):
        return f"{self.tok}"

    def __str__(self):
        return f'StringNode("{self.tok.value}")'


class ListNode:
    __slots__ = ["element_nodes", "pos_start", "pos_end"]

    def __init__(self, element_nodes, pos_start, pos_end):
        self.element_nodes = element_nodes
        self.pos_start = pos_start
        self.pos_end = pos_end

    def __str__(self):
        return f"ListNode({', '.join(str(x) for x in self.element_nodes)})"


class VarAccessNode:
    __slots__ = ["var_name_tok", "pos_start", "pos_end"]

    def __init__(self, var_name_tok):
        self.var_name_tok = var_name_tok
        self.pos_start = self.var_name_tok.pos_start
        self.pos_end = self.var_name_tok.pos_end

    def __str__(self):
        return f"VarAccessNode({self.var_name_tok.value})"


class VarAssignNode:
    __slots__ = ["var_name_tok", "value_node", "pos_start", "pos_end"]

    def __init__(self, var_name_tok, value_node):
        self.var_name_tok = var_name_tok
        self.value_node = value_node
        self.pos_start = self.var_name_tok.pos_start
        self.pos_end = self.value_node.pos_end

    def __str__(self):
        return f"VarAssignNode({self.var_name_tok.value} = {self.value_node})"


class BinOpNode:
    __slots__ = ["left_node", "op_tok", "right_node", "pos_start", "pos_end"]

    def __init__(self, left_node, op_tok, right_node):
        self.left_node = left_node
        self.op_tok = op_tok
        self.right_node = right_node
        self.pos_start = self.left_node.pos_start
        self.pos_end = self.right_node.pos_end

    def __repr__(self):
        return f"({self.left_node}, {self.op_tok}, {self.right_node})"

    def __str__(self):
        return f"BinOpNode({self.left_node} {self.op_tok.type} {self.right_node})"


class UnaryOpNode:
    __slots__ = ["op_tok", "node", "pos_start", "pos_end"]

    def __init__(self, op_tok, node):
        self.op_tok = op_tok
        self.node = node
        self.pos_start = self.op_tok.pos_start
        self.pos_end = node.pos_end

    def __repr__(self):
        return f"({self.op_tok}, {self.node})"

    def __str__(self):
        return f"UnaryOpNode({self.op_tok.type}{self.node})"


class IfNode:
    __slots__ = ["cases", "else_case", "pos_start", "pos_end"]

    def __init__(self, cases, else_case):
        self.cases = cases
        self.else_case = else_case
        self.pos_start = self.cases[0][0].pos_start
        self.pos_end = (self.else_case or self.cases[len(self.cases) - 1])[0].pos_end

    def __str__(self):
        result = "IfNode("
        for condition, expr, _ in self.cases:
            result += f"\nif {condition} do {expr}"
        if self.else_case:
            expr, _ = self.else_case
            result += f"\nelse {expr}"
        return result + ")"


class ForNode:
    __slots__ = [
        "var_name_tok",
        "start_value_node",
        "end_value_node",
        "step_value_node",
        "body_node",
        "should_return_none",
        "until",
        "pos_start",
        "pos_end",
    ]

    def __init__(
        self,
        var_name_tok,
        start_value_node,
        end_value_node,
        step_value_node,
        body_node,
        should_return_none,
        until,
    ):
        self.var_name_tok = var_name_tok
        self.start_value_node = start_value_node
        self.end_value_node = end_value_node
        self.step_value_node = step_value_node
        self.body_node = body_node
        self.should_return_none = should_return_none
        self.until = until
        self.pos_start = self.var_name_tok.pos_start

        if body_node:
            self.pos_end = self.body_node.pos_end
        elif step_value_node:
            self.pos_end = self.step_value_node.pos_end
        else:
            self.pos_end = self.end_value_node.pos_end

    def __str__(self):
        return (
            f"ForNode({self.var_name_tok.value} from {self.start_value_node}"
            + ("to" if not self.until else "until")
            + f"{self.end_value_node} step {self.step_value_node} do {self.body_node})"
        )


class WhileNode:
    __slots__ = [
        "condition_node",
        "body_node",
        "should_return_none",
        "pos_start",
        "pos_end",
    ]

    def __init__(self, condition_node, body_node, should_return_none):
        self.condition_node = condition_node
        self.body_node = body_node
        self.should_return_none = should_return_none
        self.pos_start = self.condition_node.pos_start
        self.pos_end = self.body_node.pos_end

    def __str__(self):
        return f"WhileNode(while {self.condition_node} do {self.body_node})"


class FuncDefNode:
    def __init__(
        self,
        var_name_tok,
        arg_name_toks,
        defaults,
        vargs_name_tok,
        kargs_name_tok,
        body_node,
        should_auto_return,
        decorator_nodes,
    ):
        self.var_name_tok = var_name_tok
        self.arg_name_toks = arg_name_toks
        self.defaults = defaults
        self.vargs_name_tok = vargs_name_tok
        self.kargs_name_tok = kargs_name_tok
        self.body_node = body_node
        self.should_auto_return = should_auto_return
        self.decorator_nodes = decorator_nodes

        if self.var_name_tok:
            self.pos_start = self.var_name_tok.pos_start
        elif len(self.arg_name_toks) > 0:
            self.pos_start = self.arg_name_toks[0].pos_start
        else:
            self.pos_start = self.body_node.pos_start
        self.pos_end = self.body_node.pos_end


class VargsUnpackNode:
    __slots__ = ["node_to_unpack", "pos_start", "pos_end"]

    def __init__(self, node_to_unpack):
        self.node_to_unpack = node_to_unpack
        self.pos_start = node_to_unpack.pos_start
        self.pos_end = node_to_unpack.pos_end


class KargsUnpackNode:
    __slots__ = ["node_to_unpack", "pos_start", "pos_end"]

    def __init__(self, node_to_unpack):
        self.node_to_unpack = node_to_unpack
        self.pos_start = node_to_unpack.pos_start
        self.pos_end = node_to_unpack.pos_end


class CallNode:
    def __init__(self, node_to_call, arg_nodes, pos_start=None, pos_end=None):
        self.node_to_call = node_to_call
        self.arg_nodes = arg_nodes
        self.pos_start = pos_start or node_to_call.pos_start
        self.pos_end = pos_end or (
            arg_nodes[-1].pos_end if arg_nodes else node_to_call.pos_end
        )

    def __repr__(self):
        return f"(Call: {self.node_to_call} with {self.arg_nodes})"


class ReturnNode:
    __slots__ = ["node_to_return", "pos_start", "pos_end"]

    def __init__(self, node_to_return, pos_start, pos_end):
        self.node_to_return = node_to_return
        self.pos_start = pos_start
        self.pos_end = pos_end

    def __str__(self):
        return f"ReturnNode({self.node_to_return})"


class ContinueNode:
    __slots__ = ["pos_start", "pos_end"]

    def __init__(self, pos_start, pos_end):
        self.pos_start = pos_start
        self.pos_end = pos_end

    def __str__(self):
        return "ContinueNode()"


class BreakNode:
    __slots__ = ["pos_start", "pos_end"]

    def __init__(self, pos_start, pos_end):
        self.pos_start = pos_start
        self.pos_end = pos_end

    def __str__(self):
        return "BreakNode()"


class AccessNode:
    def __init__(self, obj, index):
        self.obj = obj
        self.index = index

    def __str__(self):
        return f"AccessNode({self.obj}[{self.index}])"


class LoadNode:
    __slots__ = ["module_name_tok", "file_path", "pos_start", "pos_end"]

    def __init__(self, module_name_tok):
        self.module_name_tok = module_name_tok
        self.file_path = module_name_tok.value
        self.pos_start = self.module_name_tok.pos_start
        self.pos_end = self.module_name_tok.pos_end

    def __str__(self):
        return f'LoadNode("{self.file_path}")'


class HashMapNode:
    __slots__ = ["pairs", "pos_start", "pos_end"]

    def __init__(self, pairs, pos_start, pos_end):
        self.pairs = pairs
        self.pos_start = pos_start
        self.pos_end = pos_end

    def __str__(self):
        return f"HashMapNode({', '.join(f'{k}: {v}' for k, v in self.pairs)})"


class ForInNode:
    __slots__ = [
        "var_name_toks",
        "iterable_node",
        "body_node",
        "pos_start",
        "pos_end",
        "should_return_none",
    ]

    def __init__(
        self,
        var_name_toks,
        iterable_node,
        body_node,
        should_return_none,
        pos_start=None,
        pos_end=None,
    ):
        self.var_name_toks = var_name_toks
        self.iterable_node = iterable_node
        self.body_node = body_node
        self.should_return_none = should_return_none
        self.pos_start = pos_start
        self.pos_end = pos_end

    def __str__(self):
        var_names = ", ".join(tok.value for tok in self.var_name_toks)
        return f"ForInNode({var_names} in {self.iterable_node} do {self.body_node})"


class NameSpaceNode:
    __slots__ = ["namespace_name", "statements", "pos_start", "pos_end"]

    def __init__(self, namespace_name, statements, pos_start, pos_end):
        self.namespace_name = (
            namespace_name if isinstance(namespace_name, str) else namespace_name.value
        )
        self.statements = statements
        self.pos_start = pos_start
        self.pos_end = pos_end

    def __repr__(self):
        return f"NameSpaceNode({self.namespace_name}, {self.statements})"


class MemberAccessNode:
    __slots__ = ["object_node", "member_name", "pos_start", "pos_end"]

    def __init__(self, object_node, member_name, pos_start, pos_end):
        self.object_node = object_node
        self.member_name = member_name
        self.pos_start = pos_start
        self.pos_end = pos_end

    def __repr__(self):
        return f"(MemberAccessNode {self.object_node}.{self.member_name})"


class NamedArgumentNode:
    def __init__(self, param_name_tok, value_node, pos_start=None, pos_end=None):
        self.param_name_tok = param_name_tok
        self.value_node = value_node
        self.pos_start = pos_start or param_name_tok.pos_start
        self.pos_end = pos_end or value_node.pos_end

    def __repr__(self):
        return f"(NamedArg: {self.param_name_tok.value} = {self.value_node})"


class UsingNode:
    def __init__(self, var_name_toks, pos_start, pos_end):
        self.var_name_toks = var_name_toks
        self.pos_start = pos_start
        self.pos_end = pos_end

    def __repr__(self):
        return f"UsingNode({self.var_name_toks})"


class UsingParentNode:
    def __init__(self, var_name_toks, pos_start, pos_end):
        self.var_name_toks = var_name_toks
        self.pos_start = pos_start
        self.pos_end = pos_end

    def __repr__(self):
        return f"UsingParentNode({self.var_name_toks})"


class DelNode:
    def __init__(self, var_name_toks, pos_start, pos_end):
        self.var_name_toks = var_name_toks
        self.pos_start = pos_start
        self.pos_end = pos_end

    def __repr__(self):
        return f"DelNode({self.var_name_toks})"


class IndexAssignNode:
    def __init__(self, obj_node, index_node, value_node):
        self.obj_node = obj_node
        self.index_node = index_node
        self.value_node = value_node

        self.pos_start = self.obj_node.pos_start
        self.pos_end = self.value_node.pos_end

    def __repr__(self):
        return (
            f"IndexAssignNode({self.obj_node} [{self.index_node}] = {self.value_node})"
        )
