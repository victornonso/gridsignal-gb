#!/bin/sh
set -eu
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" --set=writer="$WRITER_PASSWORD" --set=reader="$READER_PASSWORD" <<'SQL'
CREATE ROLE gridsignal_writer LOGIN PASSWORD :'writer';
CREATE ROLE gridsignal_reader LOGIN PASSWORD :'reader';
GRANT CONNECT ON DATABASE gridsignal_db TO gridsignal_writer, gridsignal_reader;
SQL

