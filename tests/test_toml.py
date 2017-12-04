from setupmeta.toml import is_toml_section, normalized_toml, parsed_toml, \
    toml_key_value, toml_value


def test_toml():
    assert toml_key_value(None) == (None, None)
    assert toml_key_value('=') == (None, None)
    assert toml_key_value('a=b') == ('a', 'b')
    assert toml_key_value('"a=b') == (None, '"a=b')
    assert toml_key_value('"a b"=c') == ('a b', 'c')

    assert is_toml_section('[a]')
    assert is_toml_section('[[a]]')

    assert normalized_toml('a=[\n1]'.split()) == ['a=[ 1]']

    assert parsed_toml(dict(a=1)) == dict(a=1)
    assert parsed_toml('a=[\n1]') == dict(a=[1])
    assert parsed_toml('=\n[foo]\na=1') == dict(foo=dict(a=1))

    assert toml_value(None) is None
    assert toml_value("true") is True
    assert toml_value("false") is False
    assert toml_value('{a=1,b=2}') == dict(a=1, b=2)
    assert toml_value("a") == 'a'
