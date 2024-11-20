from cult.property_system import SourceProperty, \
                                 DependantProperty, \
                                 PropertyDepot

def test_update():
    pd = PropertyDepot()
    x = SourceProperty[int](pd, 10)
    y = DependantProperty(pd, lambda x: 2*x, x)
    pd.update_properties()
    assert y.value == 20

    x.value = 20
    assert y.value == 20
    pd.update_properties()
    assert y.value == 40

def test_chain_dependency():
    pd = PropertyDepot()
    x = SourceProperty[int](pd, 10)
    y = DependantProperty(pd, lambda x: 2*x, x)
    z = DependantProperty(pd, lambda y: 3*y, y)

    pd.update_properties()
    assert z.value == 60

    x.value = 6
    pd.update_properties()
    assert z.value == 36

def test_many_sources():
    pd = PropertyDepot()
    x = SourceProperty[int](pd, 10)
    y = SourceProperty[int](pd, 20)
    z = SourceProperty[int](pd, 30)
    s = DependantProperty(pd, lambda x, y, z: x + y + z, 
                                     x, y, z)

    pd.update_properties()
    assert s.value == 60

def test_separated_dependencies():
    pd = PropertyDepot()
    x1 = SourceProperty[int](pd, 10)
    x2 = SourceProperty[int](pd, 20)
    y1 = DependantProperty(pd, lambda x: x, x1)
    y2 = DependantProperty(pd, lambda x: x*2, x2)

    pd.update_properties()
    assert y1.value == 10
    assert y2.value == 40

def test_double_dependency_on_source():
    pd = PropertyDepot()
    x = SourceProperty[int](pd, 10)
    y = DependantProperty(pd, lambda x: x*2, x)
    z = DependantProperty(pd, lambda x, y: x + 3*y,
                                     x, y)

    pd.update_properties()
    assert z.value == 70

def test_double_dependency_on_dependant():
    pd = PropertyDepot()
    a = SourceProperty[int](pd, 10)
    b = DependantProperty(pd, lambda a: 2*a, a)
    c = DependantProperty(pd, lambda b: 3*b, b)
    d = DependantProperty(pd, lambda b, c: b + 4*c,
                                     b, c)

    pd.update_properties()
    assert d.value == 260

def test_callback():
    pd = PropertyDepot()
    name = SourceProperty[str](pd, 'Bob')

    result = ''
    def greeting(name: str):
        nonlocal result
        result = f'Hello, {name}!'
    name.subscribe(greeting)

    pd.update_properties(force_notify=True)
    assert result == 'Hello, Bob!'