from alembic import op

revision = "0002"
down_revision = "0001"


def upgrade():
    op.execute("""
    CREATE FUNCTION core.extend_calendar(a timestamptz,b timestamptz) RETURNS void LANGUAGE plpgsql AS $$
    DECLARE lo timestamptz; hi timestamptz;
    BEGIN
      SELECT least(a,coalesce(min(period_start),a)),greatest(b,coalesce(max(period_end),b)) INTO lo,hi FROM core.reporting_calendar;
      lo=date_trunc('hour',lo)+floor(extract(minute FROM lo)/30)*interval '30 minutes';
      INSERT INTO core.reporting_calendar
      SELECT t,t+interval '30 minutes',(t AT TIME ZONE 'Europe/London')::date,
        (extract(epoch FROM t-(((t AT TIME ZONE 'Europe/London')::date)::timestamp AT TIME ZONE 'Europe/London'))/1800)::int+1,
        extract(hour FROM t AT TIME ZONE 'Europe/London')::int,
        extract(isodow FROM t AT TIME ZONE 'Europe/London')::int,
        extract(isodow FROM t AT TIME ZONE 'Europe/London')>5
      FROM generate_series(lo,hi-interval '1 second',interval '30 minutes') t
      ON CONFLICT DO NOTHING;
    END $$;
    REVOKE ALL ON FUNCTION core.extend_calendar(timestamptz,timestamptz) FROM PUBLIC;
    GRANT EXECUTE ON FUNCTION core.extend_calendar(timestamptz,timestamptz) TO gridsignal_writer;
    SELECT core.extend_calendar((SELECT min(period_start) FROM core.reporting_calendar),(SELECT max(period_end) FROM core.reporting_calendar));
    """)


def downgrade():
    op.execute("DROP FUNCTION core.extend_calendar(timestamptz,timestamptz)")
