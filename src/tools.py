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

date_checker and percentage_checker follow the same principle: don't let the
model guess at today's date or eyeball a percentage -- give it a tool call for
anything that's actually a computation, not a lookup.
"""

from datetime import datetime

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

DATE_CHECKER_TOOL = {
    "type": "function",
    "function": {
        "name": "check_date",
        "description": (
            "Compare a date found in the CONTEXT (e.g. an admission deadline or exam date) to "
            "today's actual current date. Returns whether it is in the past, today, or in the "
            "future, and how many days apart. Use this for any question like 'has the deadline "
            "passed?', 'is this upcoming?', or 'how many days until X?' -- never guess today's "
            "date or work this out yourself."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "date": {
                    "type": "string",
                    "description": "The date to check, in YYYY-MM-DD format (convert from whatever format it appears in in the CONTEXT, e.g. '15 August 2025' -> '2025-08-15')",
                },
            },
            "required": ["date"],
        },
    },
}

PERCENTAGE_TOOL = {
    "type": "function",
    "function": {
        "name": "calculate_percentage",
        "description": (
            "Compute a percentage calculation on numbers already present in the CONTEXT. Use "
            "operation='of' to find X% of a value (e.g. a 25% scholarship discount on a Rs. "
            "1,20,000 tuition fee). Use operation='ratio' to find what percentage one number is "
            "of another (e.g. students placed out of eligible students)."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "operation": {
                    "type": "string",
                    "enum": ["of", "ratio"],
                    "description": "'of' = percent% of value; 'ratio' = part/whole expressed as a percentage",
                },
                "percent": {"type": "number", "description": "The percentage value, e.g. 25 for 25% (for operation='of')"},
                "value": {"type": "number", "description": "The base value to take the percentage of (for operation='of')"},
                "part": {"type": "number", "description": "The part (for operation='ratio')"},
                "whole": {"type": "number", "description": "The whole (for operation='ratio')"},
            },
            "required": ["operation"],
        },
    },
}

TOOLS = [CALCULATOR_TOOL, DATE_CHECKER_TOOL, PERCENTAGE_TOOL]

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


def execute_check_date(date: str) -> str:
    if not isinstance(date, str):
        raise ValueError(f"'date' must be a YYYY-MM-DD string, got {date!r}")
    try:
        target = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"'date' must be in YYYY-MM-DD format, got {date!r}")

    today = datetime.now().date()
    diff = (target - today).days
    if diff > 0:
        status = f"in the future, {diff} day(s) from today"
    elif diff < 0:
        status = f"in the past, {-diff} day(s) ago"
    else:
        status = "today"
    return f"{target.isoformat()} is {status} (today is {today.isoformat()})"


def execute_calculate_percentage(operation: str, percent=None, value=None, part=None, whole=None) -> float:
    if operation == "of":
        _check_number(percent, "'percent'")
        _check_number(value, "'value'")
        return (percent / 100) * value
    if operation == "ratio":
        _check_number(part, "'part'")
        _check_number(whole, "'whole'")
        if whole == 0:
            raise ValueError("Cannot compute a ratio with whole=0")
        return (part / whole) * 100
    raise ValueError(f"Unknown operation {operation!r}; must be 'of' or 'ratio'")


TOOL_EXECUTORS = {
    "calculate": execute_calculate,
    "check_date": execute_check_date,
    "calculate_percentage": execute_calculate_percentage,
}


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
