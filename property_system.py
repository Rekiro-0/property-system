"""
Manage many of dependant propeties with ease.

1. Properties are updated only with update() func.
    to do:
    - update list
    - update algorithm
    - keep result in var for persistance


 TO DO:
   - auto dispatch properties to thiers dependants
"""

from collections.abc import Callable
from collections import namedtuple, deque
from abc import ABC
from typing import TypeVar, Generic, List
import queue

Update = namedtuple('Update', ['source_property', 'value'])

class PropertyDepot:
    def __init__(self):
        self._source_props: List['SourceProperty'] = []
        self._dependant_props: List['DependantProperty'] = []
        self._updates = {}
        self._update_tick = 0

    def add_dependant_prop(self, property_: 'DependantProperty'):
        self._dependant_props.append(property_)

    def add_source_prop(self, property_: 'SourceProperty'):
        self._source_props.append(property_)

    def add_update(self, source_prop: 'SourceProperty', value):
        self._updates[source_prop] = value

    def update_properties(self, force_notify: bool = False):
        self._update_tick += 1
        for source_property, value in self._updates.items():
            source_property._value = value #that
            source_property._updated = self._update_tick #that
            source_property._notify_subscribers() #and that should be in a single update call 

        if force_notify:
            for source_prop in self._source_props:
                if source_prop._updated != self._update_tick:
                    source_prop._updated = self._update_tick
                    source_prop._notify_subscribers()


        dependency_stack = deque[DependantProperty]()
        for dependant_prop in self._dependant_props:
             if dependant_prop._update_tick != self._update_tick:
                dependency_stack.append(dependant_prop)

             while len(dependency_stack):
                current_dependant_prop = dependency_stack[-1]
                can_update = True
                for dependency in current_dependant_prop._dependencies:
                    if dependency is DependantProperty and dependency._update_tick != self._update_tick:
                        dependency_stack.append(dependency)
                        can_update = False
                if can_update:
                    dependency_stack.pop()
                    current_dependant_prop._update(self._update_tick) #also notifies

T = TypeVar("T")
class BaseProperty(ABC):
     def __init__(self):
        self._on_update_callbacks = []
        self._value = None
        self._updated = 0

     def subscribe(self, on_update: Callable[[T], None]):
        self._on_update_callbacks.append(on_update)

     def _notify_subscribers(self):
        for callback in self._on_update_callbacks:
            callback(self._value)


class SourceProperty(BaseProperty,  Generic[T]):
    def __init__(self, pd: PropertyDepot, value: T):
        super().__init__()
        self._pd = pd
        self._pd.add_source_prop(self)
        self._value = value

    @property
    def value(self) -> T:
        return self._value

    @value.setter
    def value(self, value: T):
        if self._value == value:
            return
        self._pd.add_update(self, value)
        self._updated = False
        #notify subscribers


class DependantProperty(BaseProperty):
    def __init__(self, pd: PropertyDepot, func_dependency: Callable, *args: List[BaseProperty]):
        super().__init__()
        self._pd = pd
        self._pd.add_dependant_prop(self)

        self._func_dependency = func_dependency
        self._dependencies = args
        self._update_tick = 0
        #check args are properties (add when base class is ready)

        #add links

    @property
    def value(self) -> T:
        #return self._func_dependency( *[pr.value for pr in self._properties] )
        return self._value

    @property
    def updated(self) -> bool:
        return self._updated

    def _update(self, update_tick: int):
        self._value = self._func_dependency( *[pr.value for pr in self._dependencies] )
        self._update_tick = update_tick
        self._notify_subscribers()
