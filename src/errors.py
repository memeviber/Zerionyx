from colorama import Fore, Style, init

init(autoreset=True, strip=False)


def get_line_from_text(text, line_number):
    if not text:
        return None
    lines = text.split("\n")
    if 0 <= line_number < len(lines):
        return lines[line_number]
    return None


def create_traceback_header(error_name, total_width=75):
    line1 = "-" * total_width + "\n"
    traceback_str = "Traceback (most recent call last)"
    remaining_space = total_width - len(error_name)
    line2 = f"{error_name}{traceback_str:>{remaining_space}}\n"
    return line1 + line2


class Error:
    __slots__ = ["pos_start", "pos_end", "error_name", "details"]

    def __init__(self, pos_start, pos_end, error_name, details):
        self.pos_start = pos_start
        self.pos_end = pos_end
        self.error_name = error_name
        self.details = details

    def __str__(self):
        result = create_traceback_header(self.error_name)

        result += f'  File {Fore.MAGENTA}"{self.pos_start.fn}"{Style.RESET_ALL}, line {Fore.MAGENTA}{self.pos_start.ln + 1}{Style.RESET_ALL}\n'

        line_text = get_line_from_text(self.pos_start.ftxt, self.pos_start.ln)

        if line_text is not None:
            s = ' \t\r'
            result += f"{Fore.LIGHTRED_EX}--> {line_text.strip(s)}{Style.RESET_ALL}\n"

        result += f"\n{Fore.LIGHTMAGENTA_EX}{Style.BRIGHT}{self.error_name}{Style.RESET_ALL}: {Fore.MAGENTA}{self.details}{Style.RESET_ALL}"
        return result


class IllegalCharError(Error):
    def __init__(self, pos_start, pos_end, details):
        super().__init__(pos_start, pos_end, "IllegalCharacterError", details)


class ExpectedCharError(Error):
    def __init__(self, pos_start, pos_end, details):
        super().__init__(pos_start, pos_end, "ExpectedCharacterError", details)


class InvalidSyntaxError(Error):
    def __init__(self, pos_start, pos_end, details=""):
        super().__init__(pos_start, pos_end, "InvalidSyntaxError", details)


class RTError(Error):
    def __init__(self, pos_start, pos_end, details, context):
        super().__init__(pos_start, pos_end, "RuntimeError", details)
        self.context = context

    def generate_traceback_frames(self):
        frames = []
        ctx = self.context
        pos = self.pos_start
        while ctx:
            if pos:
                frames.append({"pos": pos, "display_name": ctx.display_name})
            pos = ctx.parent_entry_pos
            ctx = ctx.parent
        return list(reversed(frames))

    def __str__(self):
        result = create_traceback_header(self.error_name)
        frames = self.generate_traceback_frames()

        for frame in frames:
            pos = frame["pos"]
            display_name = frame["display_name"]

            result += f'  File {Fore.MAGENTA}"{pos.fn}"{Style.RESET_ALL}, line {Fore.MAGENTA}{pos.ln + 1}{Style.RESET_ALL}, in {Fore.MAGENTA}{display_name}{Style.RESET_ALL}\n'

        line_text = get_line_from_text(self.pos_start.ftxt, self.pos_start.ln)
        if line_text is not None:
            s = ' \t\r'
            result += f"{Fore.LIGHTRED_EX}--> {line_text.strip(s)}{Style.RESET_ALL}\n"

        result += f"\n{Fore.LIGHTMAGENTA_EX}{Style.BRIGHT}{self.error_name}{Style.RESET_ALL}: {Fore.MAGENTA}{self.details}{Style.RESET_ALL}"
        return result


class MError(RTError):
    def __init__(self, pos_start, pos_end, details, context):
        super().__init__(pos_start, pos_end, details, context)
        self.error_name = "MathError"


class IError(RTError):
    def __init__(self, pos_start, pos_end, details, context):
        super().__init__(pos_start, pos_end, details, context)
        self.error_name = "IOError"


class TError(RTError):
    def __init__(self, pos_start, pos_end, details, context):
        super().__init__(pos_start, pos_end, details, context)
        self.error_name = "TypeError"
