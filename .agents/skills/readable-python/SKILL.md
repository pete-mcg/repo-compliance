---
name: readable-python
description: >
  A set of Python code practices to improve code readability.
---

## Function Design

### Do One Thing Per Function

A function should be boring and do only the one thing that its name promises and nothing extra; eliminate surprises.

```python
# ❌ BAD: mixes loading, validation, and saving
def process_order(order_id: str) -> None:
    order = db.fetch_order(order_id)
    if order.total <= 0:
        raise ValueError("invalid total")
    db.save_invoice(order)


# ✅ GOOD: each function has one clear job
def validate_order(order: Order) -> None:
    if order.total <= 0:
        raise ValueError("invalid total")


def create_invoice(order_id: str) -> None:
    order = db.fetch_order(order_id)
    validate_order(order)
    db.save_invoice(order)
```

Small functions are easier to test, reuse and read.

**Rule of thumb for spotting violations**: if the function name contains "and", it is probably doing too much.

### Keep To One Level Of Abstraction Within A Function

Do not mix high-level workflow steps with low-level details in the same function.

```python
# ❌ BAD: high-level workflow mixed with low-level calculation details
def process_order(order: Order) -> None:
    validate(order)

    total = Decimal("0")
    for item in order.items:
        total += item.price * item.quantity
    order.total = total

    charge_customer(order)
    send_confirmation(order)


# ✅ GOOD: each line describes one step at the same level
def process_order(order: Order) -> None:
    validate(order)
    calculate_total(order)
    charge_customer(order)
    send_confirmation(order)
```

Consistent abstraction is easier to read. Having to jump between various levels of detail creates cognitive friction.

**Rule of thumb for spotting violations**: if you need to mentally "zoom in" or "zoom out" between adjacent lines, the function is probably mixing levels of abstraction.

### Keep Functions Simple

Enforce a:

- **Max complexity** (McCabe). Aim to have low branching complexity: break complicated decisions into smaller functions.
- **Max nested blocks** (no deeply nested if/for/while). Flat is better than nested. Use guard clauses to handle invalid or uninteresting cases first. Avoid deep indentation when a simple early return will do.

If you hit these limits, refactor.

```python
# ❌ BAD: Complex nested logic
def process_order(order):
    if order.valid:
        if order.in_stock:
            if order.payment_ok:
                if order.address_valid:
                    # 4 levels deep!
                    ...


# ✅ GOOD: Early returns + helper functions
def process_order(order: Order) -> None:
    if not order.valid:
        raise InvalidOrderError()
    if not order.in_stock:
        raise OutOfStockError()

    validate_payment(order)
    validate_address(order)
    ship_order(order)
```

The simpler the function, the easier it is to read and test.

**Rule of thumb for spotting violations**: enforce a max complexity and max nested blocks in your linter.

> Ruff Rule: `C901 Complex-Structure`
>
> Ruff Rule: `PLR1702 Too-Many-Nested-Blocks`

### Prefer Obvious Code Over Clever Code

Write code for the next human reader, not for showing how much Python you know.

```python
# ❌ BAD: Dense and mentally expensive
return next(transform(x) for x in items if is_valid(x) and x.enabled)

# ✅ GOOD: More lines, less effort
for item in items:
    if not is_valid(item):
        continue

    if not item.enabled:
        continue

    return transform(item)

raise ItemNotFoundError()
```

Obvious code lowers review time by increasing clarity.

**Rule of thumb for spotting violations**: if you would need to explain it in, rewrite it. Clear beats impressive.

### Pass State Instead Of Using Globals

Keep mutable state local and pass dependencies as arguments. Avoid assigning to global variables from inside functions.

```python
# ❌ BAD: hidden shared state makes behavior hard to follow
count = 0


def increment():
    global count
    count += 1


increment()
print(count)  # 1


# ✅ GOOD: state is explicit at the call site
def increment(count: int) -> int:
    return count + 1


count = 0
count = increment(count)
print(count)  # 1
```

Explicit state is easier to test and reason about. Globals create hidden coupling between unrelated code.

**Rule of thumb for spotting violations**: monitor for `global` usage; in _most_ cases, `global` is a code smell.

> Ruff Rule: `PLW0603 global-statement`

### Separate Business Logic From Implementation

Keep domain decisions away from databases, HTTP clients, files, and frameworks. Let infrastructure code fetch or save data, and let business code decide what should happen.

```python
# ❌ BAD: business rule is buried inside infrastructure code
def save_order(db, order_id):
    order = db.fetch_order(order_id)

    total = sum(item.price * item.quantity for item in order.items)

    if total >= 100:
        order.status = "ready_for_free_shipping"
    else:
        order.status = "standard_shipping"

    db.save(order)


# ✅ GOOD: business rule is isolated and testable
def shipping_status_for(order):
    total = sum(item.price * item.quantity for item in order.items)

    if total >= 100:
        return "ready_for_free_shipping"

    return "standard_shipping"


def save_order(db, order_id):
    order = db.fetch_order(order_id)
    order.status = shipping_status_for(order)
    db.save(order)
```

Separated logic is easier to test without external systems. It also prevents business rules from being duplicated across adapters.

**Rule of thumb for spotting violations**: if a test needs a database to check a pricing or status rule, the rule is probably in the wrong place. Put decisions in plain Python first.

## Make Illegal States Impossible

Constrain the shape of your data so readers know what can happen. Pydantic at the edges; dataclasses in the core; enums for constrained values.

### Name Magic Values

Move unexplained numbers and strings into named constants. Put shared constants near the top of the module or in a dedicated constants module (e.g. `constants.py`). Use `enums` to group constants together if they logically pertain to the same group.

```python
# ❌ BAD: the values have no meaning at the call site
def calculate_discount(user_type, order_total):
    if user_type == "premium" and order_total > 100:
        return order_total * 0.85
    return order_total


# ✅ GOOD: the names explain the discount policy
PREMIUM_USER = "premium"
PREMIUM_DISCOUNT_THRESHOLD = 100
PREMIUM_DISCOUNT_MULTIPLIER = 0.85


def calculate_discount(user_type, order_total):
    if user_type == PREMIUM_USER and order_total > PREMIUM_DISCOUNT_THRESHOLD:
        return order_total * PREMIUM_DISCOUNT_MULTIPLIER
    return order_total
```

Named values make intent visible and reduce inconsistent copies. They also make policy changes safer.

**Rule of thumb for spotting violations**: if a reader must ask "why this value?", name it. Repeated literals deserve names.

> Ruff Rule: `PLR2004 magic-value-comparison` (partially, identifies unnamed magic numbers but not strings)

### Use Enums for Constrained Sets of Values

Use an enum when a value must be one of a constrained set. Do not scatter raw status strings through the code.

> Think of it like when you used to define Custom Names in the Name Manager of Excel that you would reference in formulas instead of harcoded text. It's for the same reason!

```python
# ❌ BAD: typo-prone magic strings
if order.status == "shippped":
    notify_customer(order)


# ✅ GOOD: allowed values are centralized
class OrderStatus(StrEnum):
    PAID = "paid"
    SHIPPED = "shipped"


if order.status is OrderStatus.SHIPPED:
    notify_customer(order)
```

Hard-coding text strings directly in code ("magic strings") are difficult to maintain, prone to errors (e.g. typos breaking logic) and no clear list of valid values. Enums make invalid states harder to create. They also give autocomplete and static analysis more useful information.

**Rule of thumb for spotting violations**: if a string controls behavior, consider an enum.

### Use Dataclasses Not Dictionaries For Domain Data

Dicts are for loose or temporary data (e.g. JSON payloads, metadata, lookup tables and temporary glue code). Prefer dataclasses over anonymous dictionaries for structured, well-defined data, that carry data without validation, persistence, or framework behavior. Use Pydantic instead at IO boundaries where parsing and validation are required.

```python
# ❌ BAD: field names and types are implicit
invoice = {
    "id": "INV-123",
    "total": Decimal("149.00"),
    "paid": False,
}

# ✅ GOOD: shape and intent are explicit
from dataclasses import dataclass


@dataclass(frozen=True)
class InvoiceSummary:
    id: str
    total: Decimal
    paid: bool


invoice = InvoiceSummary(
    id="INV-123",
    total=Decimal("149.00"),
    paid=False,
)
```

Named data gives readers and tools something concrete to understand. It also catches field mistakes earlier.

**Rule of thumb for spotting violations**: if the data represents a part of your domain model (e.g. User, Order, Invoice, or similar concept), give it a type. If it's incidental, dynamic or external, a dictionary is fine.

Use a dataclass when the code needs a clear named shape.

### Pydantic Models for All IO

Always define a Pydantic model and validate external data immediately at the boundary, before they enter core logic. This includes for example:

- API responses: `response.json()` → immediate `Model.model_validate()`
- Config files: `json.load()` → immediate `Model.model_validate()`
- CLI arguments*: `argparse.Namespace` → convert to Pydantic model
- Environment variables: Use `pydantic-settings` instead of raw `os.getenv()`

```python
# ❌ BAD: Raw dict from API/file
def process_user_data(data: dict) -> None:
    name = data["name"]  # Could fail, no validation
    age = data.get("age", 0)  # Type is Any


# ✅ GOOD: Pydantic model + immediate validation
from pydantic import BaseModel, Field


class UserData(BaseModel):
    name: str = Field(min_length=1)
    age: int = Field(ge=0, le=150)


def process_user_data(data: dict) -> None:
    user = UserData.model_validate(data)  # Fails fast with clear errors
    # Now user.name and user.age are fully typed and validated
```

Validated inputs keep messy external data out of the core. Failures happen early, close to the boundary.

**Rule of thumb for spotting violations**: use Pydantic at the edges, dataclasses in the core, and enums for constrained values. Do not let raw payloads leak through the application.

## Exception Handling

### Keep Try Blocks Narrow

Put only the operation that can raise the expected exception inside the try block. Do not hide unrelated work under the same exception handler.

```python
# ❌ BAD: too much code is covered by the same handler
try:
    user = find_user(user_id)
    audit_login(user)
    send_welcome_email(user)
except UserNotFoundError:
    return None

# ✅ GOOD: only the risky lookup is inside the try block
try:
    user = find_user(user_id)
except UserNotFoundError:
    return None

audit_login(user)
send_welcome_email(user)
```

Narrow handlers make it clear which failure is expected. They also avoid accidentally swallowing bugs from later lines.

**Rule of thumb for spotting violations**: ask whether every line inside the try block can raise the exception being caught. If not, move it out.

### Avoid Bare Exceptions

Catch the exceptions you know how to handle and do something useful. Avoid bare except blocks, silent pass statements, and empty re-raises.

```python
# ❌ BAD: Hides all errors
try:
    risky_operation()
except Exception:
    pass

# ✅ GOOD: Catch specific exceptions
try:
    risky_operation()
except (ValueError, KeyError) as e:
    logger.error(f"Expected error: {e}")
    raise
```

Specific handling tells readers what failure is expected and what the program will do next. Silent failures make systems unreliable and hard to debug.

**Rule of thumb for spotting violations**: if an except block does not log, recover, translate, or add context, question why it exists. Never hide errors by default.

> Ruff Rule: `E722 bare-except`

### Easier to Ask Forgiveness than Permission (EAFP)

Write code that assumes the existence of valid keys or attributes etc, and handles exceptions if they aren’t present.

```python
# ❌ BAD: checks first, then performs a separate operation
if path.exists():
    content = path.read_text()
else:
    content = ""

# ✅ GOOD: performs the operation and handles the expected failure
try:
    content = path.read_text()
except FileNotFoundError:
    content = ""
```

Often results in more concise and efficient code, as it minimizes the need for explicit pre-checks.

**Rule of thumb for spotting violations**: if the check only predicts whether the next line will fail, handle the failure instead. Ask for forgiveness when failure is normal and recoverable.

## Types

### Add Type Hints

Use type hints for function parameters, return values, and important variables.

```python
# ❌ BAD: callers must guess the expected shape
def calculate_tax(amount, rate):
    return amount * rate


# ✅ GOOD: types make the contract clear
def calculate_tax(amount: Decimal, rate: Decimal) -> Decimal:
    return amount * rate
```

Types improve readability without changing runtime behavior. They document intent and help tools find bugs before runtime.

**Rule of thumb for spotting violations**: if another module calls it, type it. Untyped public functions make every caller guess.

> Ruff Rule: `ANN flake8-annotations`

### Avoid Any Where Possible

Do not use `Any` to silence type errors in normal application code. If a value is truly unknown such as at a boundary and requires `Any`, validate or narrow it as soon as possible.

```python
# ❌ BAD: Any disables useful checking
def customer_name(customer: Any) -> str:
    return customer["name"]


# ✅ GOOD: the expected shape is explicit
class CustomerPayload(TypedDict):
    name: str


def customer_name(customer: CustomerPayload) -> str:
    return customer["name"]
```

Avoiding `Any` preserves the value of type checking. It forces unclear data contracts into the open.

**Rule of thumb for spotting violations**: treat `Any` as a temporary quarantine, not a design. Narrow it at the first reasonable point.

> Ruff Rule: `ANN401 any-type`

## Maintainability

### Don't Repeat Yourself (DRY)

Extract repeated logic when the copies represent the same rule or workflow. Do not force unrelated code into one abstraction just because it looks similar.

```python
# ❌ BAD: the same logging rule is copied into multiple functions
def save_user(user):
    print("Starting task")
    database.save(user)
    print("Finished task")


def send_email(email):
    print("Starting task")
    email_service.send(email)
    print("Finished task")


# ✅ GOOD: the shared logging rule lives in one place
def log_task(func):
    def wrapper(*args, **kwargs):
        print("Starting task")
        result = func(*args, **kwargs)
        print("Finished task")
        return result

    return wrapper


@log_task
def save_user(user):
    database.save(user)


@log_task
def send_email(email):
    email_service.send(email)
```

Good deduplication prevents future fixes from being missed in one copy. Poor deduplication creates awkward abstractions that are harder to change.

**Rule of thumb for spotting violations**: duplicate knowledge is the problem, not duplicate text. Extract code when the copies should always change together.

> SonarQube can help spot duplicate lines of code.

### Make Structure Consistent Everywhere

A developer should be able to predict what your code looks like before they open the file. E.g. Have consistent:

- Naming
- File organisation
- Class responsibilities
- Imports
- Error handling
- Project layout

```python
# BAD: the same role has three different names
class UserService: ...


class ProductManager: ...


class InvoiceHandler: ...


# GOOD: the naming convention communicates the architecture
class UserService: ...


class ProductService: ...


class InvoiceService: ...
```

```text
# BAD: each feature uses a different file name for the same layer
users/
    service.py

products/
    manager.py

billing/
    invoice_handler.py


# GOOD: once you know one module, you know where to look in the others
users/
    service.py

products/
    service.py

billing/
    service.py
```

```python
# BAD: similar operations use different verbs
create_user()
get_user()
fetch_order()
retrieve_invoice()
load_customer()


# GOOD: one convention is used everywhere
create_user()
get_user()
get_order()
get_invoice()
get_customer()
```

```python
# BAD: service classes all expose their actions differently
class UserService:
    def create(self): ...

    def update(self): ...

    def delete(self): ...


class ProductService:
    def add_product(self): ...

    def modify_product(self): ...

    def remove_product(self): ...


# GOOD: related classes have the same shape
class UserService:
    def create(self): ...

    def update(self): ...

    def delete(self): ...


class ProductService:
    def create(self): ...

    def update(self): ...

    def delete(self): ...
```

```python
# BAD: filesystem paths are imported three different ways
import pathlib
from pathlib import Path
from pathlib import *


# GOOD: the project has one import style for this dependency
from pathlib import Path
```

```python
# BAD: not-found cases behave differently in each function
def get_user(user_id):
    return db.find_user(user_id)


def get_order(order_id):
    order = db.find_order(order_id)
    if order is None:
        raise ValueError()
    return order


def get_product(product_id):
    product = db.find_product(product_id)
    if product is None:
        return None
    return product


# GOOD: callers can rely on one failure convention
def get_user(user_id):
    user = db.find_user(user_id)
    if user is None:
        raise NotFoundError()
    return user


def get_order(order_id):
    order = db.find_order(order_id)
    if order is None:
        raise NotFoundError()
    return order


def get_product(product_id):
    product = db.find_product(product_id)
    if product is None:
        raise NotFoundError()
    return product
```

```text
# BAD: every feature has grown its own layout
users/
    handlers.py
    utils.py

orders/
    api.py
    helpers.py

billing/
    views.py
    services.py


# GOOD: each feature follows the same structure
users/
    api.py
    service.py
    models.py

orders/
    api.py
    service.py
    models.py

billing/
    api.py
    service.py
    models.py
```

When developers can predict where things live and how they're written, the code feels much simpler.

**Rule of thumb for spotting violations**: before inventing a pattern, look at nearby code. Match the codebase unless there is a clear reason to change it.
