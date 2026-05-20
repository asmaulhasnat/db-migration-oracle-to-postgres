"""
Management command: migrate a single table from Oracle to PostgreSQL.

Usage:
  python manage.py migrate_table \
    --source EMPLOYEES \
    --target employees \
    --map EMPLOYEE_ID:id FIRST_NAME:first_name LAST_NAME:last_name \
    --default created_at:NOW() \
    --batch 500 \
    --truncate
"""
from django.core.management.base import BaseCommand
from migrator.db_utils import execute_migration


class Command(BaseCommand):
    help = 'Migrate a table from Oracle to PostgreSQL'

    def add_arguments(self, parser):
        parser.add_argument('--source', required=True, help='Oracle source table name')
        parser.add_argument('--target', required=True, help='PostgreSQL target table name')
        parser.add_argument('--map', nargs='+', metavar='SRC:TGT',
                            help='Column mappings as SOURCE_COL:TARGET_COL pairs')
        parser.add_argument('--default', nargs='*', metavar='COL:VALUE',
                            help='Default values for unmapped target columns as COL:VALUE pairs')
        parser.add_argument('--batch', type=int, default=1000, help='Batch size (default: 1000)')
        parser.add_argument('--truncate', action='store_true', help='Truncate target table before migration')

    def handle(self, *args, **options):
        mappings = []

        if options['map']:
            for pair in options['map']:
                if ':' not in pair:
                    self.stderr.write(f"Invalid mapping '{pair}', use SOURCE:TARGET format")
                    return
                src, tgt = pair.split(':', 1)
                mappings.append({'source_col': src, 'target_col': tgt, 'default_value': ''})

        if options.get('default'):
            for pair in options['default']:
                if ':' not in pair:
                    self.stderr.write(f"Invalid default '{pair}', use COL:VALUE format")
                    return
                col, val = pair.split(':', 1)
                mappings.append({'source_col': '', 'target_col': col, 'default_value': val})

        if not mappings:
            self.stderr.write('At least one --map or --default is required')
            return

        self.stdout.write(f"\nMigrating {options['source']} → {options['target']}")
        self.stdout.write(f"  Mappings : {len(mappings)}")
        self.stdout.write(f"  Batch    : {options['batch']}")
        self.stdout.write(f"  Truncate : {options['truncate']}\n")

        result = execute_migration({
            'source_table': options['source'],
            'target_table': options['target'],
            'mappings': mappings,
            'batch_size': options['batch'],
            'truncate_target': options['truncate'],
        })

        if result['success']:
            self.stdout.write(self.style.SUCCESS(
                f"\n✓ Done — {result['rows_written']} rows in {result['duration_seconds']}s "
                f"({result['batches']} batches, {result['rows_failed']} failed)"
            ))
            if result.get('mode') == 'simulation':
                self.stdout.write(self.style.WARNING("  ⚠ Ran in simulation mode (no real DB connected)"))
        else:
            self.stderr.write(self.style.ERROR(f"\n✗ Migration failed: {result.get('error')}"))
