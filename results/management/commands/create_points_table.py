# results/management/commands/create_points_table.py

from django.core.management.base import BaseCommand
from django.db import connection

class Command(BaseCommand):
    help = 'Create missing dailypointspool table and fix points system'

    def handle(self, *args, **options):
        self.stdout.write('🔧 Creating missing points system table...')
        
        sql_commands = [
            # Create the missing dailypointspool table
            """
            CREATE TABLE IF NOT EXISTS results_dailypointspool (
                id BIGSERIAL PRIMARY KEY,
                date DATE UNIQUE NOT NULL,
                total_budget INTEGER DEFAULT 10000 NOT NULL,
                distributed_points INTEGER DEFAULT 0 NOT NULL,
                remaining_points INTEGER DEFAULT 10000 NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
            );
            """,
            
            # Create index for performance
            """
            CREATE INDEX IF NOT EXISTS results_dailypointspool_date_idx ON results_dailypointspool(date);
            """,
            
            # Create today's pool (2025-07-26)
            """
            INSERT INTO results_dailypointspool (date, total_budget, distributed_points, remaining_points)
            VALUES ('2025-07-26', 10000, 0, 10000)
            ON CONFLICT (date) DO NOTHING;
            """,
            
            # Verify other tables exist
            """
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name LIKE '%points%';
            """
        ]

        try:
            with connection.cursor() as cursor:
                for i, sql in enumerate(sql_commands[:-1]):  # Skip the last SELECT for execution
                    self.stdout.write(f'📝 Executing command {i+1}...')
                    cursor.execute(sql)
                
                # Execute the verification query
                cursor.execute(sql_commands[-1])
                count = cursor.fetchone()[0]
                
                self.stdout.write(
                    self.style.SUCCESS(f'✅ Points system setup complete!')
                )
                self.stdout.write(f'📊 Found {count} points tables in database')
                
                # List the points tables
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name LIKE '%points%'
                    ORDER BY table_name;
                """)
                
                tables = cursor.fetchall()
                self.stdout.write('📋 Points system tables:')
                for table in tables:
                    self.stdout.write(f'   ✅ {table[0]}')
                
                # Check today's pool
                cursor.execute("SELECT * FROM results_dailypointspool WHERE date = '2025-07-26';")
                pool = cursor.fetchone()
                
                if pool:
                    self.stdout.write('💰 Today\'s Points Pool:')
                    self.stdout.write(f'   📅 Date: {pool[1]}')
                    self.stdout.write(f'   💵 Total Budget: {pool[2]:,}')
                    self.stdout.write(f'   📤 Distributed: {pool[3]:,}')
                    self.stdout.write(f'   💎 Remaining: {pool[4]:,}')
                else:
                    self.stdout.write(self.style.WARNING('⚠️ No pool found for today'))
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error creating points table: {e}')
            )
            return
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('🎉 Points system is ready!'))
        self.stdout.write('🧪 You can now test the check-ticket API after 3:00 PM IST')
        self.stdout.write('📱 API endpoint: /api/results/check-ticket/')
        self.stdout.write('📊 Points history: /api/results/user-points/')