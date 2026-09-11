---
name: naming-conventions
description: >
  Naming things is hard. This skill makes it easier. Only use if explicitly requested.
---

Applies to any programming language. Examples use JavaScript.

## English language

Name variables and functions in English.

```js
/* Bad */
const primerNombre = 'Gustavo'
const amigos = ['Kate', 'John']

/* Good */
const firstName = 'Gustavo'
const friends = ['Kate', 'John']
```

> English dominates programming syntax, docs, and learning material. English code improves cohesion.

## Naming convention

Pick **one** naming convention; stay consistent. May use `camelCase`, `PascalCase`, `snake_case`, or another. Follow language docs or popular GitHub repositories.

```js
/* Bad */
const page_count = 5
const shouldUpdate = true

/* Good */
const pageCount = 5
const shouldUpdate = true

/* Good as well */
const page_count = 5
const should_update = true
```

## S-I-D

Names must be _short_, _intuitive_, _descriptive_:

- **Short**. Quick to type and remember;
- **Intuitive**. Reads naturally, near common speech;
- **Descriptive**. Efficiently reflects behavior or contents.

```js
/* Bad */
const a = 5 // "a" could mean anything
const isPaginatable = a > 10 // "Paginatable" sounds extremely unnatural
const shouldPaginatize = a > 10 // Made up verbs are so much fun!

/* Good */
const postCount = 5
const hasPagination = postCount > 10
const shouldPaginate = postCount > 10 // alternatively
```

## Avoid contractions

Do **not** use contractions. They reduce code readability. Prefer short, descriptive names.

```js
/* Bad */
const onItmClk = () => {}

/* Good */
const onItemClick = () => {}
```

## Avoid context duplication

Names should not duplicate definition context. Remove context when readability remains.

```js
class MenuItem {
  /* Method name duplicates the context (which is "MenuItem") */
  handleMenuItemClick = (event) => { ... }

  /* Reads nicely as `MenuItem.handleClick()` */
  handleClick = (event) => { ... }
}
```

## Reflect the expected result

Names should reflect expected result.

```jsx
/* Bad */
const isEnabled = itemCount > 3
return <Button disabled={!isEnabled} />

/* Good */
const isDisabled = itemCount <= 3
return <Button disabled={isDisabled} />
```

---

# Naming functions

## A/HC/LC Pattern

Useful function naming pattern:

```
prefix? + action (A) + high context (HC) + low context? (LC)
```

Pattern examples:

| Name                   | Prefix   | Action (A) | High context (HC) | Low context (LC) |
| ---------------------- | -------- | ---------- | ----------------- | ---------------- |
| `getUser`              |          | `get`      | `User`            |                  |
| `getUserMessages`      |          | `get`      | `User`            | `Messages`       |
| `handleClickOutside`   |          | `handle`   | `Click`           | `Outside`        |
| `shouldDisplayMessage` | `should` | `Display`  | `Message`         |                  |

> **Note:** Context order changes variable meaning. `shouldUpdateComponent` means _you_ will update component; `shouldComponentUpdate` means _component_ updates itself while you control _when_.
> **High context emphasizes variable meaning**.

---

## Actions

Function name's verb. Describes what function _does_.

### `get`

Accesses data immediately (shorthand internal-data getter).

```js
function getFruitCount() {
  return this.fruits.length
}
```

> See also [compose](#compose).

Use `get` for asynchronous operations too:

```js
async function getUser(id) {
  const user = await fetch(`/api/user/${id}`)
  return user
}
```

### `set`

Declaratively changes variable from value `A` to value `B`.

```js
let fruits = 0

function setFruits(nextFruits) {
  fruits = nextFruits
}

setFruits(5)
console.log(fruits) // 5
```

### `reset`

Restores variable's initial value or state.

```js
const initialFruits = 5
let fruits = initialFruits
setFruits(10)
console.log(fruits) // 10

function resetFruits() {
  fruits = initialFruits
}

resetFruits()
console.log(fruits) // 5
```

### `remove`

Removes item _from_ somewhere.

Removing selected filter from search-page collection is `removeFilter`, **not** `deleteFilter`:

```js
function removeFilter(filterName, filters) {
  return filters.filter((name) => name !== filterName)
}

const selectedFilters = ['price', 'availability', 'size']
removeFilter('price', selectedFilters)
```

> See also [delete](#delete).

### `delete`

Erases something completely.

Deleting post in CMS performs `deletePost`, **not** `removePost`.

```js
function deletePost(id) {
  return database.find({ id }).delete()
}
```

> See also [remove](#remove).

> **`remove` or `delete`?**
>
> To distinguish `remove` and `delete`, compare opposites: `add` and `create`.
> `add` needs destination; `create` **requires no destination**. You `add` item _to somewhere_; you don't "`create` it _to somewhere_".
> Pair `remove` with `add`; `delete` with `create`.
>
> Explained in detail [here](https://github.com/kettanaito/naming-cheatsheet/issues/74#issue-1174942962).

### `compose`

Creates new data from existing data. Mostly strings, objects, or functions.

```js
function composePageUrl(pageName, pageId) {
  return pageName.toLowerCase() + '-' + pageId
}
```

> See also [get](#get).

### `handle`

Handles action. Often names callback method.

```js
function handleLinkClick() {
  console.log('Clicked a link!')
}

link.addEventListener('click', handleLinkClick)
```

---

## Context

Domain function operates on.

Function often acts on _something_. State domain or expected data type.

```js
/* A pure function operating with primitives */
function filter(list, predicate) {
  return list.filter(predicate)
}

/* Function operating exactly on posts */
function getRecentPosts(posts) {
  return filter(posts, (post) => post.date === Date.now())
}
```

> Language conventions may allow omitted context. In JavaScript, `filter` commonly operates on Array; explicit `filterArray` is unnecessary.

---

## Prefixes

Prefix clarifies variable meaning. Rare in function names.

### `is`

Describes current context characteristic or state (usually `boolean`).

```js
const color = 'blue'
const isBlue = color === 'blue' // characteristic
const isPresent = true // state

if (isBlue && isPresent) {
  console.log('Blue is present!')
}
```

### `has`

Describes whether current context has value or state (usually `boolean`).

```js
/* Bad */
const isProductsExist = productsCount > 0
const areProductsPresent = productsCount > 0

/* Good */
const hasProducts = productsCount > 0
```

### `should`

Positive conditional statement (usually `boolean`) tied to action.

```js
function shouldUpdateUrl(url, expectedUrl) {
  return url !== expectedUrl
}
```

### `min`/`max`

Represents minimum or maximum value for boundaries or limits.

```js
/**
 * Renders a random amount of posts within
 * the given min/max boundaries.
 */
function renderPosts(posts, minPosts, maxPosts) {
  return posts.slice(0, randomBetween(minPosts, maxPosts))
}
```

### `prev`/`next`

Indicate previous or next variable state in current context. Used for state transitions.

```jsx
async function getPosts() {
  const prevPosts = this.state.posts

  const latestPosts = await fetch('...')
  const nextPosts = concat(prevPosts, latestPosts)

  this.setState({ posts: nextPosts })
}
```

## Singular and Plurals

Use singular names for one value; plural names for multiple values.

```js
/* Bad */
const friends = 'Bob'
const friend = ['Bob', 'Tony', 'Tanya']

/* Good */
const friend = 'Bob'
const friends = ['Bob', 'Tony', 'Tanya']
```
