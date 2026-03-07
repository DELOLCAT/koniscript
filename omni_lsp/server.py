import logging
import re

from lsprotocol import types

from pygls.lsp.server import LanguageServer
from pygls.workspace import TextDocument

from omni_compiler import base_env
from omni_compiler.main import (
    Compiler,
    CompilerError,
    Parser,
    ParserError,
    Tokenizer,
    TokenizerError,
)

ADDITION = re.compile(r"^\s*(\d+)\s*\+\s*(\d+)\s*=\s*(\d+)?$")


class PublishDiagnosticServer(LanguageServer):
    """Language server demonstrating "push-model" diagnostics."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.diagnostics = {}

    def parse(self, document: TextDocument):
        diagnostics = []

        logging.info("SOURCE:\n%s", document.source)
        tkns = None
        try:
            tknr = Tokenizer(document.source)
            tkns = []
            while True:
                tkn = tknr.get_next_token()
                tkns.append(tkn)
                if tkn.type == "EOF":
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
                        end=types.Position(line=e.line, character=e.end_col),
                    ),
                )
            )
        program = None
        if tkns is not None:
            psr = Parser(tkns, base_env.ASTenv)
            try:
                program = psr.program()
            except ParserError as e:
                diagnostics.append(
                    types.Diagnostic(
                        message=e.msg,
                        range=types.Range(
                            start=types.Position(line=e.line, character=e.col),
                            end=types.Position(line=e.line, character=e.end_col),
                        ),
                    )
                )
        if program is not None:
            compiler = Compiler(
                base_env.compiler_env, base_env.ASTenv, base_env.attrs, document.path
            )
            it = iter(compiler.compile(program))
            while True:
                try:
                    a = next(it)
                    logging.info(a)
                    if isinstance(a, Compiler.Warn):
                        if a.line is not None:
                            diagnostics.append(
                                types.Diagnostic(
                                    range=types.Range(
                                        start=types.Position(
                                            line=a.line, character=a.col
                                        ),
                                        end=types.Position(
                                            line=a.line, character=a.end_col
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
                                    end=types.Position(line=e.line, character=e.end_col if e.end_col is not None else 1),
                                ),
                                message=e.msg,
                            )
                        )

        self.diagnostics[document.uri] = (document.version, diagnostics)


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
