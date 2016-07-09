from django.db import models

class EnumField(models.Field):
    __metaclass__ = models.SubfieldBase

    def __init__(self, enum, *args, **kwargs):
        self.enum = enum

        kwargs.setdefault('choices', enum.get_choices())

        super(EnumField, self).__init__(*args, **kwargs)

    def get_internal_type(self):
        return 'IntegerField'

    def to_python(self, value):
        return self.enum.to_python(value)

    def get_db_prep_save(self, value, connection=None):
        if value is None:
            return value

        return self.to_python(value).value

    def get_db_prep_lookup(self, lookup_type, value, connection=None, prepared=False):
        def prepare(value):
            x = self.to_python(value)

            return self.get_db_prep_save(x, connection=connection)

        if lookup_type in ('exact', 'lt', 'lte', 'gt', 'gte'):
            return [prepare(value)]
        elif lookup_type == 'in':
            return [prepare(v) for v in value]
        elif lookup_type == 'isnull':
            return []

        raise TypeError("Lookup type %r not supported." % lookup_type)

    def south_field_triple(self):
        from south.modelsinspector import introspector, NOT_PROVIDED
        args, kwargs = introspector(self)

        # repr(Item) is not only invalid as an lookup value, it actually causes
        # South to generate invalid Python
        if self.default != NOT_PROVIDED:
            kwargs['default'] = None

            # Cannot set a real default if the "default" kwarg is a callable.
            if not callable(self.default):
                kwargs['default'] = self.default and self.default.value

        return ('django.db.models.fields.IntegerField', args, kwargs)

    def value_to_string(self, obj):
        item = self._get_val_from_obj(obj)

        return str(item.value)

    def clone(self):
        _, _, args, kwargs = self.deconstruct()
        return models.IntegerField(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super(EnumField, self).deconstruct()

        # If there is a callable default, override it and set the first item
        # from the enum. This is to stop randomised defaults causing unstable
        # migrations, as deconstruct is called every time makemigrations is run
        default = kwargs.get('default')
        if default and callable(default):
            kwargs['default'] = self.enum[0]

        try:
            kwargs['default'] = kwargs['default'].value
        except (KeyError, AttributeError):
            # No default or not an Item instance
            pass

        # We don't want to serialise this for migrations.
        del kwargs['choices']

        return name, 'django.db.models.fields.IntegerField', args, kwargs
