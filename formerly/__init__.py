from __future__ import annotations

import inspect
import warnings
from typing import Any, TypeVar, cast

__all__ = ["deprecated_class"]

_T = TypeVar("_T")


def deprecated_class(
    name: str,
    new_class: type[_T],
    *,
    namespace: dict[str, Any] | None = None,
    category: type[Warning] = DeprecationWarning,
    warn_once: bool = True,
    old_path: str | None = None,
    new_path: str | None = None,
    suggest_new: bool | None = None,
    subclass_message: str | None = None,
    instance_message: str | None = None,
) -> type[_T]:
    """Return a deprecated alias of *new_class* named *name*.

    Subclassing the alias warns, and so does instantiating it, but
    instantiating a subclass does not. Subclasses of *new_class* count as
    subclasses of the alias, so ``issubclass()`` and ``isinstance()`` checks
    against the alias keep working for code that has already migrated.

    Use it to rename a class that users inherit from::

        class NewName(SomeClass): ...


        OldName = deprecated_class("OldName", NewName)

    *namespace* is added to the alias, e.g. to keep attributes that
    *new_class* no longer defines.

    *old_path* and *new_path* replace the ``module.Name`` paths that the
    warning messages report, which is useful when either class is reexported
    from a different module.

    The warning messages tell users to use *new_class* instead, unless its
    path, or *new_path* if given, has a ``_``-prefixed part. Set
    *suggest_new* to ``True`` or ``False`` to decide that yourself.

    *subclass_message* and *instance_message* replace the warning messages.
    Both may use the ``{cls}``, ``{old}`` and ``{new}`` fields, filled with
    the path of the subclass or instantiated class, of the alias, and of
    *new_class*.

    Set *warn_once* to ``False`` to warn on every subclass instead of only on
    the first one.
    """
    if suggest_new is None:
        suggest_new = not _is_private(new_path or _path(new_class))
    subclass_template = subclass_message or (
        "{cls} inherits from deprecated class {old}"
        + (", please inherit from {new}." if suggest_new else ".")
    )
    instance_template = instance_message or (
        "{cls} is deprecated" + (", instantiate {new} instead." if suggest_new else ".")
    )

    alias: type[_T] | None = None
    warned = False

    class DeprecatedClass(type(new_class)):  # type: ignore[misc]
        def __init__(
            cls,
            cls_name: str,
            bases: tuple[type, ...],
            cls_namespace: dict[str, Any],
        ) -> None:
            nonlocal warned
            # A direct subclass of the alias is the only thing worth warning
            # about: the alias itself is created with alias still unset, and
            # deeper descendants are the subclass author's business. A class
            # with a more derived metaclass is an alias of the alias, built by
            # another deprecated_class() call, and its own warnings suffice.
            if (
                type(cls) is DeprecatedClass
                and alias in bases
                and not (warn_once and warned)
            ):
                assert alias is not None
                warned = True
                message = subclass_template.format(
                    cls=_path(cls),
                    old=old_path or _path(alias),
                    new=new_path or _path(new_class),
                )
                if warn_once:
                    message += " (warning only on first subclass, there may be others)"
                warnings.warn(message, category, stacklevel=2)
            super().__init__(cls_name, bases, cls_namespace)

        def __call__(cls, *args: Any, **kwargs: Any) -> Any:
            if cls is alias:
                assert alias is not None
                warnings.warn(
                    instance_template.format(
                        cls=old_path or _path(alias),
                        new=new_path or _path(new_class),
                    ),
                    category,
                    stacklevel=2,
                )
            return super().__call__(*args, **kwargs)

        # https://docs.python.org/3/reference/datamodel.html#customizing-instance-and-subclass-checks
        def __instancecheck__(cls, instance: Any) -> bool:
            return any(
                cls.__subclasscheck__(c) for c in (type(instance), instance.__class__)
            )

        def __subclasscheck__(cls, subclass: type) -> bool:
            if cls is not alias:
                # Subclasses of the alias are ordinary classes, and checks
                # against them must not be answered by the alias rules.
                return cast("bool", super().__subclasscheck__(subclass))
            if not inspect.isclass(subclass):
                raise TypeError("issubclass() arg 1 must be a class")
            return any(c in {cls, new_class} for c in getattr(subclass, "__mro__", ()))

    alias = DeprecatedClass(name, (new_class,), namespace or {})

    # Pickling looks the alias up by qualified name, so it must report the
    # module where it is defined rather than this one.
    frame = inspect.currentframe()
    if frame is not None and frame.f_back is not None:
        alias.__module__ = frame.f_back.f_globals.get("__name__", alias.__module__)

    return alias


def _path(cls: type) -> str:
    return f"{cls.__module__}.{cls.__name__}"


def _is_private(path: str) -> bool:
    return any(
        part.startswith("_") and not part.endswith("__") for part in path.split(".")
    )
