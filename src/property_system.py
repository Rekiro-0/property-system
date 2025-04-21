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
from typing import TypeVar, Generic, List, Any
import queue
import inspect

Update = namedtuple('Update', ['source_property', 'value'])

class PropertyDepot:
    def __init__(self):
        # self._source_props: List['SourceProperty'] = []
        # self._dependant_props: List['DependantProperty'] = []
        self._properties = {}
        self._source_props = {}
        self._dependant_props = {}
        self._updates: dict[SourceProperty, Any] = {}
        self._update_tick = 0

    def add_dependant_prop(self, property_: 'DependantProperty'):
        self._dependant_props[property_.name] = property_
        self._properties[property_.name] = property_

    def add_source_prop(self, property_: 'SourceProperty'):
        self._source_props[property_.name] = property_
        self._properties[property_.name] = property_

    def add_update(self, source_prop: 'SourceProperty', value):
        self._updates[source_prop] = value

    def _get_signature_params(self, parameters) -> List['BaseProperty']:
        return [self._properties[name] for name in parameters]

    def update_properties(self, force_notify: bool = False):
        self._update_tick += 1
        for source_property, value in self._updates.items():
            source_property._update(self._update_tick)
        self._updates = {}

        if force_notify:
            for source_prop in self._source_props.values():
                if source_prop._updated != self._update_tick:
                    source_prop._updated = self._update_tick
                    source_prop._notify_subscribers()


        dependency_stack = deque[DependantProperty]()
        for dependant_prop in self._dependant_props.values():
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

    def get_updates(self) -> List['SourceProperty']:
        return self._updates.keys()

T = TypeVar("T")
class BaseProperty(ABC):
     def __init__(self, name, data: Any = None):
        self._on_update_callbacks = []
        self._value = None
        self._updated = 0
        self.name = name
        self.data = data

     def subscribe(self, on_update: Callable[[T], None]):
        self._on_update_callbacks.append(on_update)

     def _notify_subscribers(self):
        for callback in self._on_update_callbacks:
            callback(self._value)


class SourceProperty(BaseProperty,  Generic[T]):
    def __init__(self, pd: PropertyDepot, name: str, value: T, data: Any = None):
        super().__init__(name, data)
        self._pd = pd
        self._pd.add_source_prop(self)
        self._value = value
        self._new_value = None

    @property
    def value(self) -> T:
        return self._value

    #Change behavior to track several changes. What to do with negative values?
    @value.setter
    def value(self, value: T):
        if self._value == value:
            return
        self._pd.add_update(self, value)
        self._new_value = value
        self._updated = False
        #notify subscribers

    def _update(self, update_tick: int):
        self._value = self._new_value
        self._new_value = None
        self._updated = update_tick
        self._notify_subscribers()


class DependantProperty(BaseProperty):
    def __init__(
        self,
        pd: PropertyDepot,
        name: str,
        func_dependency: Callable,
        dependancy_names: List[str] | None = None,
    ):#, *args: List[BaseProperty]):
        super().__init__(name)
        self._pd = pd
        self._pd.add_dependant_prop(self)
        self._update_tick = 0

        self._func_dependency = func_dependency
        if dependancy_names is not None:
            self._dependencies = pd._get_signature_params(dependancy_names)
        else:
            self._dependencies = pd._get_signature_params(inspect.signature(func_dependency).parameters)
        
        #check args are properties (add when base class is ready)

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


def testfunc(a: int, s: str) -> None:
    print(a, type(a))
    print(s, type(s))

# class MyData:
#     def __init__(self):
#         self.a: float = 5.0
#         self.s: str = 'hi'

#     def process_func(self, func):
#         sig = inspect.signature(func)
#         params = sig.parameters
#         data = {}

#         for param in params.values():
#             if hasattr(self, param.name):
#                 if param.annotation != type(getattr(self, param.name)):
#                     raise 'Wrong type'
#                 data[param.name] = getattr(self, param.name)

#             else:
#                 raise 'No such attribute'
#         func(**data)

# mydata = MyData()
# mydata.process_func(testfunc)