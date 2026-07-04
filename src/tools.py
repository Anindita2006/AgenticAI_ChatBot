"""Function calling / tool use (Day 5, Session 1): gives the chat model a
calculator so it can compute over figures found in the retrieved CONTEXT
(e.g. "hostel fee x 4 years") instead of guessing an approximate answer.

The model only ever emits a tool call (name + arguments) — this module is what
actually executes it. Arguments are validated before use; never trust a
model-generated argument as safe input (see the "Five Mistakes" slide: a
plausible-looking argument is not the same as a valid one).

"sum" takes a list rather than relying on the model chaining several binary
"add" calls across multiple rounds: in practice, given several already-computed
line items, the model would reliably call the tool for each multiplication but
then still total them itself in plain text (getting the total wrong) instead of
issuing N-1 sequential add calls -- even with an explicit instruction not to.
One "sum over a list" call removes that failure mode entirely for the most
common multi-step pattern (fee line items -> grand total).
"""

CALCULATOR_TOOL = {
    "type": "function",
    "function": {
        "name": "calculate",
        "description": (
            "Perform arithmetic on numbers already present in the CONTEXT -- never to invent a "
            "number that isn't grounded there. Use 'add'/'subtract'/'multiply'/'divide' with two "
            "operands (a, b) for a single operation (e.g. an annual fee x a number of years). Use "
            "'sum' with a 'values' list to total three or more numbers at once (e.g. several fee "
            "line items into a grand total) -- do this in one 'sum' call rather than several "
            "separate additions."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["add", "subtract", "multiply", "divide", "sum"],
                    "description": "Which operation to perform",
                },
                "a": {"type": "number", "description": "First operand (for add/subtract/multiply/divide)"},
                "b": {"type": "number", "description": "Second operand (for add/subtract/multiply/divide)"},
                "values": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "List of three or more numbers to total (for operation='sum')",
                },
            },
            "required": ["operation"],
        },
    },
}

TOOLS = [CALCULATOR_TOOL]

_BINARY_OPERATIONS = {
    "add": lambda a, b: a + b,
    "subtract": lambda a, b: a - b,
    "multiply": lambda a, b: a * b,
    "divide": lambda a, b: a / b,
}


def _check_number(value, label: str) -> None:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{label} must be a number, got {value!r}")


def execute_calculate(operation: str, a=None, b=None, values=None) -> float:
    if operation == "sum":
        if not isinstance(values, list) or len(values) < 2:
            raise ValueError("'values' must be a list of at least 2 numbers for operation='sum'")
        for v in values:
            _check_number(v, "each item in 'values'")
        return sum(values)

    if operation not in _BINARY_OPERATIONS:
        raise ValueError(f"Unknown operation {operation!r}; must be one of {list(_BINARY_OPERATIONS) + ['sum']}")
    _check_number(a, "'a'")
    _check_number(b, "'b'")
    if operation == "divide" and b == 0:
        raise ValueError("Cannot divide by zero")
    return _BINARY_OPERATIONS[operation](a, b)


TOOL_EXECUTORS = {"calculate": execute_calculate}


def run_tool_call(name: str, arguments: dict) -> str:
    """Executes a named tool with validated arguments and returns a string result
    (or an error string) to send back to the model as the tool-role message."""
    executor = TOOL_EXECUTORS.get(name)
    if executor is None:
        return f"Error: no such tool '{name}'"
    try:
        result = executor(**arguments)
    except (ValueError, TypeError, ZeroDivisionError) as exc:
        return f"Error: {exc}"
    return str(result)
