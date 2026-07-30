const TOKEN_TYPES = {
    STRING: 'STRING',
    COMMENT: 'COMMENT',
    CODE: 'CODE',
    EOF: 'EOF'
};

class MiniLexer {
    constructor(text) {
        this.text = text;
        this.pos = 0;
        this.line = 0;
        this.col = 0;
        this.currentChar = text.length > 0 ? text[0] : null;
    }

    advance(steps = 1) {
        for (let i = 0; i < steps; i++) {
            if (this.currentChar === '\n') {
                this.line++;
                this.col = 0;
            } else {
                this.col++;
            }
            this.pos++;
            this.currentChar = this.pos < this.text.length ? this.text[this.pos] : null;
        }
    }

    peek(steps = 1) {
        const peekPos = this.pos + steps;
        return peekPos < this.text.length ? this.text[peekPos] : null;
    }

    makeComment() {
        const startLine = this.line;
        const startCol = this.col;
        const startPos = this.pos;

        this.advance();
        while (this.currentChar !== null && this.currentChar !== '\n') {
            this.advance();
        }

        return {
            type: TOKEN_TYPES.COMMENT,
            value: this.text.slice(startPos, this.pos),
            range: { startLine, startCol, endLine: this.line, endCol: this.col }
        };
    }

    makeString() {
        const quoteChar = this.currentChar;
        const startLine = this.line;
        const startCol = this.col;
        const startPos = this.pos;

        this.advance();
        let isMultiline = false;

        if (this.currentChar === quoteChar && this.peek(1) === quoteChar) {
            isMultiline = true;
            this.advance(2);
        }

        let escape = false;
        while (this.currentChar !== null) {
            if (isMultiline) {
                if (
                    !escape &&
                    this.currentChar === quoteChar &&
                    this.peek(1) === quoteChar &&
                    this.peek(2) === quoteChar
                ) {
                    this.advance(3);
                    break;
                }
            } else {
                if (!escape && this.currentChar === quoteChar) {
                    this.advance();
                    break;
                }
            }

            if (escape) {
                escape = false;
            } else if (this.currentChar === '\\') {
                escape = true;
            }
            this.advance();
        }

        return {
            type: TOKEN_TYPES.STRING,
            value: this.text.slice(startPos, this.pos),
            range: { startLine, startCol, endLine: this.line, endCol: this.col }
        };
    }

    tokenize() {
        const tokens = [];
        let codeStartPos = this.pos;
        let codeStartLine = this.line;
        let codeStartCol = this.col;

        const flushCodeToken = () => {
            if (this.pos > codeStartPos) {
                tokens.push({
                    type: TOKEN_TYPES.CODE,
                    value: this.text.slice(codeStartPos, this.pos),
                    range: { startLine: codeStartLine, startCol: codeStartCol, endLine: this.line, endCol: this.col }
                });
            }
        };

        while (this.currentChar !== null) {
            if (this.currentChar === '#') {
                flushCodeToken();
                tokens.push(this.makeComment());
                codeStartPos = this.pos;
                codeStartLine = this.line;
                codeStartCol = this.col;
            } else if (this.currentChar === '"' || this.currentChar === "'") {
                flushCodeToken();
                tokens.push(this.makeString());
                codeStartPos = this.pos;
                codeStartLine = this.line;
                codeStartCol = this.col;
            } else {
                this.advance();
            }
        }

        flushCodeToken();
        return tokens;
    }
}

module.exports = MiniLexer;
