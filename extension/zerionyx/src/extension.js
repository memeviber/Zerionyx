const vscode = require('vscode');
const fs = require('fs');
const path = require('path');

const zerionyxKeywords = [
    'load', 'namespace', 'done', 'defun', 'using', 'parent',
    'if', 'elif', 'else', 'do', 'for', 'to', 'step', 'in', 'while', 'del'
];
const zerionyxControlFlow = ['return', 'continue', 'break'];
const zerionyxOperators = ['and', 'or', 'not'];
const zerionyxConstants = ['true', 'false', 'none', 'nan', 'inf', 'neg_inf', 'is_main', 'PI', 'E', 'ln2'];
const zerionyxTypeConstants = [
    'list', 'str', 'int', 'float', 'bool', 'func', 'hashmap', 'thread',
    'bytes', 'cfloat', 'py_obj', 'namespace', 'channel_type', 'none_type',
    'thread_pool_type', 'future_type'
];

const zerionyxBuiltins = [
    'println', 'print', 'input', 'get_password', 'clear', 'type', 'is_none',
    'is_num', 'is_bool', 'is_str', 'is_list', 'is_func', 'is_thread',
    'is_thread_pool', 'is_future', 'is_namespace', 'is_channel', 'is_cfloat',
    'is_py_obj', 'is_nan', 'is_panic', 'len', 'panic', 'pop', 'append',
    'insert', 'extend', 'slice', 'to_str', 'to_int', 'to_float', 'to_cfloat',
    'to_bytes', 'pyexec', 'clone', 'keys', 'values', 'items', 'has', 'get',
    'del_key', 'get_member', 'shl', 'shr', 'bitwise_and', 'bitwise_or',
    'bitwise_xor', 'bitwise_not'
];

const libraryFunctions = {
    "msgbox": ["alert", "confirm", "prompt", "password"],
    "time.datetime": ["now", "diff", "add_days", "format", "today", "parse"],
    "listm": ["map", "filter", "reduce", "min", "max", "reverse", "zip", "zip_longest", "sort", "count", "index_of", "rand_int_list", "rand_float_list"],
    "string": ["split", "strip", "join", "replace", "to_upper", "to_lower", "ord", "chr", "is_digit", "is_ascii_lowercase", "is_ascii_uppercase", "is_ascii_letter", "is_space", "find", "find_all", "startswith", "endswith", "encode", "decode", "format"],
    "math": ["sqrt", "abs", "fact", "sin", "cos", "tan", "gcd", "lcm", "fib", "is_prime", "deg2rad", "rad2deg", "exp", "log", "sinh", "cosh", "tanh", "round", "is_close"],
    "ffio": ["write", "read", "exists", "get_cdir", "set_cdir", "list_dir", "make_dir", "remove_file", "rename", "remove_dir", "copy", "is_file", "abs_path", "base_name", "dir_name", "symlink", "readlink", "stat", "lstat", "walk", "chmod", "chown", "utime", "link", "unlink", "access", "path_join", "is_dir", "is_link", "is_mount"],
    "hash": ["md5", "sha1", "sha256", "sha512", "crc32"],
    "memory": ["remember", "recall", "forget", "clear_memory", "keys", "is_empty", "size"],
    "net": ["get_ip", "get_mac", "ping", "downl", "get_local_ip", "get_hostname", "request"],
    "random": ["rand", "rand_int", "rand_float", "rand_choice", "int_seed", "float_seed"],
    "sys": ["system", "osystem", "get_env", "set_env", "exit"],
    "threading": ["start", "sleep", "join", "is_alive", "cancel"],
    "threading.pool": ["new", "submit", "shutdown", "result", "is_done"],
    "time": ["sleep", "time", "ctime"],
    "keyboard": ["write", "press", "release", "wait", "is_pressed"],
    "termcolor": ["cprint", "cprintln", "get_code"],
    "mouse": ["move", "click", "right_click", "scroll", "position"],
    "screen": ["capture", "capture_area", "get_color"],
    "json": ["parse", "stringify"],
    "csv": ["read", "write"],
    "decorators": ["cache", "once", "retry", "timeout", "log_call", "measure_time", "repeat", "ignore_error", "deprecated", "lazy"],
    "channel": ["new", "send", "recv", "is_empty"]
};

const libraryConstants = {
    "math": ["PI", "E", "ln2"],
    "ffio": ["os_sep"],
    "sys": ["argv", "os_name"]
};

function stripCommentsAndStrings(code) {
    let cleanCode = code.replace(/#.*/g, "");
    cleanCode = cleanCode.replace(/"""[\s\S]*?"""/g, "");
    cleanCode = cleanCode.replace(/'''[\s\S]*?'''/g, "");
    cleanCode = cleanCode.replace(/"([^"\\]|\\.)*"/g, "");
    cleanCode = cleanCode.replace(/'([^'\\]|\\.)*'/g, "");
    return cleanCode;
}

function parseSource(sourceCode, localNsMap, globalSuggestions) {
    const cleanCode = stripCommentsAndStrings(sourceCode);
    const lines = cleanCode.split('\n');

    let nsStack = [];
    let stack = [];

    const nsStart = /\bnamespace\s+([a-zA-Z_]\w*)/;
    const defunMultiline = /\bdefun\b(?!.*->)/;
    const ifMultiline = /\b(?<!el)if\b.*?\bdo\s*$/;
    const whileMultiline = /\bwhile\b.*?\bdo\s*$/;
    const forMultiline = /\bfor\b.*?\bdo\s*$/;

    const funcPattern = /defun\s+([a-zA-Z_]\w*)/g;
    const varPattern = /([a-zA-Z_]\w*)\s*=/g;
    const forPattern = /(?:\bfor|,)\s+([a-zA-Z_]\w*)/g;

    const getMatches = (regex, text) => {
        let m, results = [];
        regex.lastIndex = 0;
        while ((m = regex.exec(text)) !== null) {
            results.push(m[1]);
        }
        return results;
    };

    for (let line of lines) {
        let stripped = line.trim();
        if (!stripped) continue;

        if (stripped === "done" || stripped.endsWith(" done")) {
            if (stack.length > 0) {
                let top = stack.pop();
                if (top.startsWith("ns:")) {
                    nsStack.pop();
                }
            }
            continue;
        }

        let nsMatch = stripped.match(nsStart);
        if (nsMatch) {
            let nsName = nsMatch[1];
            nsStack.push(nsName);
            stack.push("ns:" + nsName);

            globalSuggestions.add(nsName);
            globalSuggestions.add(nsStack.join("."));
            continue;
        }

        if (defunMultiline.test(stripped) || ifMultiline.test(stripped) ||
            whileMultiline.test(stripped) || forMultiline.test(stripped)) {
            stack.push("generic");
        }

        let currentNs = nsStack.join(".");
        let funcs = getMatches(funcPattern, stripped);
        let vars = getMatches(varPattern, stripped);
        let fors = getMatches(forPattern, stripped);

        if (currentNs) {
            if (!localNsMap[currentNs]) localNsMap[currentNs] = new Set();
            funcs.forEach(f => localNsMap[currentNs].add(f));
            vars.forEach(v => localNsMap[currentNs].add(v));
        } else {
            funcs.forEach(f => globalSuggestions.add(f));
            vars.forEach(v => globalSuggestions.add(v));
            fors.forEach(f => globalSuggestions.add(f));
        }
    }
}

function activate(context) {
    const provider = vscode.languages.registerCompletionItemProvider('zerionyx', {
        provideCompletionItems(document, position) {
            const lineText = document.lineAt(position).text;
            const linePrefix = lineText.slice(0, position.character);

            if (linePrefix.includes('#')) {
                return undefined;
            }

            const fullText = document.getText();
            let stdLibsLoaded = new Set();
            let localFilesToScan = new Set();

            const loadPattern = /load\s+["']([^"']+)["']/g;
            let match;
            while ((match = loadPattern.exec(fullText)) !== null) {
                let p = match[1];
                if (p.startsWith("libs.")) {
                    stdLibsLoaded.add(p.slice(5));
                } else if (p.startsWith("local.")) {
                    localFilesToScan.add(p.slice(6));
                }
            }

            let localNsMap = {};
            let globalSuggestions = new Set();

            parseSource(fullText, localNsMap, globalSuggestions);

            if (document.uri.scheme === 'file') {
                const baseDir = path.dirname(document.uri.fsPath);
                for (let loc of localFilesToScan) {
                    let relPath = loc.replace(/\./g, path.sep);
                    let localPathZyx = path.join(baseDir, relPath + ".zyx");
                    let localPathZex = path.join(baseDir, relPath + ".zex");

                    let targetPath = fs.existsSync(localPathZyx) ? localPathZyx : (fs.existsSync(localPathZex) ? localPathZex : null);
                    if (targetPath) {
                        try {
                            let localText = fs.readFileSync(targetPath, 'utf-8');
                            parseSource(localText, localNsMap, globalSuggestions);
                        } catch (e) { }
                    }
                }
            }

            let completions = [];

            const dotMatch = linePrefix.match(/([a-zA-Z_]\w*(?:\.[a-zA-Z_]\w*)*)\.([a-zA-Z_]\w*)?$/);

            if (dotMatch) {
                let prefix = dotMatch[1];
                let rootLib = prefix.split('.')[0];

                if (stdLibsLoaded.has(prefix) || stdLibsLoaded.has(rootLib)) {
                    if (libraryFunctions[prefix]) {
                        libraryFunctions[prefix].forEach(f => {
                            completions.push(new vscode.CompletionItem(f, vscode.CompletionItemKind.Method));
                        });
                    }
                    if (libraryConstants[prefix]) {
                        libraryConstants[prefix].forEach(c => {
                            completions.push(new vscode.CompletionItem(c, vscode.CompletionItemKind.Field));
                        });
                    }
                }

                if (localNsMap[prefix]) {
                    localNsMap[prefix].forEach(member => {
                        completions.push(new vscode.CompletionItem(member, vscode.CompletionItemKind.Property));
                    });
                }
                return completions;
            }

            zerionyxKeywords.forEach(k => completions.push(new vscode.CompletionItem(k, vscode.CompletionItemKind.Keyword)));
            zerionyxControlFlow.forEach(k => completions.push(new vscode.CompletionItem(k, vscode.CompletionItemKind.Keyword)));
            zerionyxOperators.forEach(k => completions.push(new vscode.CompletionItem(k, vscode.CompletionItemKind.Operator)));
            zerionyxConstants.forEach(k => completions.push(new vscode.CompletionItem(k, vscode.CompletionItemKind.Constant)));
            zerionyxTypeConstants.forEach(k => completions.push(new vscode.CompletionItem(k, vscode.CompletionItemKind.TypeParameter)));
            zerionyxBuiltins.forEach(k => completions.push(new vscode.CompletionItem(k, vscode.CompletionItemKind.Function)));

            stdLibsLoaded.forEach(lib => {
                completions.push(new vscode.CompletionItem(lib, vscode.CompletionItemKind.Module));
            });

            globalSuggestions.forEach(sym => {
                completions.push(new vscode.CompletionItem(sym, vscode.CompletionItemKind.Variable));
            });

            const uniqueCompletions = [];
            const seen = new Set();
            for (let item of completions) {
                if (!seen.has(item.label)) {
                    seen.add(item.label);
                    uniqueCompletions.push(item);
                }
            }

            return uniqueCompletions;
        }
    },
        '.'
    );

    context.subscriptions.push(provider);
}

module.exports = {
    activate
};
