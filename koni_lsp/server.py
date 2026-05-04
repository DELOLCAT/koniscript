import logging
import re

from lsprotocol import types

from pygls.lsp.server import LanguageServer
from pygls.workspace import TextDocument

from koni_compiler import base_env
from koni_compiler.main import (
    Compiler,
    CompilerError,
    Parser,
    ParserError,
    Tokenizer,
    TokenizerError,
    ParserWarn
)

ADDITION = re.compile(r"^\s*(\d+)\s*\+\s*(\d+)\s*=\s*(\d+)?$")


class PublishDiagnosticServer(LanguageServer):
    """Language server demonstrating "push-model" diagnostics."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.diagnostics = {}

    def parse(self, document: TextDocument):
        before = len(base_env.compiler_env)  # or however you'd measure its size
        diagnostics = []
        self.diagnostics[document.uri] = (document.version, [])

        ast_env, compiler_env, attrs = base_env.make_fresh_env()

        logging.info("SOURCE:\n%s", document.source)
        tkns = None
        try:
            tknr = Tokenizer(document.source)
            tkns = []
            while True:
                tkn = tknr.get_next_token()
                if isinstance(tkn, list):
                    tkns += tkn
                else:
                    tkns.append(tkn)
                if tkns[-1].type == "EOF":
                    break
        except TokenizerError as e:
            diagnostics.append(
                types.Diagnostic(
                    message=e.msg,
                    range=types.Range(
                        start=types.Position(
                            line=e.line,
                            character=e.col,
                        ),
                        end=types.Position(line=e.end_line, character=e.end_col),
                    ),
                )
            )
        program = None
        if tkns is not None:
            psr = Parser(tkns, ast_env)
            try:
                p = psr.program()
                while True:
                    try:
                        next(p)
                    except StopIteration as e:
                        program = e.value
                        break
            except ParserError as e:
                diagnostics.append(
                    types.Diagnostic(
                        message=e.msg,
                        range=types.Range(
                            start=types.Position(line=e.line, character=e.col),
                            end=types.Position(line=e.end_line, character=e.end_col),
                        ),
                    )
                )
        if program is not None:
            compiler = Compiler(compiler_env, ast_env, attrs, document.path)
            self.window_log_message(
                types.LogMessageParams(
                    type=types.MessageType.Warning, message=str(compiler)
                )
            )
            it = iter(compiler.compile(program))
            while True:
                try:
                    a = next(it)
                    logging.info(a)
                    if isinstance(a, ParserWarn):
                        diagnostics.append(
                            types.Diagnostic(
                                range=types.Range(
                                    start=types.Position(line=a.line, character=a.col),
                                    end=types.Position(
                                        line=a.end_line, character=a.end_col
                                    ),
                                ),
                                message=a.message,
                                severity=types.DiagnosticSeverity.Warning,
                            )
                        )
                except StopIteration:
                    break
                except CompilerError as e:
                    if e.line is not None:
                        diagnostics.append(
                            types.Diagnostic(
                                range=types.Range(
                                    start=types.Position(
                                        line=e.line,
                                        character=e.col if e.col is not None else 0,
                                    ),
                                    end=types.Position(
                                        line=(
                                            e.end_line
                                            if e.end_line is not None
                                            else e.line
                                        ),
                                        character=(
                                            e.end_col if e.end_col is not None else 1
                                        ),
                                    ),
                                ),
                                message=e.msg,
                            )
                        )

        self.diagnostics[document.uri] = (document.version, diagnostics)
        # ... run compiler ...
        after = len(base_env.compiler_env)
        logging.info("ASTenv size before: %d, after: %d", before, after)


server = PublishDiagnosticServer("diagnostic-server", "v1")


@server.feature(types.TEXT_DOCUMENT_DID_OPEN)
def did_open(ls: PublishDiagnosticServer, params: types.DidOpenTextDocumentParams):
    """Parse each document when it is opened"""
    doc = ls.workspace.get_text_document(params.text_document.uri)
    ls.parse(doc)

    for uri, (version, diagnostics) in ls.diagnostics.items():
        ls.text_document_publish_diagnostics(
            types.PublishDiagnosticsParams(
                uri=uri,
                version=version,
                diagnostics=diagnostics,
            )
        )


@server.feature(types.TEXT_DOCUMENT_DID_CHANGE)
def did_change(ls: PublishDiagnosticServer, params: types.DidOpenTextDocumentParams):
    """Parse each document when it is changed"""
    doc = ls.workspace.get_text_document(params.text_document.uri)
    ls.parse(doc)

    for uri, (version, diagnostics) in ls.diagnostics.items():
        ls.text_document_publish_diagnostics(
            types.PublishDiagnosticsParams(
                uri=uri,
                version=version,
                diagnostics=diagnostics,
            )
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    server.start_io()
