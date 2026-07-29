import operator
from concurrent.futures import Future as PyFuture
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction
from queue import Queue as PyQueue

from .errors import MError, RTError, TError
from .utils import RTResult


class ThreadPoolError(Exception):
    def __init__(self, err):
        self.err = err
        super().__init__(err)


class Context:
    __slots__ = (
        "display_name",
        "parent",
        "parent_entry_pos",
        "symbol_table",
        "private_symbol_table",
        "using_vars",
        "nonlocal_vars",
    )

    def __init__(self, display_name, parent=None, parent_entry_pos=None):
        self.display_name = display_name
        self.parent = parent
        self.parent_entry_pos = parent_entry_pos
        self.symbol_table = None
        self.private_symbol_table = None
        self.using_vars = set()
        self.nonlocal_vars = set()


class SymbolTable:
    __slots__ = ("symbols", "parent")

    def __init__(self, parent=None):
        self.symbols = {}
        self.parent = parent

    def get(self, name):
        value = self.symbols.get(name, None)
        if value == None and self.parent:
            return self.parent.get(name)
        return value

    def set(self, name, value):
        self.symbols[name] = value

    def change(self, other):
        self.symbols = other.symbols
        self.parent = other.parent

    def remove(self, name):
        del self.symbols[name]

    def exists(self, value):
        return True if value in self.symbols.values() else False

    def copy(self):
        return SymbolTable().change(self)


class Object:
    __slots__ = ("fields", "pos_start", "pos_end", "context")

    def __init__(self):
        self.set_pos()
        self.set_context()
        self.fields = []

    def set_pos(self, pos_start=None, pos_end=None):
        self.pos_start = pos_start
        self.pos_end = pos_end
        return self

    def set_context(self, context=None):
        self.context = context
        return self

    def type(self):
        return "Object"

    def added_to(self, other):
        return None, self.illegal_operation(other)

    def dollared_by(self, other):
        return None, self.illegal_operation(other)

    def subbed_by(self, other):
        return None, self.illegal_operation(other)

    def multed_by(self, other):
        return None, self.illegal_operation(other)

    def dived_by(self, other):
        return None, self.illegal_operation(other)

    def moduled_by(self, other):
        return None, self.illegal_operation(other)

    def powed_by(self, other):
        return None, self.illegal_operation(other)

    def get_comparison_eq(self, other):
        return None, self.illegal_operation(other)

    def get_comparison_ne(self, other):
        return None, self.illegal_operation(other)

    def get_comparison_lt(self, other):
        return None, self.illegal_operation(other)

    def get_comparison_gt(self, other):
        return None, self.illegal_operation(other)

    def get_comparison_lte(self, other):
        return None, self.illegal_operation(other)

    def get_comparison_gte(self, other):
        return None, self.illegal_operation(other)

    def anded_by(self, other):
        return None, self.illegal_operation(other)

    def ored_by(self, other):
        return None, self.illegal_operation(other)

    def notted(self):
        return None, self.illegal_operation()

    def execute(self, _, __):
        return RTResult().failure(
            self.illegal_operation(error_str="Can't call non-function")
        )

    def copy(self):
        raise Exception("No copy method defined")

    def is_true(self):
        return False

    def prequaled_by(self, other: "Object"):
        return None, self.illegal_operation(other)

    def get(self, other):
        return self.illegal_operation(other)

    def iter(self):
        return None, self.illegal_operation(
            error_str="Iteration is not supported for this type"
        )

    def illegal_operation(self, other=None, error_str=None):
        if not other:
            other = self
        return TError(
            self.pos_start,
            other.pos_end,
            f"Illegal operation -> {error_str or 'unknown'}",
            self.context,
        )


class Channel(Object):
    __slots__ = ("queue",)

    def __init__(self, queue_instance=None):
        super().__init__()
        self.queue = queue_instance if queue_instance else PyQueue()

    def copy(self):
        return self

    def type(self):
        return "<channel>"

    def __repr__(self):
        return f"<channel size={self.queue.qsize()}>"


class ThreadWrapper(Object):
    __slots__ = "thread"

    def __init__(self, thread):
        super().__init__()
        self.thread = thread

    def copy(self):
        copy = ThreadWrapper(self.thread)
        copy.set_pos(self.pos_start, self.pos_end)
        copy.set_context(self.context)
        return copy

    def type(self):
        return "<thread>"

    def __str__(self):
        return f"<thread id={self.thread.ident} active={self.thread.is_alive()}>"

    def __repr__(self):
        return self.__str__()

    def join(self, timeout=None):
        return self.thread.join(timeout)

    def is_alive(self):
        return self.thread.is_alive()

    def cancel(self):
        if self.thread.is_alive():
            self.thread._stop()

    def type(self):
        return "<thread>"


class NoneObject(Object):
    __slots__ = "value"

    def __init__(self, value):
        super().__init__()
        self.value = value

    def copy(self):
        copy = NoneObject(self.value)
        copy.set_pos(self.pos_start, self.pos_end)
        copy.set_context(self.context)
        return copy

    def is_true(self):
        return False

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self):
        return str(self.value).lower()

    def type(self):
        return "<none>"

    def get_comparison_eq(self, other):
        if isinstance(other, NoneObject):
            return Number.true.set_context(self.context), None
        return Number.false.set_context(self.context), None

    def get_comparison_ne(self, other):
        if isinstance(other, NoneObject):
            return Number.false.set_context(self.context), None
        return Number.true.set_context(self.context), None

    def notted(self):
        return Number.true.set_context(self.context)

    def anded_by(self, other):
        if not isinstance(other, NoneObject) and not isinstance(other, Bool):
            return None, None
        return Bool(self.value and other.value).set_context(self.context), None

    def ored_by(self, other):
        if not isinstance(other, NoneObject) and not isinstance(other, Bool):
            return None, None
        return Bool(self.value or other.value).set_context(self.context), None


NoneObject.none = NoneObject("none")


class Bool(Object):
    __slots__ = ("value",)

    def __init__(self, value):
        super().__init__()
        self.value = bool(value)

    def copy(self):
        copy = Bool(self.value)
        copy.set_pos(self.pos_start, self.pos_end)
        copy.set_context(self.context)
        return copy

    def is_true(self):
        return self.value

    def type(self):
        return "<bool>"

    def notted(self):
        return Bool(not self.value).set_context(self.context), None

    def anded_by(self, other):
        if not isinstance(other, Bool):
            return None, None
        return Bool(self.value and other.value).set_context(self.context), None

    def ored_by(self, other):
        if not isinstance(other, Bool):
            return None, None
        return Bool(self.value or other.value).set_context(self.context), None

    def _get_comparison_result(self, other, op):
        if (
            isinstance(other, Bool)
            and not isinstance(self, NoneObject)
            and not isinstance(other, NoneObject)
        ):
            result = bool(op(self.value, other.value))
            return Bool(result).set_context(self.context), None

        if isinstance(self, NoneObject):
            if isinstance(other, NoneObject):
                result = op in (operator.eq, operator.le, operator.ge)
            else:
                result = op is operator.ne
            return Bool(result).set_context(self.context), None

        return Bool(op is operator.ne).set_context(self.context), None

    def get_comparison_eq(self, other):
        return self._get_comparison_result(other, operator.eq)

    def get_comparison_ne(self, other):
        return self._get_comparison_result(other, operator.ne)

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self):
        return str(self.value).lower()


Bool.true = Bool(True)
Bool.false = Bool(False)


class CFloat(Object):
    __slots__ = ("value", "context", "pos_start", "pos_end", "fields")

    def __init__(self, value, context=None, pos_start=None, pos_end=None):
        if isinstance(value, Fraction):
            self.value = value
        else:
            self.value = Fraction(str(value))

        self.context = context
        self.pos_start = pos_start
        self.pos_end = pos_end
        self.fields = []

    def set_context(self, context=None):
        self.context = context
        return self

    def copy(self):
        return CFloat(self.value, self.context, self.pos_start, self.pos_end)

    def _convert_to_fraction(self, other):
        if isinstance(other, CFloat):
            return other.value
        if isinstance(other, Number):
            if isinstance(other.value, int):
                return Fraction(other.value)
            try:
                return Fraction(str(other.value))
            except (ValueError, ZeroDivisionError, TypeError):
                return None
        return None

    def added_to(self, other):
        other_frac = self._convert_to_fraction(other)
        if other_frac is not None:
            result = self.value + other_frac
            return CFloat(result).set_context(self.context), None
        return None, Object.illegal_operation(
            other, f"Can't add cfloat to '{other.type()}'"
        )

    def subbed_by(self, other):
        other_frac = self._convert_to_fraction(other)
        if other_frac is not None:
            result = self.value - other_frac
            return CFloat(result).set_context(self.context), None
        return None, Object.illegal_operation(
            other, f"Can't subtract cfloat from '{other.type()}'"
        )

    def multed_by(self, other):
        other_frac = self._convert_to_fraction(other)
        if other_frac is not None:
            result = self.value * other_frac
            return CFloat(result).set_context(self.context), None
        return None, Object.illegal_operation(
            other, f"Can't multiply cfloat by '{other.type()}'"
        )

    def dived_by(self, other):
        other_frac = self._convert_to_fraction(other)
        if other_frac is not None:
            if other_frac == 0:
                return None, RTError(
                    other.pos_start, other.pos_end, "Division by zero", self.context
                )
            result = self.value / other_frac
            return CFloat(result).set_context(self.context), None
        return None, Object.illegal_operation(
            other, f"Can't divide cfloat by '{other.type()}'"
        )

    def moduled_by(self, other):
        other_frac = self._convert_to_fraction(other)
        if other_frac is not None:
            if other_frac == 0:
                return None, RTError(
                    other.pos_start, other.pos_end, "Division by zero", self.context
                )
            result = self.value % other_frac
            return CFloat(result).set_context(self.context), None
        return None, Object.illegal_operation(
            other, f"Can't mod cfloat by '{other.type()}'"
        )

    def powed_by(self, other):
        other_frac = self._convert_to_fraction(other)
        if other_frac is not None:
            try:
                result = self.value**other_frac
                if isinstance(result, complex):
                    return None, MError(
                        self.pos_start,
                        self.pos_end,
                        "Math domain error (imaginary numbers are not supported)",
                        self.context,
                    )
                return CFloat(result).set_context(self.context), None
            except (ValueError, OverflowError, ZeroDivisionError):
                return None, MError(
                    self.pos_start,
                    self.pos_end,
                    "Math domain error",
                    self.context,
                )
        return None, Object.illegal_operation(
            other, f"Can't power cfloat by '{other.type()}'"
        )

    def floordived_by(self, other):
        other_frac = self._convert_to_fraction(other)
        if other_frac is not None:
            if other_frac == 0:
                return None, MError(
                    other.pos_start, other.pos_end, "Division by zero", self.context
                )
            result = self.value // other_frac
            return Number(int(result)).set_context(self.context), None
        return None, Object.illegal_operation(
            other, f"Can't floor divide cfloat by '{other.type()}'"
        )

    def _get_comparison_result(self, other, op):
        other_frac = self._convert_to_fraction(other)
        if other_frac is not None and not isinstance(self, NoneObject):
            return Bool(op(self.value, other_frac)).set_context(self.context), None

        if isinstance(self, NoneObject):
            is_none_other = isinstance(other, NoneObject)
            if op == operator.eq:
                return Bool(is_none_other).set_context(self.context), None
            if op == operator.ne:
                return Bool(not is_none_other).set_context(self.context), None

        return None, Object.illegal_operation(
            other, f"Can't compare cfloat with '{other.type()}'"
        )

    def get_comparison_eq(self, other):
        return self._get_comparison_result(other, operator.eq)

    def get_comparison_ne(self, other):
        return self._get_comparison_result(other, operator.ne)

    def get_comparison_lt(self, other):
        return self._get_comparison_result(other, operator.lt)

    def get_comparison_gt(self, other):
        return self._get_comparison_result(other, operator.gt)

    def get_comparison_lte(self, other):
        return self._get_comparison_result(other, operator.le)

    def get_comparison_gte(self, other):
        return self._get_comparison_result(other, operator.ge)

    def anded_by(self, other):
        if not isinstance(other, (Number, CFloat)):
            return None, Object.illegal_operation(
                other, f"Can't perform logical AND on cfloat and '{other.type()}'"
            )
        return Bool(self.is_true() and other.is_true()).set_context(self.context), None

    def ored_by(self, other):
        if not isinstance(other, (Number, CFloat)):
            return None, Object.illegal_operation(
                other, f"Can't perform logical OR on cfloat and '{other.type()}'"
            )
        return Bool(self.is_true() or other.is_true()).set_context(self.context), None

    def notted(self):
        return Bool(not self.is_true()).set_context(self.context), None

    def is_true(self):
        return self.value != 0 if not isinstance(self, NoneObject) else False

    def type(self):
        return "<cfloat>"

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        if isinstance(self, NoneObject):
            return "none"
        if self.value.denominator == 1:
            return str(self.value.numerator)
        return str(float(self.value))


class Number(Object):
    __slots__ = ("value", "context", "pos_start", "pos_end", "fields")

    def __init__(self, value, context=None, pos_start=None, pos_end=None):
        self.value = value
        self.context = context
        self.pos_start = pos_start
        self.pos_end = pos_end
        self.fields = []

    def set_context(self, context=None):
        self.context = context
        return self

    def copy(self):
        return Number(self.value, self.context, self.pos_start, self.pos_end)

    def _convert_value(self, other):
        if isinstance(other, Number):
            return other.value
        elif isinstance(other, CFloat):
            return float(other.value)
        return None

    def added_to(self, other):
        other_value = self._convert_value(other)
        if other_value is not None:
            return Number(self.value + other_value).set_context(self.context), None
        return None, Object.illegal_operation(
            other, f"Can't add number to '{other.type()}'"
        )

    def subbed_by(self, other):
        other_value = self._convert_value(other)
        if other_value is not None:
            return Number(self.value - other_value).set_context(self.context), None
        return None, Object.illegal_operation(
            other, f"Can't subtract number from '{other.type()}'"
        )

    def multed_by(self, other):
        other_value = self._convert_value(other)
        if other_value is not None:
            return Number(self.value * other_value).set_context(self.context), None
        return None, Object.illegal_operation(
            other, f"Can't multiply number by '{other.type()}'"
        )

    def dived_by(self, other):
        other_value = self._convert_value(other)
        if other_value is not None:
            if other_value == 0:
                return None, RTError(
                    other.pos_start, other.pos_end, "Division by zero", self.context
                )
            return Number(self.value / other_value).set_context(self.context), None
        return None, Object.illegal_operation(
            other, f"Can't divide number by '{other.type()}'"
        )

    def moduled_by(self, other):
        other_value = self._convert_value(other)
        if other_value is not None:
            if other_value == 0:
                return None, RTError(
                    other.pos_start, other.pos_end, "Division by zero", self.context
                )
            return Number(self.value % other_value).set_context(self.context), None
        return None, Object.illegal_operation(
            other, f"Can't mod number by '{other.type()}'"
        )

    def powed_by(self, other):
        other_value = self._convert_value(other)
        if other_value is not None:
            try:
                result = self.value**other_value
                if isinstance(result, complex):
                    return None, MError(
                        self.pos_start,
                        self.pos_end,
                        "Math domain error (imaginary numbers are not supported)",
                        self.context,
                    )
                return Number(result).set_context(self.context), None
            except (ValueError, OverflowError, ZeroDivisionError):
                return None, MError(
                    self.pos_start, self.pos_end, "Math domain error", self.context
                )
        return None, Object.illegal_operation(
            other, f"Can't power number by '{other.type()}'"
        )

    def floordived_by(self, other):
        other_value = self._convert_value(other)
        if other_value is not None:
            if other_value == 0:
                return None, MError(
                    other.pos_start, other.pos_end, "Division by zero", self.context
                )
            return Number(self.value // other_value).set_context(self.context), None
        return None, Object.illegal_operation(
            other, f"Can't floor divide number by '{other.type()}'"
        )

    def _get_comparison_result(self, other, op):
        other_value = self._convert_value(other)
        if other_value is not None and not isinstance(self, NoneObject):
            return Bool(op(self.value, other_value)).set_context(self.context), None
        if isinstance(self, NoneObject):
            if isinstance(other, NoneObject):
                result = op in (operator.eq, operator.le, operator.ge)
            else:
                result = op is operator.ne
            return Bool(result).set_context(self.context), None
        return Bool(op is operator.ne).set_context(self.context), None

    def get_comparison_eq(self, other):
        return self._get_comparison_result(other, operator.eq)

    def get_comparison_ne(self, other):
        return self._get_comparison_result(other, operator.ne)

    def get_comparison_lt(self, other):
        return self._get_comparison_result(other, operator.lt)

    def get_comparison_gt(self, other):
        return self._get_comparison_result(other, operator.gt)

    def get_comparison_lte(self, other):
        return self._get_comparison_result(other, operator.le)

    def get_comparison_gte(self, other):
        return self._get_comparison_result(other, operator.ge)

    def anded_by(self, other):
        if not isinstance(other, (Number, CFloat)):
            return None, Object.illegal_operation(
                other, f"Can't perform logical AND on number and '{other.type()}'"
            )
        if isinstance(self, NoneObject) or isinstance(other, NoneObject):
            return None, TError(
                self.pos_start,
                self.pos_end,
                "Can't perform logical operation with 'none'",
                self.context,
            )
        return (
            Bool((self.value != 0) and (other.value != 0)).set_context(self.context),
            None,
        )

    def ored_by(self, other):
        if not isinstance(other, (Number, CFloat)):
            return None, Object.illegal_operation(
                other, f"Can't perform logical OR on number and '{other.type()}'"
            )
        if isinstance(self, NoneObject) or isinstance(other, NoneObject):
            return None, TError(
                self.pos_start,
                self.pos_end,
                "Can't perform logical operation with 'none'",
                self.context,
            )
        return (
            Bool((self.value != 0) or (other.value != 0)).set_context(self.context),
            None,
        )

    def notted(self):
        if isinstance(self, NoneObject):
            return None, TError(
                self.pos_start,
                self.pos_end,
                "Can't perform logical operation with 'none'",
                self.context,
            )
        return Bool(not bool(self.value)).set_context(self.context), None

    def is_true(self):
        return bool(self.value) if not isinstance(self, NoneObject) else False

    def type(self):
        if isinstance(self.value, int):
            return "<int>"
        elif isinstance(self.value, float):
            return "<float>"
        elif isinstance(self, NoneObject):
            return "<none>"

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        if isinstance(self, NoneObject):
            return "none"
        if isinstance(self.value, bool):
            return "true" if self.value else "false"
        s = str(self.value)
        if "e" in s or "E" in s:
            return s.replace("e", "*10^(").replace("E", "*10^(") + ")"
        return s


Number.false = Bool.false
Number.true = Bool.true
Number.none = NoneObject.none


class String(Object):
    __slots__ = "value"

    def __init__(self, value):
        super().__init__()
        self.value = value
        self.fields = ["size"]

    def __len__(self):
        return len(self.value)

    def __iter__(self):
        return iter(self.value)

    def added_to(self, other):
        if isinstance(other, String):
            return String(self.value + other.value).set_context(self.context), None
        else:
            return None, self.illegal_operation(
                other, f"Can't add string to '{other.type()}'"
            )

    def multed_by(self, other):
        if isinstance(other, Number):
            return String(self.value * other.value).set_context(self.context), None
        else:
            return None, self.illegal_operation(
                other, f"Can't multiply string by '{other.type()}'"
            )

    def _make_comparison(self, other, op, type_to_check):
        if isinstance(other, type_to_check):
            result = bool(op(self.value, other.value))
            return Bool(result).set_context(self.context), None
        default_result = True if op is operator.ne else False
        return Bool(default_result).set_context(self.context), None

    def get_comparison_eq(self, other):
        return self._make_comparison(other, operator.eq, String)

    def get_comparison_ne(self, other):
        return self._make_comparison(other, operator.ne, String)

    def is_true(self):
        return len(self.value) > 0

    def copy(self):
        copy = String(self.value)
        copy.set_pos(self.pos_start, self.pos_end)
        copy.set_context(self.context)
        return copy

    def type(self):
        return "<str>"

    def __str__(self):
        return self.value

    def dollared_by(self, index):
        if not isinstance(index, Number):
            return None, self.illegal_operation(index, "Index must be a number")
        try:
            return String(self.value[index.value]), None
        except IndexError:
            return None, RTError(
                index.pos_start,
                index.pos_end,
                f"Index {index.value} is out of bounds for string of size {len(self.value)}",
                self.context,
            )

    def iter(self):
        return iter([String(ch) for ch in self.value]), None

    def __repr__(self):
        return repr(self.value)


class PyObject(Object):
    __slots__ = "value"

    def __init__(self, obj):
        super().__init__()
        self.value = obj

    def get_obj(self):
        return self.value

    def copy(self):
        c = PyObject(self.value)
        c.set_pos(self.pos_start, self.pos_end)
        c.set_context(self.context)
        return c

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self):
        return f"<py-obj {self.value}>"

    def type(self):
        return "<py-obj>"


class List(Object):
    __slots__ = "value"

    def __init__(self, value):
        super().__init__()
        self.value = value

    def added_to(self, other):
        new_list = self.copy()
        new_list.value.append(other)
        return new_list, None

    def subbed_by(self, other):
        if isinstance(other, Number):
            new_list = self.copy()
            try:
                new_list.value.pop(other.value)
                return new_list, None
            except:
                return None, RTError(
                    other.pos_start,
                    other.pos_end,
                    f"Index {other.value} is out of bounds for list of size {len(self.value)}",
                    self.context,
                )
        else:
            return None, self.illegal_operation(
                other, f"Can't subtract list by '{other.type()}'"
            )

    def multed_by(self, other):
        if isinstance(other, List):
            new_list = self.copy()
            new_list.value.extend(other.value)
            return new_list, None
        elif isinstance(other, Number):
            new_list = self.copy()
            new_list.value = self.value * other.value
            return new_list, None
        else:
            return None, self.illegal_operation(
                other, f"Can't multiply list by '{other.type()}'"
            )

    def dollared_by(self, other):
        if isinstance(other, Number):
            try:
                return self.value[other.value], None
            except IndexError:
                return None, RTError(
                    other.pos_start,
                    other.pos_end,
                    f"Index {other.value} is out of bounds for list of size {len(self.value)}",
                    self.context,
                )
        else:
            return None, self.illegal_operation(other, "Index must be a number")

    def copy(self):
        copy = List(self.value[:])
        copy.set_pos(self.pos_start, self.pos_end)
        copy.set_context(self.context)
        return copy

    def get_comparison_eq(self, other):
        if not isinstance(other, List):
            return Number.false.set_context(self.context), None
        if len(self.value) != len(other.value):
            return Number.false.set_context(self.context), None

        for i in range(len(self.value)):
            cmp, err = self.value[i].get_comparison_eq(other.value[i])
            if err:
                return None, err
            if not cmp.is_true():
                return Number.false.set_context(self.context), None
        return Number.true.set_context(self.context), None

    def get_comparison_ne(self, other):
        eq_result, _ = self.get_comparison_eq(other)
        if eq_result == Number.true:
            return Number.false.set_context(self.context), None
        return Number.true.set_context(self.context), None

    def is_true(self):
        return len(self.value) > 0

    def type(self):
        return "<list>"

    def iter(self):
        return iter(self.value), None

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self) -> str:
        return str(self.value)


class HashMap(Object):
    __slots__ = "value"

    def __init__(self, value):
        super().__init__()
        self.value: dict[str, Object] = {}
        if isinstance(value, HashMap):
            raw = value.value
        elif isinstance(value, dict):
            raw = value
        else:
            raw = {}

        for k, v in raw.items():
            key_str = str(k)
            self.value[key_str] = v

    def is_true(self):
        return len(self.value) > 0

    def added_to(self, other):
        if not isinstance(other, HashMap):
            return None, self.illegal_operation(other)

        new_map_value = self.value.copy()
        for key, value in other.value.items():
            new_map_value[key] = value

        return HashMap(new_map_value), None

    def type(self):
        return "<hashmap>"

    def dollared_by(self, index):
        if not isinstance(index, String):
            return None, self.illegal_operation(index)

        try:
            return self.value[index.value], None
        except KeyError:
            return None, RTError(
                index.pos_start,
                index.pos_end,
                "Key not found in hashmap",
                self.context,
            )

    def get_index(self, index):
        if not isinstance(index, String):
            return None, self.illegal_operation(index)
        try:
            return self.value[index.value], None
        except KeyError:
            return None, RTError(
                index.pos_start,
                index.pos_end,
                "Key not found in hashmap",
                self.context,
            )

    def set_index(self, index, value):
        if not isinstance(index, String):
            return None, self.illegal_operation(index)
        new_value = self.value.copy()
        new_value[index.value] = value
        return HashMap(new_value)

    def iter(self):
        pairs = [List([String(str(k)), v]) for k, v in self.value.items()]
        return iter(pairs), None

    def get_comparison_eq(self, other):
        if not isinstance(other, HashMap):
            return Number.false.set_context(self.context), None
        if len(self.value) != len(other.value):
            return Number.false.set_context(self.context), None

        for key, value in self.value.items():
            if key not in other.value:
                return Number.false.set_context(self.context), None
            cmp, err = value.get_comparison_eq(other.value[key])
            if err:
                return None, err
            if not cmp.is_true():
                return Number.false.set_context(self.context), None
        return Number.true.set_context(self.context), None

    def get_comparison_ne(self, other):
        eq_result, _ = self.get_comparison_eq(other)
        if eq_result == Number.true:
            return Number.false.set_context(self.context), None
        return Number.true.set_context(self.context), None

    def __len__(self) -> int:
        return len(self.value)

    def copy(self):
        copied_map = HashMap(self.value.copy())
        copied_map.set_pos(self.pos_start, self.pos_end)
        copied_map.set_context(self.context)
        return copied_map

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self) -> str:
        return str(self.value)


class File(Object):
    __slots__ = ("name", "path")

    def __init__(self, name, path):
        super().__init__()
        self.name = name
        self.path = path

    def _make_comparison(self, other, op, type_to_check):
        if isinstance(other, type_to_check):
            result = bool(op(self.path, other.path))
            return Bool(result).set_context(self.context), None
        default_result = True if op is operator.ne else False
        return Bool(default_result).set_context(self.context), None

    def get_comparison_eq(self, other):
        return self._make_comparison(other, operator.eq, File)

    def get_comparison_ne(self, other):
        return self._make_comparison(other, operator.ne, File)

    def copy(self):
        copy = File(self.name, self.path)
        copy.set_pos(self.pos_start, self.pos_end)
        copy.set_context(self.context)
        return copy

    def type(self):
        return "<file>"

    def __repr__(self):
        return f"<file {self.name}>"


class NameSpace(Object):
    __slots__ = ("name", "value", "_internal")

    def __init__(self, name):
        super().__init__()
        self.name = name

        self.value = HashMap({})

        self._internal = {
            "context_": Number.none,
            "statements_": Number.none,
            "initialized_": Number.false,
        }

    def get(self, name, checked=False):
        if name in self._internal and checked:
            return self._internal[name]

        r, err = self.value.dollared_by(String(name))
        if err:
            return None
        return r

    def set(self, name, value, checked=False):
        if name in self._internal and checked:
            self._internal[name] = value
        else:
            self.value = self.value.set_index(String(name), value)
        return self

    def copy(self):
        copied_ns = NameSpace(self.name)
        copied_ns.value = self.value.copy()
        copied_ns._internal = self._internal.copy()
        copied_ns.set_pos(self.pos_start, self.pos_end)
        copied_ns.set_context(self.context)
        return copied_ns

    def type(self):
        return "<namespace>"

    def __repr__(self):
        return f"<namespace {self.name}>"


class Bytes(Object):
    __slots__ = ("value",)

    def __init__(self, value):
        super().__init__()
        self.value = value

    def added_to(self, other):
        if isinstance(other, Bytes):
            return Bytes(self.value + other.value).set_context(self.context), None
        return None, self.illegal_operation(other)

    def get_comparison_eq(self, other):
        if isinstance(other, Bytes):
            return Bool(self.value == other.value).set_context(self.context), None
        return Number.false.set_context(self.context), None

    def get_comparison_ne(self, other):
        if isinstance(other, Bytes):
            return Bool(self.value != other.value).set_context(self.context), None
        return Number.true.set_context(self.context), None

    def dollared_by(self, index):
        if not isinstance(index, Number):
            return None, self.illegal_operation(index)
        try:
            return Number(self.value[index.value]).set_context(self.context), None
        except IndexError:
            return None, RTError(
                index.pos_start,
                index.pos_end,
                f"Index {index.value} is out of bounds for bytes of size {len(self.value)}",
                self.context,
            )

    def copy(self):
        copy = Bytes(self.value)
        copy.set_pos(self.pos_start, self.pos_end)
        copy.set_context(self.context)
        return copy

    def iter(self):
        pairs = [Number(i) for i in self.value]
        return iter(pairs), None

    def is_true(self):
        return len(self.value) > 0

    def type(self):
        return "<bytes>"

    def __str__(self):
        return self.value.hex()

    def __repr__(self):
        return self.value.hex()


class ThreadPool(Object):
    __slots__ = ("executor",)

    def __init__(self, max_workers):
        super().__init__()
        self.executor = ThreadPoolExecutor(max_workers=max_workers)

    def copy(self):
        return self

    def type(self):
        return "<thread-pool>"

    def __repr__(self):
        return f"<thread-pool max_workers={self.executor._max_workers}>"


class Future(Object):
    __slots__ = ("future",)

    def __init__(self, future: PyFuture):
        super().__init__()
        self.future = future

    def copy(self):
        return self

    def type(self):
        return "<future>"

    def __repr__(self):
        return f"<future state={self.future._state}>"
