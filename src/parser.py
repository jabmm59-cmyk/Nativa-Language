from . import ast_nodes as A
from .errors import NativaSyntaxError
from .lexer import (
    EOF, KEYWORD, NAME, NEWLINE, NUMBER, OP, PENDING_KEYWORDS, STRING, Lexer,
)

COMPARE_OPS = {"==", "!=", "<", ">", "<=", ">="}
EXPR_START_KEYWORDS = {"not", "True", "False", "None", "utype"}
EXPR_START_OPS = {"(", "[", "{", "-", "+"}


class Parser:
    def __init__(self, tokens, filename="<principal>"):
        self.tokens = tokens
        self.pos = 0
        self.filename = filename

    @property
    def cur(self):
        return self.tokens[self.pos]

    def peek(self, k=0):
        return self.tokens[min(self.pos + k, len(self.tokens) - 1)]

    def advance(self):
        tok = self.tokens[self.pos]
        if tok.type != EOF:
            self.pos += 1
        return tok

    def is_op(self, value, k=0):
        tok = self.peek(k)
        return tok.type == OP and tok.value == value

    def is_kw(self, value, k=0):
        tok = self.peek(k)
        return tok.type == KEYWORD and tok.value == value

    def is_kw_any(self, *values, k=0):
        tok = self.peek(k)
        return tok.type == KEYWORD and tok.value in values

    def describe(self, tok):
        if tok.type == EOF:
            return "fim do arquivo"
        if tok.type == NEWLINE:
            return "fim de linha"
        return repr(tok.value)

    def error(self, message, tok=None):
        tok = tok or self.cur
        return NativaSyntaxError(message, tok.line, tok.col, self.filename)

    def expect_op(self, value):
        if not self.is_op(value):
            raise self.error(f"esperado '{value}', encontrado {self.describe(self.cur)}")
        return self.advance()

    def expect_name(self, what):
        if self.cur.type != NAME:
            raise self.error(f"esperado {what}, encontrado {self.describe(self.cur)}")
        return self.advance()

    def skip_newlines(self):
        while self.cur.type == NEWLINE:
            self.advance()

    def at_statement_end(self):
        return self.cur.type in (NEWLINE, EOF) or self.is_op(")")

    def end_statement(self):
        if self.cur.type == NEWLINE:
            self.advance()
        elif self.cur.type == EOF or self.is_op(")"):
            return
        else:
            raise self.error(f"esperado fim de linha, encontrado {self.describe(self.cur)}")

    def parse_program(self):
        body = []
        self.skip_newlines()
        while self.cur.type != EOF:
            body.append(self.parse_statement())
            self.end_statement()
            self.skip_newlines()
        return A.Program(body, line=1, col=1)

    def parse_block(self):
        self.expect_op(":")
        return self._parse_block_body()

    def _parse_block_body(self):
        """Parse block body after ':' has been consumed. Expects '(' ... ')'."""
        if not self.is_op("("):
            raise self.error(f"esperado '(' para abrir o bloco, encontrado {self.describe(self.cur)}")
        opener = self.advance()
        statements = []
        self.skip_newlines()
        while not self.is_op(")"):
            if self.cur.type == EOF:
                raise self.error("bloco não fechado: falta ')'", opener)
            statements.append(self.parse_statement())
            self.end_statement()
            self.skip_newlines()
        self.advance()
        return statements

    def parse_statement(self):
        tok = self.cur
        if tok.type == KEYWORD:
            if tok.value in PENDING_KEYWORDS:
                raise self.error(f"o comando '{tok.value}' ainda não está implementado nesta etapa")
            handler = getattr(self, "stmt_" + tok.value, None)
            if handler is not None:
                return handler()
        expr = self.parse_expr()
        if self.is_op("="):
            eq = self.advance()
            if not isinstance(expr, (A.Name, A.Attr, A.Index)):
                raise self.error("alvo de atribuição inválido", eq)
            value = self.parse_expr()
            return A.Assign(expr, value, line=tok.line, col=tok.col)
        return A.ExprStmt(expr, line=tok.line, col=tok.col)

    def stmt_NA(self):
        tok = self.advance()
        if self.is_kw("imp"):
            return self._parse_imp(tok)
        elif self.is_kw("de"):
            return self._parse_de_imp(tok)
        else:
            raise self.error(f"esperado 'imp' ou 'de' após 'NA', encontrado {self.describe(self.cur)}")

    def _parse_imp(self, na_tok):
        """Parse 'NA imp modulo1, modulo2 como alias, ...' - supports dotted names"""
        self.advance()  # consume 'imp'
        names = []
        while True:
            # Parse dotted module name (e.g., NAgame.graphics, os.path)
            module_parts = []
            name_tok = self.expect_name("nome do módulo")
            module_parts.append(name_tok.value)
            while self.is_op("."):
                self.advance()
                next_tok = self.expect_name("nome do módulo após '.'")
                module_parts.append(next_tok.value)
            module_name = ".".join(module_parts)

            alias = None
            if self.is_kw("como"):
                self.advance()
                alias_tok = self.expect_name("apelido do módulo")
                alias = alias_tok.value
            names.append((module_name, alias))
            if not self.is_op(","):
                break
            self.advance()
        return A.Import(names, line=na_tok.line, col=na_tok.col)

    def _parse_de_imp(self, na_tok):
        """Parse 'NA de modulo imp nome1, nome2 como alias, ...'"""
        self.advance()  # consume 'de'
        level = 0
        while self.is_op("."):
            level += 1
            self.advance()
        # Parse dotted module name (e.g., os.path, json.decoder)
        module_parts = []
        if self.cur.type == NAME:
            module_parts.append(self.advance().value)
            while self.is_op("."):
                self.advance()
                if self.cur.type != NAME:
                    raise self.error("esperado nome após '.' no módulo")
                module_parts.append(self.advance().value)
        module = ".".join(module_parts)
        if not self.is_kw("imp"):
            raise self.error("esperado 'imp' após 'NA de modulo'")
        self.advance()
        names = []
        while True:
            name_tok = self.expect_name("nome a importar")
            alias = None
            if self.is_kw("como"):
                self.advance()
                alias_tok = self.expect_name("apelido")
                alias = alias_tok.value
            names.append((name_tok.value, alias))
            if not self.is_op(","):
                break
            self.advance()
        return A.ImportFrom(module, names, level, line=na_tok.line, col=na_tok.col)

    def stmt_shw(self):
        tok = self.advance()
        args, kwargs = [], []
        if self.at_statement_end():
            return A.Shw(args, kwargs, line=tok.line, col=tok.col)
        while True:
            if self.cur.type == NAME and self.is_op("=", 1):
                name = self.advance().value
                self.advance()
                kwargs.append((name, self.parse_expr()))
            else:
                if kwargs:
                    raise self.error("argumento posicional depois de argumento nomeado")
                args.append(self.parse_expr())
            if self.is_op(","):
                self.advance()
                continue
            break
        return A.Shw(args, kwargs, line=tok.line, col=tok.col)

    def stmt_if(self):
        tok = self.advance()
        test = self.parse_expr()
        body = self.parse_block()
        orelse = []
        save = self.pos
        self.skip_newlines()
        if self.is_kw_any("else", "senao"):
            self.advance()
            if self.is_kw_any("if", "se"):
                orelse = [self.stmt_if()]
            else:
                orelse = self.parse_block()
        else:
            self.pos = save
        return A.If(test, body, orelse, line=tok.line, col=tok.col)

    stmt_se = stmt_if

    def stmt_while(self):
        tok = self.advance()
        test = self.parse_expr()
        body = self.parse_block()
        return A.While(test, body, line=tok.line, col=tok.col)

    stmt_enquanto = stmt_while

    def stmt_for(self):
        tok = self.advance()
        var = self.expect_name("nome da variável do laço").value
        if not self.is_kw_any("in", "em"):
            raise self.error(f"esperado 'in', encontrado {self.describe(self.cur)}")
        self.advance()
        iterable = self.parse_expr()
        body = self.parse_block()
        return A.For(var, iterable, body, line=tok.line, col=tok.col)

    stmt_para = stmt_for

    def stmt_try(self):
        """Parse 'try: ( ... ) xcept: ( ... ) idgafatc: ( ... )'"""
        tok = self.advance()  # consume 'try'
        body = self.parse_block()
        handlers = []
        finalbody = []
        self.skip_newlines()
        while self.is_kw("xcept"):
            handlers.append(self.parse_except_handler())
            self.skip_newlines()
        if self.is_kw("idgafatc"):
            self.advance()
            self.expect_op(":")
            finalbody = self._parse_block_body()
        return A.Try(body, handlers, finalbody, line=tok.line, col=tok.col)

    def parse_except_handler(self):
        tok = self.advance()  # consume 'xcept'
        exc_type = None
        exc_name = None
        # Check if there's an exception type before the ':' or 'as'
        if not self.is_op(":") and not self.is_kw("as"):
            # Parse exception type
            exc_type = self.parse_expr()
            if self.is_kw("as"):
                self.advance()
                name_tok = self.expect_name("nome da variável de exceção")
                exc_name = name_tok.value
        elif self.is_kw("as"):
            # xcept as e: (no type, just variable)
            self.advance()
            name_tok = self.expect_name("nome da variável de exceção")
            exc_name = name_tok.value
        # Expect ':' then block
        self.expect_op(":")
        body = self._parse_block_body()
        return A.ExceptHandler(exc_type, exc_name, body, line=tok.line, col=tok.col)

    def stmt_xcept(self):
        """Alias for 'except' - shouldn't be called directly"""
        raise self.error("'xcept' deve ser usado dentro de 'try'")

    def stmt_idgafatc(self):
        """Alias for 'finally' - shouldn't be called directly"""
        raise self.error("'idgafatc' deve ser usado dentro de 'try'")

    def stmt_perror(self):
        """Parse 'perror [expression]' - raise exception"""
        tok = self.advance()
        exc = None
        if not self.at_statement_end():
            exc = self.parse_expr()
        return A.Raise(exc, line=tok.line, col=tok.col)

    def stmt_df(self):
        tok = self.advance()
        name = self.expect_name("nome da função").value
        self.expect_op("(")
        params = []
        self.skip_newlines()
        while not self.is_op(")"):
            vararg = False
            if self.is_op("*"):
                self.advance()
                vararg = True
            ptok = self.expect_name("nome do parâmetro")
            default = None
            if self.is_op("="):
                if vararg:
                    raise self.error("parâmetro '*' não aceita valor padrão")
                self.advance()
                default = self.parse_expr()
            if any(p.name == ptok.value for p in params):
                raise self.error(f"parâmetro '{ptok.value}' duplicado", ptok)
            if params and params[-1].vararg:
                raise self.error("o parâmetro '*' deve ser o último", ptok)
            params.append(A.Param(ptok.value, default, vararg))
            self.skip_newlines()
            if self.is_op(","):
                self.advance()
                self.skip_newlines()
            else:
                break
        self.skip_newlines()
        self.expect_op(")")
        body = self.parse_block()
        return A.FuncDef(name, params, body, line=tok.line, col=tok.col)

    def stmt_ret(self):
        tok = self.advance()
        value = None if self.at_statement_end() else self.parse_expr()
        return A.Return(value, line=tok.line, col=tok.col)

    def stmt_brk(self):
        tok = self.advance()
        return A.Break(line=tok.line, col=tok.col)

    def stmt_continue(self):
        tok = self.advance()
        return A.Continue(line=tok.line, col=tok.col)

    def stmt_classify(self):
        tok = self.advance()
        name = self.expect_name("nome da classe").value
        bases = []
        if self.is_op("("):
            self.advance()
            self.skip_newlines()
            while not self.is_op(")"):
                bases.append(self.parse_expr())
                self.skip_newlines()
                if self.is_op(","):
                    self.advance()
                    self.skip_newlines()
                else:
                    break
            self.expect_op(")")
        body = self.parse_block()
        return A.ClassDef(name, bases, body, line=tok.line, col=tok.col)

    def parse_expr(self):
        return self.parse_or()

    def parse_or(self):
        left = self.parse_and()
        while self.is_kw_any("or", "ou"):
            tok = self.advance()
            left = A.BoolOp("or", left, self.parse_and(), line=tok.line, col=tok.col)
        return left

    def parse_and(self):
        left = self.parse_not()
        while self.is_kw_any("and", "e"):
            tok = self.advance()
            left = A.BoolOp("and", left, self.parse_not(), line=tok.line, col=tok.col)
        return left

    def parse_not(self):
        if self.is_kw_any("not", "nao"):
            tok = self.advance()
            return A.Unary("not", self.parse_not(), line=tok.line, col=tok.col)
        return self.parse_comparison()

    def comparison_op(self):
        tok = self.cur
        if tok.type == OP and tok.value in COMPARE_OPS:
            self.advance()
            return tok.value
        if tok.type == KEYWORD:
            if tok.value in ("in", "em"):
                self.advance()
                return "in"
            if tok.value in ("not", "nao") and self.is_kw_any("in", "em", 1):
                self.advance()
                self.advance()
                return "not in"
            if tok.value in ("is", "é"):
                self.advance()
                if self.is_kw_any("not", "nao"):
                    self.advance()
                    return "is not"
                return "is"
        return None

    def parse_comparison(self):
        start = self.cur
        left = self.parse_arith()
        ops, rights = [], []
        while True:
            op = self.comparison_op()
            if op is None:
                break
            ops.append(op)
            rights.append(self.parse_arith())
        if not ops:
            return left
        return A.Compare(left, ops, rights, line=start.line, col=start.col)

    def parse_arith(self):
        left = self.parse_term()
        while self.cur.type == OP and self.cur.value in ("+", "-"):
            tok = self.advance()
            left = A.BinOp(tok.value, left, self.parse_term(), line=tok.line, col=tok.col)
        return left

    def parse_term(self):
        left = self.parse_unary()
        while self.cur.type == OP and self.cur.value in ("*", "/", "//", "%"):
            tok = self.advance()
            left = A.BinOp(tok.value, left, self.parse_unary(), line=tok.line, col=tok.col)
        return left

    def parse_unary(self):
        if self.cur.type == OP and self.cur.value in ("-", "+"):
            tok = self.advance()
            return A.Unary(tok.value, self.parse_unary(), line=tok.line, col=tok.col)
        return self.parse_power()

    def parse_power(self):
        base = self.parse_postfix()
        if self.is_op("**"):
            tok = self.advance()
            return A.BinOp("**", base, self.parse_unary(), line=tok.line, col=tok.col)
        return base

    def parse_postfix(self):
        node = self.parse_atom()
        while True:
            if self.is_op("("):
                node = self.parse_call(node)
            elif self.is_op("["):
                tok = self.advance()
                self.skip_newlines()
                index = self.parse_expr()
                self.skip_newlines()
                self.expect_op("]")
                node = A.Index(node, index, line=tok.line, col=tok.col)
            elif self.is_op("."):
                tok = self.advance()
                name = self.expect_name("nome do atributo").value
                node = A.Attr(node, name, line=tok.line, col=tok.col)
            else:
                break
        return node

    def parse_call(self, func):
        tok = self.advance()
        args, kwargs = [], []
        self.skip_newlines()
        while not self.is_op(")"):
            if self.cur.type == NAME and self.is_op("=", 1):
                name = self.advance().value
                self.advance()
                kwargs.append((name, self.parse_expr()))
            else:
                if kwargs:
                    raise self.error("argumento posicional depois de argumento nomeado")
                args.append(self.parse_expr())
            self.skip_newlines()
            if self.is_op(","):
                self.advance()
                self.skip_newlines()
            else:
                break
        self.skip_newlines()
        self.expect_op(")")
        return A.Call(func, args, kwargs, line=tok.line, col=tok.col)

    def starts_expression(self):
        tok = self.cur
        if tok.type in (NUMBER, STRING, NAME):
            return True
        if tok.type == OP:
            return tok.value in EXPR_START_OPS
        if tok.type == KEYWORD:
            return tok.value in EXPR_START_KEYWORDS
        return False

    def parse_atom(self):
        tok = self.cur
        if tok.type == NUMBER:
            self.advance()
            return A.Num(tok.value, line=tok.line, col=tok.col)
        if tok.type == STRING:
            self.advance()
            return self.build_string(tok)
        if tok.type == NAME:
            self.advance()
            return A.Name(tok.value, line=tok.line, col=tok.col)
        if tok.type == KEYWORD:
            if tok.value in ("True", "False", "None"):
                self.advance()
                value = {"True": True, "False": False, "None": None}[tok.value]
                return A.Const(value, line=tok.line, col=tok.col)
            if tok.value == "utype":
                self.advance()
                prompt = self.parse_expr() if self.starts_expression() else None
                return A.Utype(prompt, line=tok.line, col=tok.col)
        if tok.type == OP:
            if tok.value == "(":
                self.advance()
                self.skip_newlines()
                expr = self.parse_expr()
                self.skip_newlines()
                self.expect_op(")")
                return expr
            if tok.value == "[":
                return self.parse_list()
            if tok.value == "{":
                return self.parse_dict()
        raise self.error(f"token inesperado: {self.describe(tok)}")

    def parse_list(self):
        tok = self.advance()
        items = []
        self.skip_newlines()
        while not self.is_op("]"):
            items.append(self.parse_expr())
            self.skip_newlines()
            if self.is_op(","):
                self.advance()
                self.skip_newlines()
            else:
                break
        self.expect_op("]")
        return A.ListLit(items, line=tok.line, col=tok.col)

    def parse_dict(self):
        tok = self.advance()
        pairs = []
        self.skip_newlines()
        while not self.is_op("}"):
            key = self.parse_expr()
            self.skip_newlines()
            self.expect_op(":")
            self.skip_newlines()
            value = self.parse_expr()
            pairs.append((key, value))
            self.skip_newlines()
            if self.is_op(","):
                self.advance()
                self.skip_newlines()
            else:
                break
        self.expect_op("}")
        return A.DictLit(pairs, line=tok.line, col=tok.col)

    def build_string(self, tok):
        s = tok.value
        if "{" not in s and "}" not in s:
            return A.Str(s, line=tok.line, col=tok.col)
        parts, buf = [], []
        i, n = 0, len(s)
        while i < n:
            c = s[i]
            if c == "{":
                if i + 1 < n and s[i + 1] == "{":
                    buf.append("{")
                    i += 2
                    continue
                # Find matching }
                depth, j, quote = 1, i + 1, None
                while j < n and depth > 0:
                    d = s[j]
                    if quote:
                        if d == quote:
                            quote = None
                    elif d in "'\"":
                        quote = d
                    elif d == "{":
                        depth += 1
                    elif d == "}":
                        depth -= 1
                    j += 1
                if depth != 0:
                    raise self.error("interpolação não fechada: falta '}'", tok)
                source = s[i + 1:j - 1]
                # Empty interpolation is always an error
                if not source.strip():
                    raise self.error("interpolação vazia", tok)
                # Try to parse as interpolation
                try:
                    if buf:
                        parts.append("".join(buf))
                        buf = []
                    parts.append(self.parse_fragment(source, tok, i))
                    i = j
                    continue
                except NativaSyntaxError:
                    pass  # Fall through to literal handling
                # Not a valid interpolation, treat entire {...} as literal
                buf.append(s[i:j])
                i = j
            elif c == "}":
                if i + 1 < n and s[i + 1] == "}":
                    buf.append("}")
                    i += 2
                    continue
                raise self.error("'}' solitário na string; use '}}' para um '}' literal", tok)
            else:
                buf.append(c)
                i += 1
        if buf:
            parts.append("".join(buf))
        if len(parts) == 1 and isinstance(parts[0], str):
            return A.Str(parts[0], line=tok.line, col=tok.col)
        return A.Interp(parts, line=tok.line, col=tok.col)

    def parse_fragment(self, source, tok, offset):
        lexer = Lexer(source, self.filename, line_offset=tok.line - 1, col_offset=tok.col + 1 + offset)
        sub = Parser(lexer.tokenize(), self.filename)
        sub.skip_newlines()
        expr = sub.parse_expr()
        sub.skip_newlines()
        if sub.cur.type != EOF:
            raise sub.error(f"token inesperado na interpolação: {sub.describe(sub.cur)}")
        return expr


def parse(source, filename="<principal>"):
    tokens = Lexer(source, filename).tokenize()
    return Parser(tokens, filename).parse_program()
