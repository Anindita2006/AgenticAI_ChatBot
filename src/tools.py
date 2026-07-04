"""Function calling / tool use (Day 5, Session 1): gives the chat model a
calculator so it can compute over figures found in the retrieved CONTEXT
(e.g. "hostel fee x 4 years") instead of guessing an approximate answer.

The model only ever emits a tool call (name + arguments) — this module is what
actually executes it. Arguments are validated before use; never trust a
model-generated argument as safe input (see the "Five Mistakes" slide: a
plausible-looking argument is not the same as a valid one).
"""

CALCULATOR_TOOL = {
    "type": "function",
    "function": {
        "name": "calculate",
        "description": (
            "Perform a math operation (add, subtract, multiply, or divide) on two numbers. "
            "Use this only to compute over a figure already present in the CONTEXT (e.g. "
            "multiplying an annual fee by a number of years, or summing two fee line items) "
            "-- never to invent a number that isn't in the CONTEXT."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "a": {"type": "number", "description": "First operand"},
                "b": {"type": "number", "description": "Second operand"},
                "operation": {
                    "type": "string",
                    "enum": ["add", "subtract", "multiply", "divide"],
                    "description": "Which operation to perform",
                },
            },
            "required": ["a", "b", "operation"],
        },
    },
}

TOOLS = [CALCULATOR_TOOL]

_OPERATIONS = {
    "add": lambda a, b: a + b,
    "subtract": lambda a, b: a - b,
    "multiply": lambda a, b: a * b,
    "divide": lambda a, b: a / b,
}


def execute_calculate(a, b, operation: str) -> float:
    if not isinstance(a, (int, float)) or isinstance(a, bool):
        raise ValueError(f"'a' must be a number, got {a!r}")
    if not isinstance(b, (int, float)) or isinstance(b, bool):
        raise ValueError(f"'b' must be a number, got {b!r}")
    if operation not in _OPERATIONS:
        raise ValueError(f"Unknown operation {operation!r}; must be one of {list(_OPERATIONS)}")
    if operation == "divide" and b == 0:
        raise ValueError("Cannot divide by zero")
    return _OPERATIONS[operation](a, b)


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
