FROM postgres:15

# Copy initialization scripts
COPY init.sql /docker-entrypoint-initdb.d/01-init.sql

# Set permissions
RUN chmod 644 /docker-entrypoint-initdb.d/01-init.sql

# Enable pg_stat_statements for query lineage tracking in OpenMetadata
# The extension is loaded via command line args and created in init.sql
CMD ["postgres", "-c", "shared_preload_libraries=pg_stat_statements", "-c", "pg_stat_statements.track=all", "-c", "pg_stat_statements.max=10000"]
