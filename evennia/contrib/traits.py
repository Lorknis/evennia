"""
Traits

Whitenoise 2014, Ainneve contributors,
Griatch 2020


A `Trait` represents a modifiable property on (usually) a Character. They can
be used to represent everything from attributes (str, agi etc) to skills
(hunting 10, swords 14 etc) and dynamically changing things like HP, XP etc.

Traits use Evennia Attributes under the hood, making them persistent (they survive
a server reload/reboot).

## Adding Traits to a typeclass

To access and manipulate traits on an object, its Typeclass needs to have a
`TraitHandler` assigned it. Usually, the handler is made available as `.traits`
(in the same way as `.tags` or `.attributes`).

Here's an example for adding the TraitHandler to the base Object class:

    ```python
    # mygame/typeclasses/objects.py

    from evennia import DefaultObject
    from evennia.utils import lazy_property
    from evennia.contrib.traits import TraitHandler

    # ...

    class Object(DefaultObject):
        ...
        @lazy_property
        def traits(self):
            # this adds the handler as .traits
            return TraitHandler(self)

    ```

After a reload you can now try adding some example traits:

## Using traits

A trait is added to the traithandler, after which one can access it
as a property on the handler (similarly to how you can do .db.attrname for Attributes
in Evennia).

```python
# this is an example using the "static" trait, described below
>>> obj.traits.add("hunting", "Hunting Skill", trait_type="static", base=4)
>>> obj.traits.hunting.value
4
>>> obj.traits.hunting.value += 5
>>> obj.traits.hunting.value
9
>>> obj.traits.add("hp", "Health", trait_type="gauge", min=0, max=100)
>>> obj.traits.hp.value
100
>>> obj.traits.hp -= 200
>>> obj.traits.hp.value
0
>>> obj.traits.hp.reset()
>>> obj.traits.hp.value
100
# you can also access property with getitem
>>> obj.traits.hp["value"]
100
# you can store arbitrary data persistently as well
>>> obj.traits.hp.effect = "poisoned!"
>>> obj.traits.hp.effect
"poisoned!"

```

When adding the trait, you supply the name of the property (`hunting`) along
with a more human-friendly name ("Hunting Skill"). The latter will show if you
print the trait etc. The `trait_type` is important, this specifies which type
of trait this is.


## Trait types

All default traits have a read-only `.value` property that shows the relevant or
'current' value of the trait. Exactly what this means depends on the type of trait.

Traits can also be combined to do arithmetic with their .value, if both have a
compatible type.

```python
>>> trait1 + trait2
54
>>> trait1.value
3
>>> trait1 + 2
>>> trait1.value
5

```

Two numerical traits can also be compared (bigger-than etc), which is useful in
all sorts of rule-resolution.

```python

if trait1 > trait2:
    # do stuff

```
## Static trait

`value = base + mod`

The static trait has a `base` value and an optional `mod`-ifier. A typical use
of a static trait would be a Strength stat or Skill value. That is, something
that varies slowly or not at all, and which may be modified in-place.

```python
>>> obj.traits.add("str", "Strength", trait_type="static", base=10, mod=2)
>>> obj.traits.mytrait.value
12   # base + mod
>>> obj.traits.mytrait.base += 2
>>> obj.traits.mytrait.mod += 1
>>> obj.traits.mytrait.value
15
>>> obj.traits.mytrait.mod = 0
>>> obj.traits.mytrait.value
12

```

### Counter

    min/unset     base    base+mod                       max/unset
     |--------------|--------|---------X--------X------------|
                                    current   value
                                              = current
                                              + mod

A counter describes a value that can move from a base. The `current` property
is the thing usually modified. It starts at the `base`. One can also add a modifier,
which will both be added to the base and to current (forming .value).
The min/max of the range are optional, a boundary set to None will remove it.

```python
>>> obj.traits.add("hunting", "Hunting Skill", trait_type="counter",
                   base=10, mod=1, min=0, max=100)
>>> obj.traits.hunting.value
11  # current starts at base + mod
>>> obj.traits.hunting.current += 10
>>> obj.traits.hunting.value
21
# reset back to base+mod by deleting current
>>> del obj.traits.hunting.current
>>> obj.traits.hunting.value
11
>>> obj.traits.hunting.max = None  # removing upper bound

```

Counters have some extra properties:

`descs` is a dict {upper_bound:text_description}. This allows for easily
storing a more human-friendly description of the current value in the
interval. Here is an example for skill values between 0 and 10:
    {0: "unskilled", 1: "neophyte", 5: "trained", 7: "expert", 9: "master"}
The keys must be supplied from smallest to largest. Any values below the lowest and above the
highest description will be considered to be included in the closest description slot.
By calling `.desc()` on the Counter, will you get the text matching the current `value`
value.

```python
# (could also have passed descs= to traits.add())
>>> obj.traits.hunting.descs = {
    0: "unskilled", 10: "neophyte", 50: "trained", 70: "expert", 90: "master"}
>>> obj.traits.hunting.value
11
>>> obj.traits.hunting.desc()
"neophyte"
>>> obj.traits.hunting.current += 60
>>> obj.traits.hunting.value
71
>>> obj.traits.hunting.desc()
"expert"

```

#### .rate

The `rate` property defaults to 0. If set to a value different from 0, it
allows the trait to change value dynamically. This could be used for example
for an attribute that was temporarily lowered but will gradually (or abruptly)
recover after a certain time. The rate is given as change of the `current`
per-second, and the .value will still be restrained by min/max boundaries, if
those are set.

It is also possible to set a ".ratetarget", for the auto-change to stop at
(rather than at the min/max boundaries). This allows the value to return to
a previous value.

```python

>>> obj.traits.hunting.value
71
>>> obj.traits.hunting.ratetarget = 71
# debuff hunting for some reason
>>> obj.traits.hunting.current -= 30
>>> obj.traits.hunting.value
41
>>> obj.traits.hunting.rate = 1  # 1/s increase
# Waiting 5s
>>> obj.traits.hunting.value
46
# Waiting 8s
>>> obj.traits.hunting.value
54
# Waiting 100s
>>> obj.traits.hunting.value
71    # we have stopped at the ratetarget
>>> obj.traits.hunting.rate = 0  # disable auto-change

```
Note that if rate is a non-integer, the resulting .value (at least until it
reaches the boundary) will likely also come out a float. If you expect an
integer, you must run run int() on the result yourself.

#### .percentage()

If both min and max are defined, the `.percentage()` method of the trait will
return the value as a percentage.

```python
>>> obj.traits.hunting.percentage()
"71.0%"

```

### Gauge

This emulates a [fuel-] gauge that empties from a base+mod value.

    min/0                                            max=base+mod
     |-----------------------X---------------------------|
                           value
                          = current

The 'current' value will start from a full gauge. The .max property is
read-only and is set by .base + .mod. So contrary to a Counter, the modifier
only applies to the max value of the gauge and not the current value. The
minimum bound defaults to 0. This trait is useful for showing resources that
can deplete, like health, stamina and the like.

```python
>>> obj.traits.add("hp", "Health", trait_type="gauge", base=100)
>>> obj.traits.hp.value  # (or .current)
100
>>> obj.traits.hp.mod = 10
>>> obj.traits.hp.value
110
>>> obj.traits.hp.current -= 30
>>> obj.traits.hp.value
80

```

Same as Counters, Gauges can also have `descs` to describe the interval and can also
have `rate` and `ratetarget` to auto-update the value. The rate is particularly useful
for gauges, for everything from poison slowly draining your health, to resting gradually
increasing it. You can also use the `.percentage()` function to show the current value
as a percentage.

### Trait

A single value of any type.

This is the 'base' Trait, meant to inherit from if you want to make your own
trait-types (see below). Its .value can be anything (that can be stored in an Attribute)
and if it's a integer/float you can do arithmetic with it, but otherwise it
acts just like a glorified Attribute.


```python
>>> obj.traits.add("mytrait", "My Trait", trait_type="trait", value=30)
>>> obj.traits.mytrait.value
30
>>> obj.traits.mytrait.value = "stringvalue"
>>> obj.traits.mytrait.value
"stringvalue"

```

## Expanding with your own Traits

A Trait is a class inhering from `evennia.contrib.traits.Trait` (or
from one of the existing Trait classes).

```python
# in a file, say, 'mygame/world/traits.py'

from evennia.contrib.traits import Trait

class RageTrait(Trait):

    trait_type = "rage"
    default_keys = {
        "rage": 0
    }

```

Above is an example custom-trait-class "rage" that stores a property "rage" on
itself, with a default value of 0. This has all the
functionality of a Trait - for example, if you do del on the `rage` property, it will be
set back to its default (0). If you wanted to customize what it does, you
just add `rage` property get/setters/deleters on the class.

To add your custom RageTrait to Evennia, add the following to your settings file
(assuming your class is in mygame/world/traits.py):

    TRAIT_CLASS_PATHS = ["world.traits.RageTrait"]

Reload the server and you should now be able to use your trait:

```python
>>> obj.traits.add("mood", "A dark mood", rage=30)
>>> obj.traits.mood.rage
30

```

----

"""


from time import time
from django.conf import settings
from functools import total_ordering
from evennia.utils.dbserialize import _SaverDict
from evennia.utils import logger
from evennia.utils.utils import inherits_from, class_from_module, list_to_string, percent


# Available Trait classes.
# This way the user can easily supply their own. Each
# class should have a class-property `trait_type` to
# identify the Trait class. The default ones are "static",
# "counter" and "gauge".

_TRAIT_CLASS_PATHS = [
    "evennia.contrib.traits.Trait",
    "evennia.contrib.traits.StaticTrait",
    "evennia.contrib.traits.CounterTrait",
    "evennia.contrib.traits.GaugeTrait",
]

if hasattr(settings, "TRAIT_CLASS_PATHS"):
    _TRAIT_CLASS_PATHS += settings.TRAIT_CLASS_PATHS

# delay trait-class import to avoid circular import
_TRAIT_CLASSES = None


def _delayed_import_trait_classes():
    """
    Import classes based on the given paths. Note that
    imports from settings are last in the list, so if they
    have the same trait_type set, they will replace the
    default.
    """
    global _TRAIT_CLASSES
    if _TRAIT_CLASSES is None:
        _TRAIT_CLASSES = {}
        for classpath in _TRAIT_CLASS_PATHS:
            try:
                cls = class_from_module(classpath)
            except ImportError:
                logger.log_trace(f"Could not import Trait from {classpath}.")
            else:
                if hasattr(cls, "trait_type"):
                    trait_type = cls.trait_type
                else:
                    trait_type = str(cls.__name___).lower()
                _TRAIT_CLASSES[trait_type] = cls


_GA = object.__getattribute__
_SA = object.__setattr__
_DA = object.__delattr__

# this is the default we offer in TraitHandler.add
DEFAULT_TRAIT_TYPE = "static"


class TraitException(RuntimeError):
    """
    Base exception class raised by `Trait` objects.

    Args:
        msg (str): informative error message

    """

    def __init__(self, msg):
        self.msg = msg


class MandatoryTraitKey:
    """
    This represents a required key that must be
    supplied when a Trait is initialized. It's used
    by Trait classes when defining their required keys.
    """


class TraitHandler:
    """
    Factory class that instantiates Trait objects.

    """

    def __init__(self, obj, db_attribute_key="traits", db_attribute_category="traits"):
        """
        Initialize the handler and set up its internal Attribute-based storage.

        Args:
            obj (Object): Parent Object typeclass for this TraitHandler
            db_attribute_key (str): Name of the DB attribute for trait data storage

        """
        # load the available classes, if necessary
        _delayed_import_trait_classes()

        # Note that .trait_data retains the connection to the database, meaning every
        # update we do to .trait_data automatically syncs with database.
        self.trait_data = obj.attributes.get(db_attribute_key, category=db_attribute_category)
        if self.trait_data is None:
            # no existing storage; initialize it, we then have to fetch it again
            # to retain the db connection
            obj.attributes.add(db_attribute_key, {}, category=db_attribute_category)
            self.trait_data = obj.attributes.get(db_attribute_key, category=db_attribute_category)
        self._cache = {}

    def __len__(self):
        """Return number of Traits registered with the handler"""
        return len(self.trait_data)

    def __setattr__(self, trait_key, value):
        """
        Returns error message if trait objects are assigned directly.

        Args:
            trait_key (str): The Trait-key, like "hp".
            value (any): Data to store.
        """
        if trait_key in ("trait_data", "_cache"):
            _SA(self, trait_key, value)
        else:
            trait_cls = self._get_trait_class(trait_key=trait_key)
            valid_keys = list_to_string(list(trait_cls.default_keys.keys()), endsep="or")
            raise TraitException(
                "Trait object not settable directly. " f"Assign to {trait_key}.{valid_keys}."
            )

    def __setitem__(self, trait_key, value):
        """Returns error message if trait objects are assigned directly."""
        return self.__setattr__(trait_key, value)

    def __getattr__(self, trait_key):
        """Returns Trait instances accessed as attributes."""
        return self.get(trait_key)

    def __getitem__(self, trait_key):
        """Returns `Trait` instances accessed as dict keys."""
        return self.get(trait_key)

    def __repr__(self):
        return "TraitHandler ({num} Trait(s) stored): {keys}".format(
            num=len(self), keys=", ".join(self.all)
        )

    def _get_trait_class(self, trait_type=None, trait_key=None):
        """
        Helper to retrieve Trait class based on type (like "static")
        or trait-key (like "hp").

        """
        if not trait_type and trait_key:
            try:
                trait_type = self.trait_data[trait_key]["trait_type"]
            except KeyError:
                raise TraitException(f"Trait class for Trait {trait_key} could not be found.")
        try:
            return _TRAIT_CLASSES[trait_type]
        except KeyError:
            raise TraitException(f"Trait class for {trait_type} could not be found.")

    @property
    def all(self):
        """
        Get all trait keys in this handler.

        Returns:
            list: All Trait keys.

        """
        return list(self.trait_data.keys())

    def get(self, trait_key):
        """
        Args:
            trait_key (str): key from the traits dict containing config data.

        Returns:
            (`Trait` or `None`): named Trait class or None if trait key
            is not found in traits collection.

        """
        trait = self._cache.get(trait_key)
        if trait is None and trait_key in self.trait_data:
            trait_type = self.trait_data[trait_key]["trait_type"]
            trait_cls = self._get_trait_class(trait_type)
            trait = self._cache[trait_key] = trait_cls(_GA(self, "trait_data")[trait_key])
        return trait

    def add(
        self, trait_key, name=None, trait_type=DEFAULT_TRAIT_TYPE, force=True, **trait_properties
    ):
        """
        Create a new Trait and add it to the handler.

        Args:
            trait_key (str): This is the name of the property that will be made
                available on this handler (example 'hp').
            name (str, optional): Name of the Trait, like "Health". If
                not given, will use `trait_key` starting with a capital letter.
            trait_type (str, optional): One of 'static', 'counter' or 'gauge'.
            force_add (bool): If set, create a new Trait even if a Trait with
                the same `trait_key` already exists.
            trait_properties (dict): These will all be use to initialize
                the new trait. See the `properties` class variable on each
                Trait class to see which are required.

        Raises:
            TraitException: If specifying invalid values for the given Trait,
                the `trait_type` is not recognized, or an existing trait
                already exists (and `force` is unset).

        """
        # from evennia import set_trace;set_trace()

        if trait_key in self.trait_data:
            if force:
                self.remove(trait_key)
            else:
                raise TraitException(f"Trait '{trait_key}' already exists.")

        trait_class = _TRAIT_CLASSES.get(trait_type)
        if not trait_class:
            raise TraitException(f"Trait-type '{trait_type}' is invalid.")

        trait_properties["name"] = trait_key.title() if not name else name
        trait_properties["trait_type"] = trait_type

        # this will raise exception if input is insufficient
        trait_properties = trait_class.validate_input(trait_class, trait_properties)

        self.trait_data[trait_key] = trait_properties

    def remove(self, trait_key):
        """
        Remove a Trait from the handler's parent object.

        Args:
            trait_key (str): The name of the trait to remove.

        """
        if trait_key not in self.trait_data:
            raise TraitException(f"Trait '{trait_key}' not found.")

        if trait_key in self._cache:
            del self._cache[trait_key]
        del self.trait_data[trait_key]

    def clear(self):
        """
        Remove all Traits from the handler's parent object.
        """
        for trait_key in self.all:
            self.remove(trait_key)


# Parent Trait class


@total_ordering
class Trait:
    """Represents an object or Character trait. This simple base is just
    storing anything in it's 'value' property, so it's pretty much just a
    different wrapper to an Attribute. It does no type-checking of what is
    stored.

    Note:
        See module docstring for configuration details.

    value

    """

    # this is the name used to refer to this trait when adding
    # a new trait in the TraitHandler
    trait_type = "trait"

    # Property kwargs settable when creating a Trait of this type. This is a
    # dict of key: default. To indicate a mandatory kwarg and raise an error if
    # not given, set the default value to the `traits.MandatoryTraitKey` class.
    # Apart from the keys given here, "name" and "trait_type" will also always
    # have to be a apart of the data.
    default_keys = {"value": None}

    # enable to set/retrieve other arbitrary properties on the Trait
    # and have them treated like data to store.
    allow_extra_properties = True

    def __init__(self, trait_data):
        """
        This both initializes and validates the Trait on creation. It must
        raise exception if validation fails. The TraitHandler will call this
        when the trait is furst added, to make sure it validates before
        storing.

        Args:
            trait_data (any): Any pickle-able values to store with this trait.
                This must contain any cls.default_keys that do not have a default
                value in cls.data_default_values. Any extra kwargs will be made
                available as extra properties on the Trait, assuming the class
                variable `allow_extra_properties` is set.

        Raises:
            TraitException: If input-validation failed.

        """
        self._data = self.__class__.validate_input(self.__class__, trait_data)

        if not isinstance(trait_data, _SaverDict):
            logger.log_warn(
                f"Non-persistent Trait data (type(trait_data)) "
                f"loaded for {type(self).__name__}."
            )

    @staticmethod
    def validate_input(cls, trait_data):
        """
        Validate input

        Args:
            trait_data (dict or _SaverDict): Data to be used for
                initialization of this trait.
        Returns:
            dict: Validated data, possibly complemented with default
                values from default_keys.
        Raises:
            TraitException: If finding unset keys without a default.

        """

        def _raise_err(unset_required):
            """Helper method to format exception."""
            raise TraitException(
                "Trait {} could not be created - misses required keys {}.".format(
                    cls.trait_type, list_to_string(list(unset_required), addquote=True)
                )
            )

        inp = set(trait_data.keys())

        # separate check for name/trait_type, those are always required.
        req = set(("name", "trait_type"))
        unsets = req.difference(inp.intersection(req))
        if unsets:
            _raise_err(unsets)

        # check other keys, these likely have defaults to fall back to
        req = set(list(cls.default_keys.keys()))
        unsets = req.difference(inp.intersection(req))
        unset_defaults = {key: cls.default_keys[key] for key in unsets}

        if MandatoryTraitKey in unset_defaults.values():
            # we have one or more unset keys that was mandatory
            _raise_err([key for key, value in unset_defaults.items() if value == MandatoryTraitKey])
        # apply the default values
        trait_data.update(unset_defaults)

        if not cls.allow_extra_properties:
            # don't allow any extra properties - remove the extra data
            for key in (key for key in inp.difference(req) if key not in ("name", "trait_type")):
                del trait_data[key]

        return trait_data

    # Grant access to properties on this Trait.

    def __getitem__(self, key):
        """Access extra parameters as dict keys."""
        try:
            return self.__getattr__(key)
        except AttributeError:
            raise KeyError(key)

    def __setitem__(self, key, value):
        """Set extra parameters as dict keys."""
        self.__setattr__(key, value)

    def __delitem__(self, key):
        """Delete extra parameters as dict keys."""
        self.__delattr__(key)

    def __getattr__(self, key):
        """Access extra parameters as attributes."""
        if key in ("default_keys", "data_default", "trait_type", "allow_extra_properties"):
            return _GA(self, key)
        try:
            return self._data[key]
        except KeyError:
            raise AttributeError(
                "{!r} {} ({}) has no property {!r}.".format(
                    self._data["name"], type(self).__name__, self.trait_type, key
                )
            )

    def __setattr__(self, key, value):
        """Set extra parameters as attributes.

        Arbitrary attributes set on a Trait object will be
        stored in the 'extra' key of the `_data` attribute.

        This behavior is enabled by setting the instance
        variable `_locked` to True.

        """
        propobj = getattr(self.__class__, key, None)
        if isinstance(propobj, property):
            # we have a custom property named as this key, find and use its setter
            if propobj.fset:
                propobj.fset(self, value)
            return
        else:
            # this is some other value
            if key in ("_data",):
                _SA(self, key, value)
                return
            if _GA(self, "allow_extra_properties"):
                _GA(self, "_data")[key] = value
                return
        raise AttributeError(f"Can't set attribute {key} on " f"{self.trait_type} Trait.")

    def __delattr__(self, key):
        """
        Delete or reset parameters.

        Args:
            key (str): property-key to delete.
        Raises:
            TraitException: If trying to delete a data-key
                without a default value to reset to.
        Notes:
            This will outright delete extra keys (if allow_extra_properties is
            set). Keys in self.default_keys with a default value will be
            reset to default. A data_key with a default of MandatoryDefaultKey
            will raise a TraitException. Unfound matches will be silently ignored.

        """
        if key in self.default_keys:
            if self.default_keys[key] == MandatoryTraitKey:
                raise TraitException(
                    "Trait-Key {key} cannot be deleted: It's a mandatory property "
                    "with no default value to fall back to."
                )
            # set to default
            self._data[key] = self.default_keys[key]
        elif key in self._data:
            try:
                # check if we have a custom deleter
                _DA(self, key)
            except AttributeError:
                # delete normally
                del self._data[key]
        else:
            try:
                # check if we have custom deleter, otherwise ignore
                _DA(self, key)
            except AttributeError:
                pass

    def __repr__(self):
        """Debug-friendly representation of this Trait."""
        return "{}({{{}}})".format(
            type(self).__name__,
            ", ".join(
                [
                    "'{}': {!r}".format(k, self._data[k])
                    for k in self.default_keys
                    if k in self._data
                ]
            ),
        )

    def __str__(self):
        return f"<Trait {self.name}: {self._data['value']}>"

    # access properties

    @property
    def name(self):
        """Display name for the trait."""
        return self._data["name"]

    key = name

    # Numeric operations

    def __eq__(self, other):
        """Support equality comparison between Traits or Trait and numeric.

        Note:
            This class uses the @functools.total_ordering() decorator to
            complete the rich comparison implementation, therefore only
            `__eq__` and `__lt__` are implemented.
        """
        if inherits_from(other, Trait):
            return self.value == other.value
        elif type(other) in (float, int):
            return self.value == other
        else:
            return NotImplemented

    def __lt__(self, other):
        """Support less than comparison between `Trait`s or `Trait` and numeric."""
        if inherits_from(other, Trait):
            return self.value < other.value
        elif type(other) in (float, int):
            return self.value < other
        else:
            return NotImplemented

    def __pos__(self):
        """Access `value` property through unary `+` operator."""
        return self.value

    def __add__(self, other):
        """Support addition between `Trait`s or `Trait` and numeric"""
        if inherits_from(other, Trait):
            return self.value + other.value
        elif type(other) in (float, int):
            return self.value + other
        else:
            return NotImplemented

    def __sub__(self, other):
        """Support subtraction between `Trait`s or `Trait` and numeric"""
        if inherits_from(other, Trait):
            return self.value - other.value
        elif type(other) in (float, int):
            return self.value - other
        else:
            return NotImplemented

    def __mul__(self, other):
        """Support multiplication between `Trait`s or `Trait` and numeric"""
        if inherits_from(other, Trait):
            return self.value * other.value
        elif type(other) in (float, int):
            return self.value * other
        else:
            return NotImplemented

    def __floordiv__(self, other):
        """Support floor division between `Trait`s or `Trait` and numeric"""
        if inherits_from(other, Trait):
            return self.value // other.value
        elif type(other) in (float, int):
            return self.value // other
        else:
            return NotImplemented

    # commutative property
    __radd__ = __add__
    __rmul__ = __mul__

    def __rsub__(self, other):
        """Support subtraction between `Trait`s or `Trait` and numeric"""
        if inherits_from(other, Trait):
            return other.value - self.value
        elif type(other) in (float, int):
            return other - self.value
        else:
            return NotImplemented

    def __rfloordiv__(self, other):
        """Support floor division between `Trait`s or `Trait` and numeric"""
        if inherits_from(other, Trait):
            return other.value // self.value
        elif type(other) in (float, int):
            return other // self.value
        else:
            return NotImplemented

    # Public members

    @property
    def value(self):
        """Store a value"""
        return self._data["value"]

    @value.setter
    def value(self, value):
        """Get value"""
        self._data["value"] = value


# Implementation of the respective Trait types


class StaticTrait(Trait):
    """
    Static Trait. This is a single value with a modifier,
    with no concept of a 'current' value.

    value = base + mod

    """

    trait_type = "static"

    default_keys = {"base": 0, "mod": 0}

    def __str__(self):
        status = "{value:11}".format(value=self.value)
        return "{name:12} {status} ({mod:+3})".format(name=self.name, status=status, mod=self.mod)

    # Helpers

    @property
    def mod(self):
        """The trait's modifier."""
        return self._data["mod"]

    @mod.setter
    def mod(self, amount):
        if type(amount) in (int, float):
            self._data["mod"] = amount

    @property
    def value(self):
        "The value of the Trait"
        return self.base + self.mod


class CounterTrait(Trait):
    """
    Counter Trait.

    This includes modifications and min/max limits as well as the notion of a
    current value. The value can also be reset to the base value.

    min/unset     base    base+mod                       max/unset
     |--------------|--------|---------X--------X------------|
                                    current   value
                                              = current
                                              + mod

    - value = current + mod, starts at base + mod
    - if min or max is None, there is no upper/lower bound (default)
    - if max is set to "base", max will be equal ot base+mod
    - descs are used to optionally describe each value interval.
      The desc of the current `value` value can then be retrieved
      with .desc(). The property is set as {lower_bound_inclusive:desc}
      and should be given smallest-to-biggest. For example, for
      a skill rating between 0 and 10:
            {0: "unskilled",
             1: "neophyte",
             5: "traited",
             7: "expert",
             9: "master"}
    - rate/ratetarget are optional settings to include a rate-of-change
      of the current value. This is calculated on-demand and allows for
      describing a value that is gradually growing smaller/bigger. The
      increase will stop when either reaching a boundary (if set) or
      ratetarget. Setting the rate to 0 (default) stops any change.

    """

    trait_type = "counter"

    # current starts equal to base.
    default_keys = {
        "base": 0,
        "mod": 0,
        "min": None,
        "max": None,
        "descs": None,
        "rate": 0,
        "ratetarget": None,
    }

    @staticmethod
    def validate_input(cls, trait_data):
        """Add extra validation for descs"""
        trait_data = Trait.validate_input(cls, trait_data)
        # validate descs
        descs = trait_data["descs"]
        if isinstance(descs, dict):
            if any(
                not (isinstance(key, (int, float)) and isinstance(value, str))
                for key, value in descs.items()
            ):
                raise TraitException(
                    f"Trait descs must be defined on the "
                    f"form {{number:str}} (instead found {descs})."
                )
        # set up rate
        if trait_data["rate"] != 0:
            trait_data["last_update"] = time()
        else:
            trait_data["last_update"] = None
        return trait_data

    # Helpers

    def _within_boundaries(self, value):
        """Check if given value is within boundaries"""
        return not (
            (self.min is not None and value <= self.min)
            or (self.max is not None and value >= self.max)
        )

    def _enforce_boundaries(self, value):
        """Ensures that incoming value falls within boundaries"""
        if self.min is not None and value <= self.min:
            return self.min
        if self.max is not None and value >= self.max:
            return self.max
        return value

    # timer component

    def _passed_ratetarget(self, value):
        """Check if we passed the ratetarget in either direction."""
        ratetarget = self._data["ratetarget"]
        return ratetarget is not None and (
            (self.rate < 0 and value <= ratetarget) or (self.rate > 0 and value >= ratetarget)
        )

    def _stop_timer(self):
        """Stop rate-timer component."""
        if self.rate != 0 and self._data["last_update"] is not None:
            self._data["last_update"] = None

    def _check_and_start_timer(self, value):
        """Start timer if we are not at a boundary."""
        if self.rate != 0 and self._data["last_update"] is None:
            ratetarget = self._data["ratetarget"]
            if self._within_boundaries(value) and not self._passed_ratetarget(value):
                # we are not at a boundary [anymore].
                self._data["last_update"] = time()
        return value

    def _update_current(self, current):
        """Update current value by scaling with rate and time passed."""
        rate = self.rate
        if rate != 0 and self._data["last_update"] is not None:
            now = time()
            tdiff = now - self._data["last_update"]
            current += rate * tdiff
            value = current + self.mod

            # we must make sure so we don't overstep our bounds
            # even if .mod is included

            if self._passed_ratetarget(value):
                current = self._data["ratetarget"] - self.mod
                self._stop_timer()
            elif not self._within_boundaries(value):
                current = self._enforce_boundaries(value) - self.mod
                self._stop_timer()
            else:
                self._data["last_update"] = now

            self._data["current"] = current

        return current

    # properties

    @property
    def base(self):
        return self._data["base"]

    @base.setter
    def base(self, value):
        if value is None:
            self._data["base"] = self.default_keys["base"]
        if type(value) in (int, float):
            if self.min is not None and value + self.mod < self.min:
                value = self.min - self.mod
            if self.max is not None and value + self.mod > self.max:
                value = self.max - self.mod
            self._data["base"] = value

    @property
    def mod(self):
        return self._data["mod"]

    @mod.setter
    def mod(self, value):
        if value is None:
            # unsetting the boundary to default
            self._data["mod"] = self.default_keys["mod"]
        elif type(value) in (int, float):
            if self.min is not None and value + self.base < self.min:
                value = self.min - self.base
            if self.max is not None and value + self.base > self.max:
                value = self.max - self.base
            self._data["mod"] = value

    @property
    def min(self):
        return self._data["min"]

    @min.setter
    def min(self, value):
        if value is None:
            # unsetting the boundary
            self._data["min"] = value
        elif type(value) in (int, float):
            if self.max is not None:
                value = min(self.max, value)
            self._data["min"] = min(value, self.base + self.mod)

    @property
    def max(self):
        return self._data["max"]

    @max.setter
    def max(self, value):
        if value is None:
            # unsetting the boundary
            self._data["max"] = value
        elif type(value) in (int, float):
            if self.min is not None:
                value = max(self.min, value)
            self._data["max"] = max(value, self.base + self.mod)

    @property
    def current(self):
        """The `current` value of the `Trait`. This does not have .mod added."""
        return self._update_current(self._data.get("current", self.base))

    @current.setter
    def current(self, value):
        if type(value) in (int, float):
            self._data["current"] = self._check_and_start_timer(self._enforce_boundaries(value))

    @current.deleter
    def current(self):
        """reset back to base"""
        self._data["current"] = self.base

    @property
    def value(self):
        "The value of the Trait (current + mod)"
        return self._enforce_boundaries(self.current + self.mod)

    @property
    def ratetarget(self):
        return self._data["ratetarget"]

    @ratetarget.setter
    def ratetarget(self, value):
        self._data["ratetarget"] = self._enforce_boundaries(value)
        self._check_and_start_timer(self.value)

    def percent(self, formatting="{:3.1f}%"):
        """
        Return the current value as a percentage.

        Args:
            formatting (str, optional): Should contain a
               format-tag which will receive the value. If
               this is set to None, the raw float will be
               returned.
        Returns:
            float or str: Depending of if a `formatting` string
                is supplied or not.
        """
        return percent(self.value, self.min, self.max, formatting=formatting)

    def reset(self):
        """Resets `current` property equal to `base` value."""
        del self.current

    def desc(self):
        """
        Retrieve descriptions of the current value, if available.

        This must be a mapping {upper_bound_inclusive: text},
        ordered from small to big. Any value above the highest
        upper bound will be included as being in the highest bound.
        rely on Python3.7+ dicts retaining ordering to let this
        describe the interval.

        Returns:
            str: The description describing the `value` value.
                If not found, returns the empty string.
        """
        descs = self._data["descs"]
        if descs is None:
            return ""
        value = self.value
        # we rely on Python3.7+ dicts retaining ordering
        highest = ""
        for bound, txt in descs.items():
            highest = txt
            if value <= bound:
                return txt
        # if we get here we are above the highest bound so
        # we return the latest bound specified.
        return highest


class GaugeTrait(CounterTrait):
    """
    Gauge Trait.

    This emulates a gauge-meter that empties from a base+mod value.

    min/0                                            max=base+mod
     |-----------------------X---------------------------|
                           value
                          = current

    - min defaults to 0
    - max value is always base + mad
    - .max is an alias of .base
    - value = current and varies from min to max.
    - descs is a mapping {upper_bound_inclusive: desc}. These
        are checked with .desc() and can be retrieve a text
        description for a given current value.

        For example, this could be used to describe health
        values between 0 and 100:
            {0: "Dead"
             10: "Badly hurt",
             30: "Bleeding",
             50: "Hurting",
             90: "Healthy"}

    """

    trait_type = "gauge"

    # same as Counter, here for easy reference
    # current starts out equal to base
    default_keys = {
        "base": 0,
        "mod": 0,
        "min": 0,
        "descs": None,
        "rate": 0,
        "ratetarget": None,
    }

    def _update_current(self, current):
        """Update current value by scaling with rate and time passed."""
        rate = self.rate
        if rate != 0 and self._data["last_update"] is not None:
            now = time()
            tdiff = now - self._data["last_update"]
            current += rate * tdiff
            value = current

            # we don't worry about .mod for gauges

            if self._passed_ratetarget(value):
                current = self._data["ratetarget"]
                self._stop_timer()
            elif not self._within_boundaries(value):
                current = self._enforce_boundaries(value)
                self._stop_timer()
            else:
                self._data["last_update"] = now

            self._data["current"] = current

        return current

    def _enforce_boundaries(self, value):
        """Ensures that incoming value falls within trait's range."""
        if self.min is not None and value <= self.min:
            return self.min
        return min(self.mod + self.base, value)

    def __str__(self):
        status = "{value:4} / {base:4}".format(value=self.value, base=self.base)
        return "{name:12} {status} ({mod:+3})".format(name=self.name, status=status, mod=self.mod)

    @property
    def base(self):
        return self._data["base"]

    @base.setter
    def base(self, value):
        """Limit so base+mod can never go below min."""
        if type(value) in (int, float):
            if value + self.mod < self.min:
                value = self.min - self.mod
            self._data["base"] = value

    @property
    def mod(self):
        return self._data["mod"]

    @mod.setter
    def mod(self, value):
        """Limit so base+mod can never go below min."""
        if type(value) in (int, float):
            if value + self.base < self.min:
                value = self.min - self.base
            self._data["mod"] = value

    @property
    def min(self):
        val = self._data["min"]
        return self.default_keys["min"] if val is None else val

    @min.setter
    def min(self, value):
        """Limit so min can never be greater than base+mod."""
        if value is None:
            self._data["min"] = self.default_keys["min"]
        elif type(value) in (int, float):
            self._data["min"] = min(value, self.base + self.mod)

    @property
    def max(self):
        "The max is always base + mod."
        return self.base + self.mod

    @max.setter
    def max(self, value):
        raise TraitException(
            "The .max property is not settable " "on GaugeTraits. Set .base instead."
        )

    @max.deleter
    def max(self):
        raise TraitException(
            "The .max property cannot be reset " "on GaugeTraits. Reset .mod and .base instead."
        )

    @property
    def current(self):
        """The `current` value of the gauge."""
        return self._update_current(
            self._enforce_boundaries(self._data.get("current", self.base + self.mod))
        )

    @current.setter
    def current(self, value):
        if type(value) in (int, float):
            self._data["current"] = self._check_and_start_timer(self._enforce_boundaries(value))

    @current.deleter
    def current(self):
        "Resets current back to 'full'"
        self._data["current"] = self.base + self.mod

    @property
    def value(self):
        "The value of the trait"
        return self.current

    def percent(self, formatting="{:3.1f}%"):
        """
        Return the current value as a percentage.

        Args:
            formatting (str, optional): Should contain a
               format-tag which will receive the value. If
               this is set to None, the raw float will be
               returned.
        Returns:
            float or str: Depending of if a `formatting` string
                is supplied or not.
        """
        return percent(self.current, self.min, self.max, formatting=formatting)

    def reset(self):
        """
        Fills the gauge to its maximum allowed by base + mod
        """
        del self.current