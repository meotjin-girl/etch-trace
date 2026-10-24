-- Live Agent Server threads are independent of legacy tasks.
CREATE TABLE IF NOT EXISTS v1_live_investigations (
    id uuid PRIMARY KEY,
    alert jsonb NOT NULL,
    summary text NOT NULL,
    candidates jsonb NOT NULL CHECK (
        jsonb_typeof(candidates) = 'array' AND jsonb_array_length(candidates) > 0
    ),
    revision bigint NOT NULL CHECK (revision > 0),
    approval jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE OR REPLACE FUNCTION preserve_live_investigation_evidence()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.alert IS DISTINCT FROM OLD.alert THEN
        RAISE EXCEPTION 'Investigation alert is immutable' USING ERRCODE = '23514';
    END IF;
    IF OLD.approval IS NOT NULL AND NEW.approval IS DISTINCT FROM OLD.approval THEN
        RAISE EXCEPTION 'Investigation approval is immutable' USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE TRIGGER preserve_live_investigation_evidence
BEFORE UPDATE ON v1_live_investigations
FOR EACH ROW EXECUTE FUNCTION preserve_live_investigation_evidence();
