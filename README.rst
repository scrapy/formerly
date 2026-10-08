========
formerly
========

|version| |python_version| |tests| |coverage|

.. |version| image:: https://img.shields.io/pypi/v/formerly
   :target: https://pypi.org/pypi/formerly
   :alt: PyPI Version

.. |python_version| image:: https://img.shields.io/pypi/pyversions/formerly
   :target: https://pypi.org/pypi/formerly
   :alt: Supported Python Versions

.. |tests| image:: https://img.shields.io/github/check-runs/scrapy/formerly/main?label=tests
   :target: https://github.com/scrapy/formerly/actions?query=branch%3Amain
   :alt: Tests

.. |coverage| image:: https://img.shields.io/codecov/c/github/scrapy/formerly/main
   :target: https://codecov.io/github/scrapy/formerly?branch=main
   :alt: Coverage report

``formerly`` renames a class that users inherit from, without breaking them.

Install with:

.. code:: bash

    pip install formerly


Usage
=====

Rename the class, and leave the old name behind as an alias:

.. code:: python

    from formerly import deprecated_class


    class NewName(SomeClass): ...


    OldName = deprecated_class("OldName", NewName)

Now:

-   Subclassing ``OldName`` warns, pointing at the ``class`` statement.

-   Instantiating ``OldName`` warns, but instantiating a subclass does not:
    the subclass author gets one warning where the problem is, not one per
    object.

-   ``issubclass()`` and ``isinstance()`` checks against ``OldName`` accept
    subclasses of ``NewName``, so code that has already migrated keeps passing
    the checks of code that has not.

-   ``OldName`` is a real class: it pickles, survives ``copy.deepcopy()``,
    passes ``inspect.isclass()``, and can be registered with an
    ``abc.ABCMeta`` interface.

Type checkers reject a base class that comes from a variable, so users
subclassing the alias need ``OldName: Any = ...`` on their side, or a
per-statement ignore comment.

Warnings use ``DeprecationWarning`` and report the paths of the classes
involved. Both are configurable, along with the messages themselves:

.. code:: python

    OldName = deprecated_class(
        "OldName",
        NewName,
        category=MyLibraryDeprecationWarning,
        new_path="mylibrary.NewName",
        subclass_message="{cls} inherits from {old}, which is going away in 3.0.",
    )

Messages only tell users to switch to the new class when its path, or
``new_path`` if given, has no ``_``-prefixed part. Pass ``suggest_new=True`` or
``suggest_new=False`` to decide that yourself.

By default only the first subclass warns, since one warning is enough to tell
users to migrate. Pass ``warn_once=False`` to warn on every subclass.

See the ``deprecated_class()`` docstring for the full signature.


Alternatives
============

Renaming a base class asks more of a deprecation helper than renaming a
function does. Each row below is a behavior that a class users inherit from
needs:

.. list-table::
   :header-rows: 1
   :stub-columns: 1

   * -
     - formerly
     - `warnings.deprecated`_
     - `debtcollector`_
     - `Deprecated`_
     - `pyDeprecate`_
   * - Warns where the subclass is defined
     - ✔
     - ✔
     - ✘
     - ✘
     - ✘
   * - Stays quiet when a subclass is instantiated
     - ✔
     - ✔
     - ✘
     - ✘
     - ✘
   * - Warns when the old name is instantiated
     - ✔
     - ✔
     - ✔
     - ✔
     - ✔
   * - Accepts migrated classes in ``issubclass()`` and ``isinstance()``
     - ✔
     - ✘
     - ✘
     - ✘
     - ✔
   * - Is a class: ``pickle``, ``deepcopy``, ``inspect.isclass()``, ``abc``
     - ✔
     - ✔
     - ✔
     - ✔
     - ✘
   * - Reported by type checkers
     - ✘
     - ✔
     - ✘
     - ✘
     - ✘

Only the fourth row is unique to ``formerly``: the old name keeps accepting
classes that already inherit from the new one, so a library can rename a base
class without breaking the ``isinstance()`` checks that its own code, or its
users' code, runs against the old name.

If nothing checks types against the old name, `warnings.deprecated`_ covers the
rest, and adds what ``formerly`` cannot: type checkers report the deprecation
before the code runs. It needs Python 3.13, or `typing_extensions`_ for older
versions, which behaves identically.

Measured on Python 3.13 against ``Deprecated`` 1.3.1, ``debtcollector`` 3.1.0
and ``pyDeprecate`` 0.11.0. ``pyDeprecate`` wraps the class in a proxy object
rather than a class, so subclassing it raises ``TypeError``.

.. _debtcollector: https://pypi.org/project/debtcollector/
.. _Deprecated: https://pypi.org/project/Deprecated/
.. _pyDeprecate: https://pypi.org/project/pyDeprecate/
.. _typing_extensions: https://pypi.org/project/typing-extensions/
.. _warnings.deprecated: https://docs.python.org/3/library/warnings.html#warnings.deprecated
