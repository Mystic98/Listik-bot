# Listik-bot domain context

This context defines the shared grocery-list concepts used by the Telegram bot and its future Mini App.

## Access and collaboration

**User**:
A Telegram person registered in Listik-bot. A user may be pending approval or approved for use.
_Avoid_: account, client

**Room**:
An isolated shared shopping space with its own list, templates, and members.
_Avoid_: group, project

**Active room**:
The room whose list and templates the user is currently operating on.
_Avoid_: current list

**Member**:
An approved user who belongs to a room. A member can work with that room's shared shopping data according to their role.
_Avoid_: participant when referring to access rights

## Shopping

**Shopping list**:
The collection of product items belonging to an active room and divided into pending and purchased items.
_Avoid_: cart, order

**Item**:
A product entry in a shopping list with an optional quantity, unit, category, and purchased status.
_Avoid_: product when referring to a concrete list entry

**Category**:
A supermarket department assigned to an item for grouping and navigation.
_Avoid_: tag, label

**Template**:
A reusable set of item definitions that can be applied to a room's shopping list.
_Avoid_: preset, saved list

**Template conflict**:
A situation in which applying a template finds an existing list item with the same product and compatible unit group.
_Avoid_: duplicate error

**Quantity merge**:
An addition of the same product with a compatible unit group increases the existing item's quantity instead of creating a second item.
_Avoid_: silent duplicate

**Manual quantity edit conflict**:
A manual edit based on an outdated item state that cannot overwrite a newer change without showing the user the current value.
_Avoid_: last-write-wins edit
