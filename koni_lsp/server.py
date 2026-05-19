import logging
import re

from lsprotocol import types

from pygls.lsp.server import LanguageServer
from pygls.workspace import TextDocument

from koni_compiler import base_env
from koni_compiler.main import (
    Compiler,
    Parser,
    TokenType,
    Tokenizer,
    Token,
    CompilationException,
    Warn,
)

ADDITION = re.compile(r'^\s*(\d+)\s*\+\s*(\d+)\s*=\s*(\d+)?$')


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

        logging.info('SOURCEa:\n%s', document.source)
        tkns: list[Token] | None = None
        try:
            tknr = Tokenizer(document.source)
            tkns = []
            while True:
                logging.info('hi')
                tkn = tknr.get_next_token()
                if isinstance(tkn, list):
                    tkns += tkn
                else:
                    tkns.append(tkn)
                if tkns[-1].type == TokenType.EOF:
                    break
            logging.info('break')
        except CompilationException as e:
            if e.end_line is None:
                endln = e.line
            else:
                endln = e.end_line
            if e.end_col is None:
                end_col = e.col
            else:
                end_col = e.end_col
            diagnostics.append(
                types.Diagnostic(
                    message=e.message,
                    range=types.Range(
                        start=types.Position(
                            line=e.line,
                            character=e.col,
                        ),
                        end=types.Position(line=endln, character=end_col),
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
                        w = next(p)
                        if w.end_line is None:
                            endln = w.line
                        else:
                            endln = w.end_line
                        if w.end_col is None:
                            end_col = w.col
                        else:
                            end_col = w.end_col
                        helps = [
                            types.DiagnosticRelatedInformation(
                                types.Location(
                                    document.uri,
                                    types.Range(
                                        types.Position(w.line, w.col),
                                        types.Position(endln, end_col),
                                    ),
                                ),
                                help.value,
                            )
                            for help in w.helps
                        ]
                        diagnostics.append(
                            types.Diagnostic(
                                message=w.message,
                                severity=types.DiagnosticSeverity.Warning,
                                range=types.Range(
                                    start=types.Position(line=w.line, character=w.col),
                                    end=types.Position(line=endln, character=end_col),
                                ),
                                related_information=helps,
                            )
                        )
                        logging.info(w)
                    except StopIteration as e:
                        program = e.value
                        break
            except CompilationException as e:
                if e.end_line is None:
                    endln = e.line
                else:
                    endln = e.end_line
                if e.end_col is None:
                    end_col = e.col
                else:
                    end_col = e.end_col
                helps = [
                    types.DiagnosticRelatedInformation(
                        types.Location(
                            document.uri,
                            types.Range(
                                types.Position(e.line, e.col),
                                types.Position(endln, end_col),
                            ),
                        ),
                        help.value,
                    )
                    for help in e.helps
                ]

                diagnostics.append(
                    types.Diagnostic(
                        message=e.message,
                        range=types.Range(
                            start=types.Position(line=e.line, character=e.col),
                            end=types.Position(line=endln, character=end_col),
                        ),
                        related_information=helps,
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
                    if isinstance(a, Warn):
                        if a.end_line is None:
                            endln = a.line
                        else:
                            endln = a.end_line
                        if a.end_col is None:
                            end_col = a.col
                        else:
                            end_col = a.end_col

                        helps = [
                            types.DiagnosticRelatedInformation(
                                types.Location(
                                    document.uri,
                                    types.Range(
                                        types.Position(a.line, a.col),
                                        types.Position(endln, end_col),
                                    ),
                                ),
                                help.value,
                            )
                            for help in a.helps
                        ]

                        diagnostics.append(
                            types.Diagnostic(
                                range=types.Range(
                                    start=types.Position(line=a.line, character=a.col),
                                    end=types.Position(line=endln, character=end_col),
                                ),
                                message=a.message,
                                severity=types.DiagnosticSeverity.Warning,
                                related_information=helps,
                            )
                        )
                except StopIteration:
                    break
                except CompilationException as e:
                    if e.end_line is None:
                        endln = e.line
                    else:
                        endln = e.end_line
                    if e.end_col is None:
                        end_col = e.col
                    else:
                        end_col = e.end_col

                    helps = [
                        types.DiagnosticRelatedInformation(
                            types.Location(
                                document.uri,
                                types.Range(
                                    types.Position(e.line, e.col),
                                    types.Position(endln, end_col),
                                ),
                            ),
                            help.value,
                        )
                        for help in e.helps
                    ]

                    diagnostics.append(
                        types.Diagnostic(
                            range=types.Range(
                                start=types.Position(
                                    line=e.line,
                                    character=e.col if e.col is not None else 0,
                                ),
                                end=types.Position(
                                    line=endln,
                                    character=end_col,
                                ),
                            ),
                            message=e.message,
                        )
                    )
                break

        self.diagnostics[document.uri] = (document.version, diagnostics)
        # ... run compiler ...
        after = len(base_env.compiler_env)
        logging.info('ASTenv size before: %d, after: %d', before, after)


server = PublishDiagnosticServer('diagnostic-server', 'v1')


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


@server.feature(
    types.TEXT_DOCUMENT_COMPLETION,
    types.CompletionOptions(trigger_characters=['.', ' ']),
)
def completions(ls: PublishDiagnosticServer, params: types.CompletionParams):
    doc = ls.workspace.get_text_document(params.text_document.uri)
    # Use your AST/compiler env to suggest symbols
    items = []
    for name in base_env.compiler_env:
        items.append(types.CompletionItem(label=name))
    return types.CompletionList(is_incomplete=False, items=items)


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


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(message)s')
    server.start_io()
