from .aecdata import ticket_sort_key


def apply_ticket_sort(items):
    return list(sorted(items, key=ticket_sort_key))


def test_a_c_already_sorted():
    assert(apply_ticket_sort(['A', 'B', 'C']) == ['A', 'B', 'C'])


def test_a_c_reversed():
    assert(apply_ticket_sort(['C', 'B', 'A']) == ['A', 'B', 'C'])


def test_a_c_aa_reversed():
    assert(apply_ticket_sort(['AA', 'C', 'B', 'A']) == ['A', 'B', 'C', 'AA'])


def test_a_c_aa_already_sorted():
    assert(apply_ticket_sort(['A', 'B', 'C', 'AA']) == ['A', 'B', 'C', 'AA'])
