from django.core.management.commands import dumpdata


class Command(dumpdata.Command):
    def execute(self, *args, **options):
        path = options.get('output')
        if path:
            options['output'] = None
            with open(path, mode='w', encoding='utf-8') as file:
                self.stdout = file
                result = super(Command, self).execute(*args, **options)
        else:
            result = super(Command, self).execute(*args, **options)
        return result
