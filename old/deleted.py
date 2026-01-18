from main import Token, PRECEDENCE, IDENTIFIER, ADD, INT, SUB, MUL, DIV
def infix_to_rpn(tokens: list[Token]) -> list[Token]:
    output: list[Token] = []
    operators: list[Token] = []

    for token in tokens:
        if token.type == INT or token.type == IDENTIFIER:
            output.append(token)

        elif token.type == ADD:
            while (
                operators
                and operators[-1].type == ADD
                and PRECEDENCE[operators[-1].type] >= PRECEDENCE[token.type]
            ):
                output.append(operators.pop())
            operators.append(token)

        else:
            raise SyntaxError(f"Unsupported token {token.type}")

    while operators:
        output.append(operators.pop())

    return output

def eval_rpm(tokens: list[Token | None]):
    stack = []
    for token in tokens:
        if token is None:
            raise SyntaxError('Unexpected end of input')     
        if token.type == INT:
            stack.append(token.value)
        elif token.type == ADD:
            rhs = stack.pop()
            lhs = stack.pop()
            stack.append(lhs + rhs)
        elif token.type == SUB:
            rhs = stack.pop()
            lhs = stack.pop()
            stack.append(lhs - rhs)
        elif token.type == MUL:
            rhs = stack.pop()
            lhs = stack.pop()
            stack.append(lhs * rhs)
        elif token.type == DIV:
            rhs = stack.pop()
            lhs = stack.pop()
            stack.append(lhs / rhs)
        else:
            raise SyntaxError(f'Unexpected token {token.type}. Expected INT or ADD')
    return stack[0]
