# server.py
import logging
from typing import List, Optional
from pygls.lsp.server import LanguageServer
from lsprotocol import types
from omni_compiler import base_env
from omni_compiler.main import Parser, Token, Tokenizer, EOF
from omni_compiler.runtime import ASTNode, Program


server = LanguageServer("my-lang-server", "v0.1")


@server.feature(types.TEXT_DOCUMENT_DID_OPEN)
def did_open(ls: LanguageServer, params: types.DidOpenTextDocumentParams):
    tokens = tokenize(params.text_document.text)
    _token_cache[params.text_document.uri] = tokens
    _ast_cache[params.text_document.uri] = parse(tokens)


@server.feature(types.TEXT_DOCUMENT_DID_CHANGE)
def did_change(ls: LanguageServer, params: types.DidChangeTextDocumentParams):
    doc = ls.workspace.get_text_document(params.text_document.uri)
    tokens = tokenize(doc.source)
    _token_cache[params.text_document.uri] = tokens
    _ast_cache[params.text_document.uri] = parse(tokens)


# --- Document store: uri -> token list ---
_token_cache: dict[str, List[Token]] = {}
_ast_cache: dict[str, ASTNode] = {}


def tokenize(source: str) -> List[Token]:
    """Replace with your actual lexer."""
    print(f"SOURCE:\n{source}\n")
    tknr = Tokenizer(source)
    tkns: list[Token] = []
    while True:
        tkn = tknr.get_next_token()
        tkns.append(tkn)
        if tkn.type == EOF:
            break
    return tkns

def parse(tokens: list[Token]) -> Program:
    psr = Parser(tokens, base_env.ASTenv)
    return psr.program()

def token_at(tokens: List[Token], line: int, col: int) -> Optional[Token]:
    """Find token covering a given (0-indexed) position."""
    for tok in reversed(tokens):
        tok_line = tok.line - 1  # adjust if your lines are 1-indexed
        tok_col = tok.col - 1
        if tok_line == line and tok_col <= col:
            return tok
    return None


TOKEN_TYPES = ["keyword", "variable", "number", "string", "comment", "operator"]
TOKEN_MODIFIERS = []

# Map your token types to LSP semantic token types
TYPE_MAP = {
    "KEYWORD": "keyword",
    "IDENTIFIER": "variable",
    "INT": "number",
    "STRING": "string",
    "COMMENT": "comment",
    "OPERATOR": "operator",
}



@server.feature(
    types.TEXT_DOCUMENT_SEMANTIC_TOKENS_FULL,
    types.SemanticTokensRegistrationOptions(
        legend=types.SemanticTokensLegend(
            token_types=TOKEN_TYPES,
            token_modifiers=TOKEN_MODIFIERS,
        ),
        full=True,
    ),
)
def semantic_tokens(ls: LanguageServer, params: types.SemanticTokensParams):
    tokens = _token_cache.get(params.text_document.uri, [])
    data = []
    prev_line, prev_col = 0, 0

    for tok in tokens:
        match tok.type:
            case "INT":
                tok_type = 'number'
            case 'FLOAT':
                tok_type = 'number'
            case 'FUNC':
                tok_type = 'keyword'
            case 'EOF':
                continue
            case 'STRING':
                tok_type = 'string'
            case 'IDENTIFIER':
                tok_type = 'variable'
            case 'ADD', 'SUBTRACT', 'DIVIDE', 'ASSIGN':
                tok_type = 'operator'
            case _:
                print(f"FAILED: {tok}")
                continue
                
        
        # Since your logs show line=0, col=0, do NOT subtract 1.
        current_line = tok.line
        current_col = tok.col
        
        delta_line = current_line - prev_line
        delta_col = current_col if delta_line > 0 else current_col - prev_col
        
        # Safety check: LSP requires non-negative integers
        if delta_line < 0 or delta_col < 0:
            continue

        type_idx = TOKEN_TYPES.index(tok_type)
        token_len = len(str(tok.value))
        # Change this line in your loop:
        token_text = str(tok.value)
        token_len = len(token_text)

        # Add a print here to see what the server thinks the length is
        print(f"Token: {token_text} | Length: {token_len} | Type: {tok_type}")
        # [deltaLine, deltaStartChar, length, tokenType, tokenModifiers]
        data.extend([delta_line, delta_col, token_len, type_idx, 0])
        
        prev_line, prev_col = current_line, current_col

    return types.SemanticTokens(data=data)



if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    server.start_tcp("0.0.0.0", 2087)
