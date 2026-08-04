FROM apache/superset:4.1.1

# Switch to root to install additional Python packages required for
# connecting to the demo warehouses and rendering charts.
USER root

# Both warehouse drivers ship in one image so a single Superset stack serves
# either target. Versions are pinned to keep the demo reproducible.
RUN pip install --no-cache-dir \
        sqlalchemy-redshift==0.8.14 \
        redshift-connector==2.1.4 \
        sqlalchemy-bigquery==1.11.0 \
        psycopg2-binary==2.9.10 \
        Pillow

# Drop back to the unprivileged `superset` user that the base image expects.
USER superset
