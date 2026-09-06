# Coding Philosophies

- Prefer simple, obvious and readable code over clever tricks; no over-engineering or over-productionising. Think of it as beginner friendly.
- Function Design:
	- Do one thing per function;
	- Keep to one level of abstraction within a function;
	- Keep functions simple;
- Adhere to the skill `readable-python`

# Name Conventions

Refer to skill `naming-conventions`.

- Names must be **S-I-D: short, intuitive, descriptive**.
- Function pattern: `prefix? + action + highContext + lowContext`
  - Prefixes (optional): `is | has | should | min | max | prev | next`
  - Actions: `get | set | reset | remove | delete | compose | handle`

Examples

```md
get_user
get_user_messages
handle_click_outside
should_display_message
```