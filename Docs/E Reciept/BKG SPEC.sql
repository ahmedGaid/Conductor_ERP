/* Formatted on 4/8/2026 9:20:57 AM (QP5 v5.336) */
CREATE OR REPLACE PACKAGE PRD."ATR_ELECTRONIC_RECEIPT"
IS
    FUNCTION get_wallet_path
        RETURN VARCHAR2;

    FUNCTION get_wallet_pwd
        RETURN VARCHAR2;

    FUNCTION get_url (P_server IN VARCHAR2, p_type IN VARCHAR2)
        RETURN VARCHAR2;

    FUNCTION get_credentials (P_server IN VARCHAR2, p_type IN VARCHAR2)
        RETURN VARCHAR2;

    FUNCTION Login_as_Taxpayer_System (P_server IN VARCHAR2)
        RETURN VARCHAR2;

    PROCEDURE get_invoice_signature (l_body            IN     CLOB,
                                     P_server          IN     VARCHAR2,
                                     l_response           OUT CLOB,
                                     l_out_signature      OUT CLOB);

    PROCEDURE get_receipt (l_hash IN VARCHAR2);

    PROCEDURE Submit_Documents_JSON (P_RECEIPT_ID IN NUMBER, P_PERSON_ID IN NUMBER, P_server IN VARCHAR2);

    PROCEDURE Submit_Documents_credit (P_RECEIPT_ID IN NUMBER, P_PERSON_ID IN NUMBER, P_server IN VARCHAR2);

    PROCEDURE Submit_Documents_no_reference (P_RECEIPT_ID IN NUMBER, P_PERSON_ID IN NUMBER, P_server IN VARCHAR2);

    PROCEDURE AutoSubmit_RECEIPT (errbuf OUT NOCOPY VARCHAR2, retcode OUT NOCOPY NUMBER);

    PROCEDURE AutoGET_RECEIPT (errbuf OUT NOCOPY VARCHAR2, retcode OUT NOCOPY NUMBER);
END;
/