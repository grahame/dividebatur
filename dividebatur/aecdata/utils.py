from collections import namedtuple


def int_or_none(s):
    if s == '':
        return None
    try:
        return int(s)
    except ValueError:
        return None


def named_tuple_iter(name, reader, header, **kwargs):
    field_names = [t for t in [t.strip().replace('-', '_')
                               for t in header] if t]
    typ = namedtuple(name, field_names)
    mappings = []
    for field_name in kwargs:
        idx = field_names.index(field_name)
        mappings.append((idx, kwargs[field_name]))
    for row in reader:
        for idx, map_fn in mappings:
            row[idx] = map_fn(row[idx])
        yield typ(*row)


def ticket_sort_key(ticket):
    "sort key for an ATL ticket, eg. A..Z, AA..ZZ"
    return (len(ticket), ticket)
