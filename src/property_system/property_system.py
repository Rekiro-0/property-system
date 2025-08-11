from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from collections import deque, namedtuple
from collections.abc import Callable, Iterable
from typing import Any

Update = namedtuple("Update", ["source_property", "value"])


class PropertyDepot:
    def __init__(self) -> None:
        self._properties: dict[str, BaseProperty] = {}
        self._source_props: dict[str, SourceProperty] = {}
        self._dependant_props: dict[str, DependantProperty] = {}
        self._updates: dict[SourceProperty, Any] = {}
        self._update_tick: int = 0

    def add_dependant_prop(self, property_: DependantProperty) -> None:
        self._dependant_props[property_.name] = property_
        self._properties[property_.name] = property_

    def add_source_prop(self, property_: SourceProperty) -> None:
        self._source_props[property_.name] = property_
        self._properties[property_.name] = property_

    def add_update(self, source_prop: SourceProperty, value: Any) -> None:
        self._updates[source_prop] = value

    def _get_signature_params(self, parameters: Iterable[str]) -> list[BaseProperty]:
        return [self._properties[name] for name in parameters]

    def update_properties(self, force_notify: bool = False) -> None:
        self._update_tick += 1
        for source_property in self._updates:
            source_property._update(self._update_tick)
        self._updates = {}

        if force_notify:
            for source_prop in self._source_props.values():
                if source_prop._updated != self._update_tick:
                    source_prop._updated = self._update_tick
                    source_prop._notify_subscribers()

        self._update_dependant_properties()

    def _update_dependant_properties(self) -> None:
        dependency_stack = deque[DependantProperty]()
        for dependant_prop in self._dependant_props.values():
            if dependant_prop._update_tick != self._update_tick:
                dependency_stack.append(dependant_prop)

            while len(dependency_stack):
                current_dependant_prop = dependency_stack[-1]
                can_update = True
                for dependency in current_dependant_prop._dependencies:
                    if (
                        isinstance(dependency, DependantProperty)
                        and dependency._update_tick != self._update_tick
                    ):
                        dependency_stack.append(dependency)
                        can_update = False
                if can_update:
                    dependency_stack.pop()
                    current_dependant_prop._update(self._update_tick)  # also notifies

    def get_updates(self) -> Iterable[SourceProperty]:
        return self._updates.keys()


class BaseProperty[T](ABC):
    def __init__(self, name: str, data: Any = None) -> None:
        self._on_update_callbacks: list[Callable[[T], None]] = []
        self._value: T
        self._updated = 0
        self.name = name
        self.data = data

    @property
    @abstractmethod
    def value(self) -> T:
        raise NotImplementedError

    def subscribe(self, on_update: Callable[[T], None]) -> None:
        self._on_update_callbacks.append(on_update)

    @abstractmethod
    def _update(self, update_tick: int) -> None:
        raise NotImplementedError

    def _notify_subscribers(self) -> None:
        if self._value is None:
            raise NoneValueException
        for callback in self._on_update_callbacks:
            callback(self._value)


class SourceProperty[T](BaseProperty[T]):
    def __init__(
        self, pd: PropertyDepot, name: str, value: T, data: Any = None
    ) -> None:
        super().__init__(name, data)
        self._pd = pd
        self._pd.add_source_prop(self)
        self._value: T = value
        self._new_value: T = value

    @property
    def value(self) -> T:
        return self._value

    # Change behavior to track several changes. What to do with negative values?
    @value.setter
    def value(self, value: T) -> None:
        if self._value == value:
            return
        self._pd.add_update(self, value)
        self._new_value = value
        self._updated = False
        # notify subscribers

    def _update(self, update_tick: int) -> None:
        self._value = self._new_value
        self._updated = update_tick
        self._notify_subscribers()


class DependantProperty[T](BaseProperty[T]):
    def __init__(
        self,
        pd: PropertyDepot,
        name: str,
        func_dependency: Callable,
        dependancy_names: list[str] | None = None,
    ) -> None:
        super().__init__(name)
        self._pd = pd
        self._pd.add_dependant_prop(self)
        self._update_tick = 0

        self._func_dependency = func_dependency
        if dependancy_names is not None:
            self._dependencies = pd._get_signature_params(dependancy_names)
        else:
            self._dependencies = pd._get_signature_params(
                inspect.signature(func_dependency).parameters
            )

        # check args are properties (add when base class is ready)

    @property
    def value(self) -> T:
        # return self._func_dependency( *[pr.value for pr in self._properties] )
        return self._value

    @property
    def updated(self) -> bool:
        return bool(self._updated)

    def _update(self, update_tick: int) -> None:
        self._value = self._func_dependency(*[pr.value for pr in self._dependencies])
        self._update_tick = update_tick
        self._notify_subscribers()


class NoneValueException(Exception):
    pass
