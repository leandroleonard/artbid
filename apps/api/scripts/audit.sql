BEGIN;

SET LOCAL lock_timeout = '5s';
SET LOCAL statement_timeout = '30s';

CREATE FUNCTION public.artbid_audit_guard_v1()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog
AS $$
BEGIN
    RAISE LOG
        'ARTBID_AUDIT_BLOCK operation=% table=%.% session_user=% current_user=% client=% application=%',
        TG_OP,
        TG_TABLE_SCHEMA,
        TG_TABLE_NAME,
        session_user,
        current_user,
        inet_client_addr(),
        current_setting('application_name', true);

    RAISE EXCEPTION
        'Histórico protegido: operação % proibida em %.%',
        TG_OP,
        TG_TABLE_SCHEMA,
        TG_TABLE_NAME
        USING
            ERRCODE = '42501',
            HINT = 'Eventos e checkpoints são append-only. Não altere nem remova registos existentes.';

    RETURN NULL;
END;
$$;

-- Protecção dos eventos.
CREATE TRIGGER artbid_audit_events_guard_v1
BEFORE UPDATE OR DELETE OR TRUNCATE
ON public.audit_events
FOR EACH STATEMENT
EXECUTE FUNCTION public.artbid_audit_guard_v1();

ALTER TABLE public.audit_events
    ENABLE ALWAYS TRIGGER artbid_audit_events_guard_v1;

CREATE TRIGGER artbid_audit_checkpoints_guard_v1
BEFORE UPDATE OR DELETE OR TRUNCATE
ON public.audit_checkpoints
FOR EACH STATEMENT
EXECUTE FUNCTION public.artbid_audit_guard_v1();

ALTER TABLE public.audit_checkpoints
    ENABLE ALWAYS TRIGGER artbid_audit_checkpoints_guard_v1;

COMMIT;