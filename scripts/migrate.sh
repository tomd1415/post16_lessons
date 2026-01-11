#!/bin/bash
# Database migration script for new improvements
# Creates new tables: login_attempts, api_rate_limits

set -e

echo "=== Post16 Lessons Database Migration ==="
echo "This script will create new database tables required for improvements."
echo ""
echo "New tables to be created:"
echo "  - login_attempts (persisted login rate limiting)"
echo "  - api_rate_limits (API rate limiting tracking)"
echo ""
read -p "Continue? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]
then
    echo "Migration cancelled."
    exit 1
fi

echo ""
echo "Creating new database tables..."

docker compose exec api python -c "
from app.db import engine
from app.models import Base, LoginAttempt, ApiRateLimit

print('Creating tables...')
Base.metadata.create_all(bind=engine)
print('✓ Tables created successfully!')

# Verify tables exist
from sqlalchemy import inspect
inspector = inspect(engine)
tables = inspector.get_table_names()

if 'login_attempts' in tables:
    print('✓ login_attempts table exists')
else:
    print('✗ login_attempts table NOT found')

if 'api_rate_limits' in tables:
    print('✓ api_rate_limits table exists')
else:
    print('✗ api_rate_limits table NOT found')
"

echo ""
echo "=== Migration Complete ==="
echo "Database has been updated with new tables."
echo ""
echo "Next steps:"
echo "  1. Restart the application: docker compose restart api"
echo "  2. Test the improvements (see docs/improvements-summary.md)"
echo "  3. Review logs: docker compose logs -f api"
