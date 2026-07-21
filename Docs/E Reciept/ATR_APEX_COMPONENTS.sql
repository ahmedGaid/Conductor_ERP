CREATE OR REPLACE PACKAGE BODY PRD."ATR_APEX_COMPONENTS" 
AS
FUNCTION is_prod
        RETURN BOOLEAN
    IS
        v_name   VARCHAR2 (100);
    BEGIN
        IF SYS_CONTEXT ('USERENV', 'DB_NAME') = 'ATRPROD'
        THEN
            RETURN TRUE;
        ELSE
            RETURN FALSE;
        END IF;
    END;

END;
/
