import collections
from ast import literal_eval as make_tuple
from django.core.exceptions import ValidationError

# if we use PostGIS
        
def parse_tuple(box_tuple):
    if len(box_tuple) != 2:
        raise ValidationError("Box has exactly two points (NE, SW)")
    if not all(isinstance(i, tuple) for i in box_tuple):
        raise ValidationError("Box must be a tuple of tuples")
    return box_tuple


def parse_box(box_string):
    box_string = '({0})'.format(box_string)
    try:
        val = make_tuple(box_string)
    except (ValueError, SyntaxError):
        raise ValidationError("Invalid input: '{0}'".format(box_string))
    if not isinstance(val, collections.Iterable):
        raise ValidationError("Box must be a tuple")
    return parse_tuple(val)


class BoxField(models.Field):
    """
    To create an index on this field:
    CREATE INDEX frames_frame_area ON frames_frame USING gist(area box_ops);
    """
    description = "A postgresql box type"

    def db_type(self, connection):
        return 'box'

    def from_db_value(self, value, expression, connection, context):
        if value is None:
            return value
        return parse_box(value)

    def to_python(self, value):
        if isinstance(value, tuple):
            parse_tuple(value)
        if value is None:
            return value
        return parse_box(value)

    def get_prep_value(self, value):
        # remove paratheses from string representation
        # for postgres insertion
        return str(parse_tuple(value))[1:][:-1]

    def get_prep_lookup(self, lookup_type, value):
        if lookup_type == 'contains':
            # Value will be a point
            return str(value)
        else:
            raise TypeError('Lookup type %r not supported.' % lookup_type)


@BoxField.register_lookup
class BoxContains(models.Lookup):
    lookup_name = 'contains'

    def as_sql(self, compiler, connection):
        lhs, lhs_params = self.process_lhs(compiler, connection)
        rhs, rhs_params = self.process_rhs(compiler, connection)
        params = lhs_params + rhs_params
        return "%s @> %s::point" % (lhs, rhs), params
