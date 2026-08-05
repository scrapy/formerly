from __future__ import annotations

import abc
import copy
import inspect
import pickle
import warnings
from typing import Any

import pytest

from formerly import deprecated_class


class MyWarning(UserWarning):
    pass


class SomeBaseClass:
    pass


class NewName(SomeBaseClass):
    pass


# Module-level alias, needed to test pickling.
OldName: Any = deprecated_class("OldName", NewName)


class TestSubclassing:
    def test_no_warning_on_definition(self):
        with warnings.catch_warnings():
            warnings.simplefilter("error")
            deprecated_class("Deprecated", NewName)

    def test_message(self):
        Deprecated: Any = deprecated_class("Deprecated", NewName, category=MyWarning)
        message = (
            r"tests\.test_formerly\.UserClass inherits from deprecated class "
            r"tests\.test_formerly\.Deprecated, please inherit from "
            r"tests\.test_formerly\.NewName\."
            r" \(warning only on first subclass, there may be others\)"
        )
        with pytest.warns(MyWarning, match=message) as record:

            class UserClass(Deprecated):
                pass

        assert record[0].lineno == inspect.getsourcelines(UserClass)[1]

    def test_custom_paths(self):
        Deprecated: Any = deprecated_class(
            "Deprecated",
            NewName,
            old_path="bar.OldClass",
            new_path="foo.NewClass",
            category=MyWarning,
        )

        with pytest.warns(
            MyWarning,
            match=r"UserClass inherits from deprecated class bar\.OldClass, please inherit from foo\.NewClass",
        ):

            class UserClass(Deprecated):
                pass

        with pytest.warns(
            MyWarning,
            match=r"bar\.OldClass is deprecated, instantiate foo\.NewClass instead",
        ):
            Deprecated()

    def test_custom_messages(self):
        Deprecated: Any = deprecated_class(
            "Deprecated",
            NewName,
            category=MyWarning,
            subclass_message="{old} is deprecated.",
            instance_message="{cls} is deprecated.",
            warn_once=False,
        )

        with pytest.warns(
            MyWarning, match=r"tests\.test_formerly\.Deprecated is deprecated\.$"
        ):

            class UserClass(Deprecated):
                pass

        with pytest.warns(
            MyWarning, match=r"tests\.test_formerly\.Deprecated is deprecated\.$"
        ):
            Deprecated()

    def test_only_direct_subclasses_warn(self):
        Deprecated: Any = deprecated_class(
            "Deprecated", NewName, warn_once=False, category=MyWarning
        )

        with pytest.warns(MyWarning, match="UserClass inherits from deprecated class"):

            class UserClass(Deprecated):
                pass

        with warnings.catch_warnings():
            warnings.simplefilter("error", MyWarning)

            class Grandchild(UserClass):
                pass

    def test_warn_once(self):
        Deprecated: Any = deprecated_class("Deprecated", NewName, category=MyWarning)

        with pytest.warns(MyWarning, match="UserClass inherits from deprecated class"):

            class UserClass(Deprecated):
                pass

        with warnings.catch_warnings():
            warnings.simplefilter("error", MyWarning)

            class FooClass(Deprecated):
                pass

            class BarClass(Deprecated):
                pass

    def test_warn_every_time(self):
        Deprecated: Any = deprecated_class(
            "Deprecated", NewName, warn_once=False, category=MyWarning
        )

        with pytest.warns(MyWarning) as record:

            class FooClass(Deprecated):
                pass

            class BarClass(Deprecated):
                pass

        assert len(record) == 2
        assert "only on first subclass" not in str(record[0].message)

    def test_default_category(self):
        Deprecated: Any = deprecated_class("Deprecated", NewName)
        with pytest.warns(DeprecationWarning, match="inherits from deprecated class"):

            class UserClass(Deprecated):
                pass

    def test_custom_metaclass(self):
        Meta = type("Meta", (type,), {})
        New = Meta("New", (), {})
        Deprecated: Any = deprecated_class("Deprecated", New)
        assert isinstance(Deprecated, Meta)

    def test_namespace(self):
        Deprecated: Any = deprecated_class(
            "Deprecated", NewName, namespace={"foo": "bar"}
        )
        assert Deprecated.foo == "bar"

    def test_deprecated_subclass_of_deprecated_class(self):
        with warnings.catch_warnings():
            warnings.simplefilter("error", MyWarning)
            Deprecated: Any = deprecated_class(
                "Deprecated", NewName, category=MyWarning
            )
            AlsoDeprecated: Any = deprecated_class(
                "AlsoDeprecated", Deprecated, new_path="foo.Bar", category=MyWarning
            )

        with pytest.warns(
            MyWarning,
            match=r"AlsoDeprecated is deprecated, instantiate foo\.Bar instead",
        ):
            AlsoDeprecated()

        with pytest.warns(
            MyWarning,
            match=r"UserClass inherits from deprecated class tests\.test_formerly\.AlsoDeprecated, please inherit from foo\.Bar",
        ):

            class UserClass(AlsoDeprecated):
                pass


class TestInstantiation:
    def test_message(self):
        Deprecated: Any = deprecated_class("Deprecated", NewName, category=MyWarning)

        with pytest.warns(
            MyWarning,
            match=r"tests\.test_formerly\.Deprecated is deprecated, instantiate "
            r"tests\.test_formerly\.NewName instead\.",
        ) as record:
            _, lineno = Deprecated(), inspect.getlineno(inspect.currentframe())  # type: ignore[arg-type]

        assert len(record) == 1
        assert record[0].lineno == lineno

    def test_subclass_instances_do_not_warn(self):
        Deprecated: Any = deprecated_class("Deprecated", NewName, category=MyWarning)

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", MyWarning)

            class UserClass(Deprecated):
                pass

        with warnings.catch_warnings():
            warnings.simplefilter("error", MyWarning)
            UserClass()

    def test_init_arguments_are_passed(self):
        class Base:
            def __init__(self, value):
                self.value = value

        Deprecated: Any = deprecated_class("Deprecated", Base, category=MyWarning)

        with pytest.warns(MyWarning):
            assert Deprecated(1).value == 1


@pytest.fixture
def hierarchy():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        Deprecated: Any = deprecated_class("Deprecated", NewName)

        class Migrated(NewName):
            pass

        class Outdated(Deprecated):
            pass

        class AlsoOutdated(Deprecated):
            pass

        class Unrelated:
            pass

    return Deprecated, Migrated, Outdated, AlsoOutdated, Unrelated


class TestChecks:
    def test_issubclass(self, hierarchy):
        Deprecated, Migrated, Outdated, AlsoOutdated, Unrelated = hierarchy

        assert issubclass(Migrated, Deprecated)
        assert issubclass(Outdated, Deprecated)
        assert issubclass(Deprecated, Deprecated)
        assert issubclass(Deprecated, NewName)
        assert not issubclass(Unrelated, Deprecated)
        assert not issubclass(Outdated, AlsoOutdated)
        assert not issubclass(AlsoOutdated, Outdated)

    def test_isinstance(self, hierarchy):
        Deprecated, Migrated, Outdated, AlsoOutdated, Unrelated = hierarchy

        assert isinstance(Migrated(), Deprecated)
        assert isinstance(Outdated(), Deprecated)
        assert not isinstance(Unrelated(), Deprecated)
        assert not isinstance(Outdated(), AlsoOutdated)

    def test_issubclass_non_class(self, hierarchy):
        Deprecated = hierarchy[0]
        with pytest.raises(TypeError, match="must be a class"):
            issubclass(object(), Deprecated)  # type: ignore[arg-type]


class TestClassContract:
    """The alias is a real class, unlike proxy-based deprecation helpers."""

    def test_isclass(self):
        assert inspect.isclass(OldName)

    def test_name(self):
        assert OldName.__name__ == "OldName"
        assert OldName.__module__ == "tests.test_formerly"

    def test_name_without_stack_frame_support(self, monkeypatch):
        monkeypatch.setattr(inspect, "currentframe", lambda: None)
        Deprecated = deprecated_class("Deprecated", NewName)
        assert Deprecated.__name__ == "Deprecated"
        assert Deprecated.__module__ == "formerly"

    def test_mro(self):
        assert OldName.__mro__[1:] == (NewName, SomeBaseClass, object)

    def test_pickle(self):
        assert pickle.loads(pickle.dumps(OldName)) is OldName

    def test_deepcopy_keeps_the_alias(self):
        assert copy.deepcopy(OldName) is OldName

    def test_abc_register(self):
        class Interface(abc.ABC):  # noqa: B024
            pass

        Interface.register(OldName)
        assert issubclass(OldName, Interface)

    def test_type_call(self):
        with pytest.warns(DeprecationWarning, match="inherits from deprecated class"):
            subclass = type("Subclass", (OldName,), {})
        assert issubclass(subclass, NewName)
