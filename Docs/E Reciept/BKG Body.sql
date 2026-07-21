/* Formatted on 4/8/2026 9:25:24 AM (QP5 v5.336) */
CREATE OR REPLACE PACKAGE BODY PRD.ATR_ELECTRONIC_RECEIPT
IS
    FUNCTION get_wallet_path
        RETURN VARCHAR2
    AS
    BEGIN
        IF prd.ATR_APEX_COMPONENTS.is_prod
        THEN
            RETURN 'file:/u01/app/oracle/product/19.0.0/dbhome_1/owm/wallets/oracle/proddb';   
        ELSE
            RETURN 'file:/u01/app/oracle/product/19.0.0/dbhome_1/owm/wallets/oracle/proddb';
        --            RETURN 'file:/testdb/testdb/19.6/19.6/owm/wallets/testdb';
        END IF;
    END get_wallet_path;

    FUNCTION get_wallet_pwd
        RETURN VARCHAR2
    AS
    BEGIN
        IF prd.ATR_APEX_COMPONENTS.is_prod
        THEN
            RETURN 'CLOUD_CES';
        ELSE
            RETURN 'CLOUD_CES';

        END IF;
    END get_wallet_pwd;

    FUNCTION get_url (P_server IN VARCHAR2, p_type IN VARCHAR2)
        RETURN VARCHAR2
    AS
        L_URL   VARCHAR2 (500);
    BEGIN
        IF P_server = 'Preprod' AND p_type = 'Token'
        THEN
            L_URL   := 'https://id.preprod.eta.gov.eg/connect/token';
        ELSIF P_server = 'Prod' AND p_type = 'Token'
        THEN
            L_URL   := 'https://id.eta.gov.eg/connect/token';
        ELSIF P_server = 'Preprod' AND p_type = 'API'
        THEN
            L_URL   := 'https://api.preprod.invoicing.eta.gov.eg';
        ELSIF P_server = 'Prod' AND p_type = 'API'
        THEN
            L_URL   := 'https://api.invoicing.eta.gov.eg';
        ELSIF P_server IN ('Preprod', 'Prod') AND p_type = 'signature'
        THEN
            L_URL   := 'http://10.13.188.8DS:443121/Api/Invoice/Sign';
        END IF;

        RETURN L_URL;
    END get_url;

    FUNCTION get_credentials (P_server IN VARCHAR2, p_type IN VARCHAR2)
        RETURN VARCHAR2
    AS
        L_credential   VARCHAR2 (500);
    BEGIN
        IF P_server = 'Prod' AND p_type = 'client_id'
        THEN
            L_credential   := '5ce1c223-c8c4-44a4-9181-81a46dd1b4c0';
        ELSIF P_server = 'Prod' AND p_type = 'l_client_secret'
        THEN
            L_credential   := 'c007741a-5237-421d-9f85-022c78e05479';
        ELSIF P_server = 'Preprod' AND p_type = 'client_id'
        THEN
            L_credential   := 'dcd2e363-e806-4fa9-b53a-0ef36aa6428a';
        ELSIF P_server = 'Preprod' AND p_type = 'l_client_secret'
        THEN
            L_credential   := '194b4ea5-97e4-463f-b9bc-eb9f08af036b';
        END IF;

        RETURN L_credential;
    END get_credentials;


    FUNCTION Login_as_Taxpayer_System (P_server IN VARCHAR2)
        RETURN VARCHAR2
    IS
        l_token           VARCHAR2 (4000);
        l_url             VARCHAR2 (4000);
        jtoken            apex_json.t_values;
        l_grant_type      VARCHAR2 (400) := 'client_credentials';
        l_client_id       VARCHAR2 (500) := get_credentials (P_server, 'client_id');
        l_client_secret   VARCHAR2 (500) := get_credentials (P_server, 'l_client_secret');
        l_scope           VARCHAR2 (300) := 'InvoicingAPI';
    BEGIN
        /*----------Setting Headers----------------------------------------*/
        apex_web_service.g_request_headers (1).name    := 'Content-Type';
        apex_web_service.g_request_headers (1).VALUE   := 'application/x-www-form-urlencoded';
        l_url                                          := get_url (P_server, 'Token');
        l_token                                        :=
            apex_web_service.make_rest_request (
                p_url           => l_url,
                p_http_method   => 'POST',
                p_parm_name     => APEX_UTIL.string_to_table ('grant_type:client_id:client_secret:scope'),
                p_parm_value    => APEX_UTIL.string_to_table (l_grant_type || ':' || l_client_id || ':' || l_client_secret || ':' || l_scope),
                p_wallet_path   => get_wallet_path,
                p_wallet_pwd    => get_wallet_pwd);
        apex_json.parse (jtoken, l_token);
        RETURN l_token;
    END Login_as_Taxpayer_System;

    PROCEDURE get_invoice_signature (l_body            IN     CLOB,
                                     P_server          IN     VARCHAR2,
                                     l_response           OUT CLOB,
                                     l_out_signature      OUT CLOB)
    AS
        l_body_wo_sign     CLOB;
        l_out              CLOB;
        l_out_2            CLOB;
        l_response1        CLOB;
        request            UTL_HTTP.req;
        response           UTL_HTTP.resp;
        response_2         UTL_HTTP.resp;
        l_url              VARCHAR2 (2000);
        l_url_API          VARCHAR2 (2000);
        l_url_get          VARCHAR2 (2000);
        l_token            VARCHAR (32000);
        l_buffer_size      NUMBER := 1024;
        l_substring_msg    VARCHAR2 (32767);
        l_raw_data         RAW (32767);
        l_buffer           VARCHAR2 (32767);
        l_get_response_v   CLOB;
        l_uuid             VARCHAR2 (1000);
    BEGIN
        SELECT json_value (PRD.ATR_ELECTRONIC_RECEIPT.Login_as_Taxpayer_System (P_server), '$.access_token') INTO l_token FROM DUAL;



        l_body_wo_sign                                 := l_body;



        l_url                                          := get_url (P_server, 'signature');
        l_url_API                                      := get_url (P_server, 'API') || '/api/v1/receiptsubmissions';
        request                                        := UTL_HTTP.begin_request (l_url, 'POST', 'HTTP/1.1');

        UTL_HTTP.SET_BODY_CHARSET (request, 'UTF-8');
        UTL_HTTP.set_header (request, 'Content-Type', 'application/json');

        UTL_HTTP.SET_HEADER (request, 'Content-Length', LENGTH (l_body_wo_sign));

        FOR i IN 0 .. CEIL (LENGTH (l_body_wo_sign) / l_buffer_size) - 1
        LOOP
            l_substring_msg   := SUBSTR (l_body_wo_sign, i * l_buffer_size + 1, l_buffer_size);
            l_raw_data        := UTL_RAW.cast_to_raw (l_substring_msg);
            UTL_HTTP.write_raw (r => request, data => l_raw_data);
        END LOOP;


        DBMS_LOB.createtemporary (l_out, FALSE);
        response                                       := UTL_HTTP.get_response (request);
        apex_web_service.g_request_headers (1).name    := 'Content-Type';
        apex_web_service.g_request_headers (1).VALUE   := 'application/json';
        apex_web_service.g_request_headers (2).name    := 'Authorization';
        apex_web_service.g_request_headers (2).VALUE   := 'Bearer ' || l_token;

        LOOP
            UTL_HTTP.read_text (response, l_buffer, 32000);
            DBMS_LOB.writeappend (l_out, LENGTH (l_buffer), l_buffer);
            l_out_signature   := l_out;
            l_response1       :=
                apex_web_service.make_rest_request (p_url           => l_url_API,
                                                    p_http_method   => 'POST',
                                                    p_body          => l_body_wo_sign,
                                                    p_wallet_path   => get_wallet_path,
                                                    p_wallet_pwd    => get_wallet_pwd);
            l_response        := l_response1;
        END LOOP;

        UTL_HTTP.END_RESPONSE (response);
        DBMS_LOB.freetemporary (l_out);
    EXCEPTION
        WHEN UTL_HTTP.END_OF_BODY
        THEN
            UTL_HTTP.END_RESPONSE (response);
    END get_invoice_signature;

    PROCEDURE get_receipt (L_HASH VARCHAR2)
    AS
        l_get_response      CLOB;
        l_debug_result_id   NUMBER;
        l_RECEIPT_NUMBER    VARCHAR2 (10000);
        l_status            VARCHAR2 (10000);
        LAST_DEBUG_ID       NUMBER;
    BEGIN
        l_get_response      :=
            APEX_WEB_SERVICE.make_rest_request (p_url           => 'https://api.invoicing.eta.gov.eg/api/v1/receipts/' || l_hash || '/raw',
                                                p_http_method   => 'GET',
                                                p_parm_name     => APEX_UTIL.string_to_table ('uuid'),
                                                p_parm_value    => APEX_UTIL.string_to_table (l_hash));

        l_debug_result_id   := PRD.ATR_E_RECEIPT_DEBUG_RESULT_SEQ.NEXTVAL;


        INSERT INTO PRD.ATR_E_RECEIPT_DEBUG_RESULT (DEBUG_RESULT_ID,
                                                    URL,
                                                    STATUS_CODE,
                                                    WEB_SERVICE_NAME,
                                                    WEB_SERVICE_METHOD,
                                                    DEBUG_RESULT,
                                                    CREATION_DATE,
                                                    LAST_UPDATED_DATE,
                                                    UUID)
             VALUES (l_debug_result_id,
                     'https://api.invoicing.eta.gov.eg/api/v1/receipts/' || l_hash || '/raw',
                     apex_web_service.g_status_code,
                     'GET RECEIPT (JSON)',
                     'GET',
                     l_get_response,
                     SYSDATE,
                     SYSDATE,
                     L_HASH);

        SELECT JSON_VALUE (debug_result, '$.receipt.status' RETURNING VARCHAR2)
          INTO l_status
          FROM PRD.ATR_E_RECEIPT_DEBUG_RESULT
         WHERE debug_result_id = l_debug_result_id;

        SELECT JSON_VALUE (debug_result, '$.receipt.receiptNumber' RETURNING VARCHAR2)
          INTO l_RECEIPT_NUMBER
          FROM PRD.ATR_E_RECEIPT_DEBUG_RESULT
         WHERE debug_result_id = l_debug_result_id;


        SELECT MAX (DEBUG_RESULT_ID)
          INTO LAST_DEBUG_ID
          FROM PRD.ATR_E_RECEIPT_HISTORY
         WHERE INVOICE_NUMBER = l_RECEIPT_NUMBER;


        UPDATE PRD.ATR_E_RECEIPT_HISTORY
           SET typeName            = 'I',
               status              = l_status,
               NODE_NAME           = 'Prod',
               LAST_UPDATED_DATE   = SYSDATE,
               UUID                = l_hash
         WHERE DEBUG_RESULT_ID = LAST_DEBUG_ID;

        --                     INSERT INTO PRD.ATR_E_RECEIPT_HISTORY (DEBUG_RESULT_ID,
        --                                               typeName,
        --                                               status,
        --                                               NODE_NAME,
        --                                               CREATION_DATE,
        --                                               LAST_UPDATED_DATE,
        --                                               INVOICE_NUMBER,
        --                                               UUID)
        --                 VALUES (
        --                     l_debug_result_id,
        --                     'I',
        --                     l_status,
        --                     'Preprod',
        --                     SYSDATE,
        --                     SYSDATE,
        --                     l_RECEIPT_NUMBER,
        --                     l_hash);

        COMMIT;
    END get_receipt;


    PROCEDURE Submit_Documents_JSON (P_RECEIPT_ID IN NUMBER, P_PERSON_ID IN NUMBER, P_server IN VARCHAR2)
    AS
        l_url_API               VARCHAR2 (4000);
        l_token                 VARCHAR (32000);
        l_TRX_DATE              VARCHAR (2000) := TO_CHAR (SYSDATE - (3 / 24), 'YYYY-MM-DD"T"HH24:MI:SS"Z"');
        l_TRX_NUMBER            VARCHAR (32000);
        l_BILL_TO_CUSTOMER_ID   NUMBER;
        L_CURRENCY              VARCHAR2 (40);
        L_EXCHANGE_RATE         NUMBER;
        l_BILL_TO_SITE_USE_ID   NUMBER;
        l_total_sales_invoice   NUMBER;
        l_total_tax             NUMBER;
        l_total_invoice         NUMBER;
        l_body                  CLOB;
        l_json                  CLOB;
        l_body_2                CLOB;
        l_json_2                CLOB;
        l_out_signature         CLOB;
        l_response              CLOB;
        l_get_response          CLOB;
        l_get_response_f        CLOB;
        l_TAX_VALUE             NUMBER;
        l_uuid                  VARCHAR (2000);
        l_SERIALZE              CLOB;
        l_serialize_inv         CLOB;
        l_amount                VARCHAR2 (100);
        obj                     CLOB;
        l_hash                  RAW (5000);
        l_instr_1               NUMBER;
        l_after_time            CLOB;
        l_after_time_2          CLOB;
        l_after_time_3          CLOB;
        l_after_time_4          CLOB;
        l_after_time_5          CLOB;
        l_after_time_6          CLOB;
        l_after_time_7          CLOB;
        l_after_time_8          CLOB;
        l_after_time_9          CLOB;
        l_after_time_10         CLOB;
        l_before_time           CLOB;
        l_final_serialization   CLOB;
        l_time                  VARCHAR (6000);
        l_instr_2               VARCHAR (32000);
        l_instr_3               VARCHAR (32000);
        l_substr                VARCHAR (6000);
        l_substr_1              VARCHAR (10000);
        l_serialization         CLOB;
        l_json_for_serialize    CLOB;
        last_json               CLOB;
        f_json                  CLOB;
        l_last_json             CLOB;
        l_last_json_2           CLOB;
        l_last_json_3           CLOB;
        l_last_json_4           CLOB;
        l_last_json_5           CLOB;
        l_last_json_6           CLOB;
        l_last_json_7           CLOB;
        l_last_json_8           CLOB;
        l_last_json_9           CLOB;
        l_last_json_10          CLOB;
        l_final_json            CLOB;
        LAST_UUID               VARCHAR2 (2000);
        l_debug_result_id       NUMBER;
        l_body_wo_sign          CLOB;
        l_try                   CLOB;
        l_success               BOOLEAN := FALSE;
        l_status                VARCHAR2 (10000);
    BEGIN
        --        l_url_API   := get_url (P_server, 'API') || '/api/v1/receiptsubmissions/:submissionUuid/details?';


        SELECT json_value (prd.atr_electronic_receipt.Login_as_Taxpayer_System (P_server), '$.access_token') INTO l_token FROM DUAL;

        APEX_JSON.initialize_clob_output;
        APEX_JSON.open_object;
        APEX_JSON.open_array ('receipts');
        APEX_JSON.open_object;

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------


        APEX_JSON.open_object ('header');

        SELECT h.TRX_NUMBER,
               h.BILL_TO_CUSTOMER_ID,
               H.INVOICE_CURRENCY_CODE,
               H.EXCHANGE_RATE,
               h.BILL_TO_SITE_USE_ID                                                                                                               --,
          -- TO_CHAR (SYSDATE - (3 / 24), 'YYYY-MM-DD"T"HH24:MI:SS"Z"')     inv_date
          --case when h.ATTRIBUTE11 = '0999' then nvl (h.PURCHASE_ORDER,0) else '0' end   PURCHASE_ORDER
          INTO l_TRX_NUMBER,
               l_BILL_TO_CUSTOMER_ID,
               L_CURRENCY,
               L_EXCHANGE_RATE,
               l_BILL_TO_SITE_USE_ID
          -- l_TRX_DATE
          --      L_PURCHASE
          FROM AG.EVA_RA_CUSTOMER_TRX_ALL h
         WHERE 1 = 1 AND h.CUSTOMER_TRX_ID = P_RECEIPT_ID;

        /*SELECT UUID
          INTO LAST_UUID
          FROM PRD.ATR_E_RECEIPT_DEBUG_RESULT
         WHERE DEBUG_RESULT_ID = (SELECT MAX (DEBUG_RESULT_ID) FROM PRD.ATR_E_RECEIPT_DEBUG_RESULT)*/


        SELECT UUID
          INTO LAST_UUID
          FROM PRD.ATR_E_RECEIPT_DEBUG_RESULT
         WHERE DEBUG_RESULT_ID = (SELECT MAX (de.DEBUG_RESULT_ID)
                                    FROM PRD.ATR_E_RECEIPT_DEBUG_RESULT de, PRD.ATR_E_RECEIPT_HISTORY hi
                                   WHERE de.DEBUG_RESULT_ID = hi.DEBUG_RESULT_ID AND hi.STATUS = 'valid');

        --          SELECT ''
        --          INTO LAST_UUID
        --          FROM dual;

        APEX_JSON.write ('dateTimeIssued', l_TRX_DATE);
        APEX_JSON.write ('receiptNumber', l_TRX_NUMBER);
        APEX_JSON.write ('uuid', ' ');
        APEX_JSON.write ('previousUUID', LAST_UUID);
        APEX_JSON.write ('referenceOldUUID', ' ');
        APEX_JSON.write ('currency', UPPER (L_CURRENCY));
        APEX_JSON.write ('exchangeRate', L_EXCHANGE_RATE);
        APEX_JSON.write ('sOrderNameCode', '0');
        APEX_JSON.write ('orderdeliveryMode', 'FC');
        APEX_JSON.write ('grossWeight', 0);
        APEX_JSON.write ('netWeight', 0);
        APEX_JSON.close_object;
        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------

        APEX_JSON.open_object ('documentType');
        APEX_JSON.write ('receiptType', 'S');
        APEX_JSON.write ('typeVersion', '1.2');
        APEX_JSON.close_object;

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------

        APEX_JSON.open_object ('seller');
        APEX_JSON.write ('rin', '484380486');
        APEX_JSON.write ('companyTradeName', 'اسم الشركة');
        APEX_JSON.write ('branchCode', '0');
        -------------------------------------------
        APEX_JSON.open_object ('branchAddress');
        APEX_JSON.write ('country', 'EG');
        APEX_JSON.write ('governate', 'EGYPT');
        APEX_JSON.write ('regionCity', 'EGYPT');
        APEX_JSON.write ('street', 'GIZA');
        APEX_JSON.write ('buildingNumber', '135');
        APEX_JSON.write ('postalCode', '125311');
        APEX_JSON.write ('floor', '0');
        APEX_JSON.write ('room', '0');
        APEX_JSON.write ('landmark', '0');
        APEX_JSON.write ('additionalInformation', '0');
        APEX_JSON.close_object;
        -------------------------------------------
        APEX_JSON.write ('deviceSerialNumber', 'TRF4FFDS5');
        APEX_JSON.write ('syndicateLicenseNumber', '0');
        APEX_JSON.write ('activityCode', '4882');
        APEX_JSON.close_object;


        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------

        APEX_JSON.open_object ('buyer');

        FOR Buyer IN (SELECT h.CUST_ACCOUNT_ID,
                             SITE_USES.SITE_USE_ID,
                             CASE WHEN h.ATTRIBUTE11 IS NOT NULL THEN 'B' ELSE 'P' END    TYPE,
                             --h.ACCOUNT_NUMBER id,
                             0                                                            id,
                             -- loc.CITY                                                     id,
                             (SELECT DISTINCT h.ACCOUNT_NAME
                                FROM ONT.OE_ORDER_HEADERS_ALL    soh,
                                     AG.EVA_RA_CUSTOMER_TRX_ALL  CT,
                                     apps.HZ_CUST_SITE_USES_ALL  SITE_USES,
                                     apps.HZ_CUST_ACCOUNTS       h
                               WHERE     CT.CT_REFERENCE = SOH.ORDER_NUMBER
                                     AND CT.BILL_TO_CUSTOMER_ID = H.CUST_ACCOUNT_ID
                                     AND SOH.ORG_ID = 1963
                                     AND SOH.ORG_ID = CT.ORG_ID
                                     AND CT.BILL_TO_SITE_USE_ID = SITE_USES.SITE_USE_ID
                                     AND H.CUST_ACCOUNT_ID = l_BILL_TO_CUSTOMER_ID
                                     AND SITE_USES.SITE_USE_ID = l_BILL_TO_SITE_USE_ID
                                     AND CT.TRX_NUMBER = l_TRX_NUMBER
                                     AND SOH.ATTRIBUTE18 IS NOT NULL)                     name,
                             loc.COUNTRY                                                  country,
                             'Egypt'                                                      governate,
                             --                       'Egypt'                                regioncity,
                             --                       'Cairo - Egypt'                        street,
                             loc.ADDRESS1                                                 regionCity,
                             loc.ADDRESS1                                                 street,
                             ''                                                           buildingNumber,
                             ''                                                           postalCode,
                             ''                                                           FLOOR,
                             ''                                                           room,
                             ''                                                           landmark,
                             ''                                                           additionalInformation
                        FROM apps.HZ_CUST_ACCOUNTS        h,
                             apps.hz_parties              HP,
                             APPS.HZ_LOCATIONS            loc,
                             APPS.HZ_PARTY_SITES          party_sites,
                             apps.HZ_CUST_ACCT_SITES_ALL  ACCT_SITES,
                             APPS.HZ_CUST_ACCOUNTS_ALL    CUST_ACCOUNTS,
                             apps.HZ_CUST_SITE_USES_ALL   SITE_USES,
                             APPS.FND_FLEX_VALUES_VL      FLEX
                       WHERE     loc.LOCATION_ID = party_sites.LOCATION_ID
                             AND ACCT_SITES.PARTY_SITE_ID = party_sites.PARTY_SITE_ID
                             AND h.party_id = hp.party_id
                             AND HP.party_id = party_sites.party_id
                             AND CUST_ACCOUNTS.CUST_ACCOUNT_ID = ACCT_SITES.CUST_ACCOUNT_ID
                             AND SITE_USES.CUST_ACCT_SITE_ID = ACCT_SITES.CUST_ACCT_SITE_ID
                             /*****Updated by Mareham*****/
                             AND FLEX.FLEX_VALUE_SET_ID(+) = 1018193
                             AND FLEX.ENABLED_FLAG = 'Y'
                             AND FLEX.ATTRIBUTE3 = 'EG'
                             AND HP.PROVINCE = FLEX.FLEX_VALUE
                             /*************************/
                             --                       AND FLEX.FLEX_VALUE_SET_ID(+) = 1022025
                             --                       AND party_sites.ATTRIBUTE2 =
                             --                           FLEX.FLEX_VALUE_MEANING(+)
                             AND h.CUST_ACCOUNT_ID = CUST_ACCOUNTS.CUST_ACCOUNT_ID
                             AND h.CUST_ACCOUNT_ID IN (1836040,
                                                       2468432,
                                                       1339188,
                                                       2519757,
                                                       2596516,
                                                       2658528)
                             AND CUST_ACCOUNTS.CUST_ACCOUNT_ID = l_BILL_TO_CUSTOMER_ID
                             AND SITE_USES.SITE_USE_ID = l_BILL_TO_SITE_USE_ID)
        LOOP
            APEX_JSON.write ('type', 'P');
            APEX_JSON.write ('id', ' ');
            APEX_JSON.write ('name', UPPER (Buyer.name));
            APEX_JSON.write ('mobileNumber', '0');
            APEX_JSON.write ('paymentNumber', '0');
            APEX_JSON.close_object;
        END LOOP;

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------
        APEX_JSON.open_array ('itemData');

        FOR cur_rec
            IN (WITH
                    mst
                    AS
                        (SELECT NVL (EGS_ITEM_CODE, i.segment1)          item_code,
                                i.segment1                               internalCode,
                                i.INVENTORY_ITEM_ID,
                                NVL (UOM, i.PRIMARY_UNIT_OF_MEASURE)     uom,
                                TAXABLE_TYPES,
                                TAX_SUBTYPES
                           FROM APPS.MTL_SYSTEM_ITEMS_FVL i, prd.ATR_ELECTRONIC_INVOICE_MAPPING_ITEMS MAP_ITEM
                          WHERE i.organization_id = 1964 AND MAP_ITEM.INVENTORY_ITEM_ID(+) = i.INVENTORY_ITEM_ID               -- AND item_type = 'FG'
                                                                                                                ),
                    CTAL
                    AS
                        (SELECT NVL (ctal.UNIT_STANDARD_PRICE, 0) * NVL (ctal.QUANTITY_INVOICED, 0) PRICE, ctal.CUSTOMER_TRX_LINE_ID
                           FROM AG.EVA_RA_CUSTOMER_TRX_LINES_ALL ctal
                          WHERE NVL (ctal.UNIT_SELLING_PRICE, 0) = 0)
                SELECT DISTINCT d.CUSTOMER_TRX_LINE_ID,
                                h.CUSTOMER_TRX_ID,
                                LINE_NUMBER,
                                h.EXCHANGE_RATE,
                                h.INVOICE_CURRENCY_CODE,
                                d.INVENTORY_ITEM_ID,
                                --DESCRIPTION description,
                                REGEXP_REPLACE (DESCRIPTION, '"')                                                           description,
                                'EGS'                                                                                       itemType,
                                'EG-484380486-' || mst.item_code                                                            itemCode,
                                mst.internalCode                                                                            internalCode,
                                mst.TAXABLE_TYPES                                                                           TAXABLE_TYPES,
                                CASE WHEN TAX_CLASSIFICATION_CODE = 'INPUT S_T 0%' THEN 'V003' ELSE MST.TAX_SUBTYPES END    TAX_SUBTYPES,
                                mst.uom                                                                                     unitType,
                                QUANTITY_INVOICED                                                                           quantity,
                                ROUND (NVL (UNIT_SELLING_PRICE, 0), 5)                                                      unitPrice,
                                ROUND (NVL (REVENUE_AMOUNT, 0), 5)                                                          salesTotal,
                                ROUND (
                                      NVL (REVENUE_AMOUNT, 0)
                                    + NVL (TAX_RECOVERABLE, 0)
                                    + NVL ((SELECT ROUND ((NVL (PAV.ADJUSTED_AMOUNT, 0)) * NVL (d.quantity_invoiced, 0), 2)
                                              FROM APPS.OE_PRICE_ADJUSTMENTS_V PAV
                                             WHERE PAV.LIST_LINE_TYPE_CODE = 'FREIGHT_CHARGE' AND PAV.LINE_ID = INTERFACE_LINE_ATTRIBUTE6),
                                           0),
                                    5)                                                                                      total,
                                CASE
                                    WHEN     (SELECT mst.TAX_SUBTYPES
                                                FROM prd.atr_E_INVOICE_TAXABLE_SUBTYPES ts
                                               WHERE ts.TAXABLE_CODE = mst.TAX_SUBTYPES) IN ('V009')
                                         AND d.unit_selling_price = 0
                                    THEN
                                        ROUND (
                                            (SELECT ROUND (
                                                          ROUND ((NVL (PAV.ADJUSTED_AMOUNT, 0)) * NVL (ctal.quantity_invoiced, 0), 2)
                                                        * 100
                                                        / 14,
                                                        5)    fre
                                               FROM APPS.OE_PRICE_ADJUSTMENTS_V PAV, AG.EVA_RA_CUSTOMER_TRX_LINES_ALL CTAL
                                              WHERE     PAV.LIST_LINE_TYPE_CODE = 'FREIGHT_CHARGE'
                                                    AND PAV.LINE_ID = CTAL.INTERFACE_LINE_ATTRIBUTE6
                                                    AND NVL (CTAL.UNIT_SELLING_PRICE, 0) = 0
                                                    AND ctal.CUSTOMER_TRX_ID = P_RECEIPT_ID
                                                    AND PAV.LINE_ID(+) = d.INTERFACE_LINE_ATTRIBUTE6),
                                            5)
                                    --   round(nvl(d.unit_standard_price,0) * nvl(d.quantity_invoiced,0),5)
                                    WHEN     ROUND (NVL (TAX_RECOVERABLE, 0), 5) <>
                                             TRUNC ((  NVL (REVENUE_AMOUNT, 0)
                                                     * (  (SELECT ts.TAX_VALUE
                                                             FROM prd.atr_E_INVOICE_TAXABLE_SUBTYPES ts
                                                            WHERE ts.TAXABLE_CODE = mst.TAX_SUBTYPES)
                                                        / 100)),
                                                    2)
                                         AND (SELECT mst.TAX_SUBTYPES
                                                FROM prd.atr_E_INVOICE_TAXABLE_SUBTYPES ts
                                               WHERE ts.TAXABLE_CODE = mst.TAX_SUBTYPES) IN ('V010')
                                    THEN
                                          ROUND (
                                                (  (ROUND (((  UNIT_SELLING_PRICE
                                                             * QUANTITY_INVOICED
                                                             * (  (SELECT ts.TAX_VALUE
                                                                     FROM prd.atr_E_INVOICE_TAXABLE_SUBTYPES ts
                                                                    WHERE ts.TAXABLE_CODE = mst.TAX_SUBTYPES)
                                                                / 100))),
                                                           5))
                                                 - (  (NVL (REVENUE_AMOUNT, 0) + NVL (TAX_RECOVERABLE, 0))
                                                    - ROUND (NVL (UNIT_SELLING_PRICE, 0) * NVL (QUANTITY_INVOICED, 0), 5)))
                                              * (100 / 14),
                                              5)
                                        * -1
                                    ELSE
                                        0
                                END                                                                                         valueDifference,
                                0                                                                                           totalTaxableFees,
                                --nvl(REVENUE_AMOUNT,0) + nvl(TAX_RECOVERABLE,0)
                                ROUND (NVL (REVENUE_AMOUNT, 0), 5)                                                          netTotal,
                                0                                                                                           itemsDiscount,
                                SALES_ORDER,
                                SALES_ORDER_DATE,
                                LINE_TYPE,
                                ROUND (EXTENDED_AMOUNT, 5)                                                                  EXTENDED_AMOUNT,
                                ROUND (LINE_RECOVERABLE, 5)                                                                 LINE_RECOVERABLE,
                                ROUND (TAX_RECOVERABLE, 5),
                                TAX_CLASSIFICATION_CODE
                  FROM AG.EVA_RA_CUSTOMER_TRX_ALL        h,
                       AG.EVA_RA_CUSTOMER_TRX_LINES_ALL  d,
                       mst,
                       CTAL
                 WHERE     h.CUSTOMER_TRX_ID = d.CUSTOMER_TRX_ID
                       AND h.CUSTOMER_TRX_ID = P_RECEIPT_ID
                       AND d.INVENTORY_ITEM_ID = mst.INVENTORY_ITEM_ID
                       AND d.CUSTOMER_TRX_LINE_ID <> 55590039                                                                             --22-05-2024
                       AND LINE_TYPE = 'LINE'
                       AND CTAL.CUSTOMER_TRX_LINE_ID(+) = d.CUSTOMER_TRX_LINE_ID
                       AND d.CUSTOMER_TRX_LINE_ID <> 36084217                                                                             --06/06/2023
                                                             )
        LOOP
            APEX_JSON.open_object;
            APEX_JSON.write ('internalCode', UPPER (cur_rec.internalCode));
            APEX_JSON.write ('description', UPPER (cur_rec.description));
            APEX_JSON.write ('itemType', UPPER (cur_rec.itemType));
            APEX_JSON.write ('itemCode', UPPER (cur_rec.itemCode));
            APEX_JSON.write ('unitType', UPPER (cur_rec.unitType));
            APEX_JSON.write ('quantity', cur_rec.quantity);
            APEX_JSON.write ('unitPrice', cur_rec.unitPrice);
            APEX_JSON.write ('netSale', cur_rec.netTotal);
            APEX_JSON.write ('totalSale', cur_rec.netTotal);
            APEX_JSON.write ('total', cur_rec.total);
            -------------------------------------------
            APEX_JSON.open_array ('commercialDiscountData');
            APEX_JSON.open_object;
            APEX_JSON.write ('amount', 0);
            APEX_JSON.write ('description', '0');
            APEX_JSON.write ('rate', 0);
            APEX_JSON.close_object;
            APEX_JSON.close_array;
            -------------------------------------------
            APEX_JSON.open_array ('itemDiscountData');
            APEX_JSON.open_object;
            APEX_JSON.write ('amount', 0);
            APEX_JSON.write ('description', '0');
            APEX_JSON.write ('rate', 0);
            APEX_JSON.close_object;
            APEX_JSON.close_array;
            -------------------------------------------
            APEX_JSON.open_object ('additionalCommercialDiscount');
            APEX_JSON.write ('amount', 0);
            APEX_JSON.write ('description', '0');
            APEX_JSON.write ('rate', 0);
            APEX_JSON.close_object;
            -------------------------------------------
            APEX_JSON.open_object ('additionalItemDiscount');
            APEX_JSON.write ('amount', 0);
            APEX_JSON.write ('description', '0');
            APEX_JSON.write ('rate', 0);
            APEX_JSON.close_object;
            -------------------------------------------
            APEX_JSON.write ('valueDifference', cur_rec.valueDifference);
            -------------------------------------------

            APEX_JSON.open_array ('taxableItems');

            FOR tax
                IN (SELECT tax.TAX_RATE_CODE,
                           PERCENTAGE_RATE,
                             d.TAX_RECOVERABLE
                           + NVL ((SELECT ROUND ((NVL (PAV.ADJUSTED_AMOUNT, 0)) * NVL (d.quantity_invoiced, 0), 2)
                                     FROM APPS.OE_PRICE_ADJUSTMENTS_V PAV
                                    WHERE PAV.LIST_LINE_TYPE_CODE = 'FREIGHT_CHARGE' AND PAV.LINE_ID = INTERFACE_LINE_ATTRIBUTE6),
                                  0)    TAX_RECOVERABLE
                      FROM ZX.ZX_RATES_B TAX, AG.EVA_RA_CUSTOMER_TRX_LINES_ALL d
                     WHERE     1 = 1
                           AND NVL (tax.ACTIVE_FLAG, 'Y') = 'Y'
                           AND d.TAX_CLASSIFICATION_CODE = TAX.TAX_RATE_CODE                                   -- and TAX.TAX_RATE_CODE ='PH_AR_P_14%'
                           AND SYSDATE BETWEEN TAX.EFFECTIVE_FROM AND NVL (TAX.EFFECTIVE_TO, SYSDATE + 1)
                           AND d.CUSTOMER_TRX_LINE_ID = cur_rec.CUSTOMER_TRX_LINE_ID)
            LOOP
                SELECT s.TAX_VALUE
                  INTO l_TAX_VALUE
                  FROM prd.atr_E_INVOICE_Taxable_Subtypes s
                 WHERE cur_rec.TAX_SUBTYPES = s.TAXABLE_CODE AND ROWNUM = 1;

                APEX_JSON.open_object;
                APEX_JSON.write ('taxType', NVL (UPPER (cur_rec.TAXABLE_TYPES), '0'));
                APEX_JSON.write ('amount', NVL (tax.TAX_RECOVERABLE, 0));
                APEX_JSON.write ('subType', NVL (UPPER (cur_rec.TAX_SUBTYPES), '0'));
                APEX_JSON.write ('rate', NVL (l_TAX_VALUE, 0));
                APEX_JSON.close_object;
            END LOOP;

            APEX_JSON.close_array;

            -------------------------------------------
            APEX_JSON.close_object;
        END LOOP;

        APEX_JSON.close_array;

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------
        WITH
            FR
            AS
                (SELECT ROUND ((NVL (PAV.ADJUSTED_AMOUNT, 0)) * NVL (ctal.quantity_invoiced, 0), 2) fre, PAV.LINE_ID
                   FROM APPS.OE_PRICE_ADJUSTMENTS_V PAV, AG.EVA_RA_CUSTOMER_TRX_LINES_ALL CTAL
                  WHERE     PAV.LIST_LINE_TYPE_CODE = 'FREIGHT_CHARGE'
                        AND PAV.LINE_ID = CTAL.INTERFACE_LINE_ATTRIBUTE6
                        AND NVL (CTAL.UNIT_SELLING_PRICE, 0) = 0
                        AND ctal.CUSTOMER_TRX_ID = P_RECEIPT_ID)
        SELECT ROUND (SUM (NVL (REVENUE_AMOUNT, 0)), 2)                                                 total_inv,
               ROUND (SUM (NVL (TAX_RECOVERABLE, 0)), 2)                                                total_tax,
               ROUND (SUM (NVL (REVENUE_AMOUNT, 0)), 2) + ROUND (SUM (NVL (TAX_RECOVERABLE, 0)), 2)     total_invoice
          INTO l_total_sales_invoice, l_total_tax, l_total_invoice
          FROM (SELECT NVL (REVENUE_AMOUNT, 0) REVENUE_AMOUNT, NVL (TAX_RECOVERABLE, 0) + NVL (fr.fre, 0) TAX_RECOVERABLE
                  --          INTO l_total_sales_invoice, l_total_tax, l_total_invoice
                  FROM AG.EVA_RA_CUSTOMER_TRX_ALL h, AG.EVA_RA_CUSTOMER_TRX_LINES_ALL d, FR
                 WHERE     h.CUSTOMER_TRX_ID = d.CUSTOMER_TRX_ID
                       AND h.CUSTOMER_TRX_ID = P_RECEIPT_ID
                       AND LINE_TYPE = 'LINE'
                       AND FR.LINE_ID(+) = d.INTERFACE_LINE_ATTRIBUTE6);

        APEX_JSON.write ('totalSales', l_total_sales_invoice);
        APEX_JSON.write ('totalCommercialDiscount', 0);
        APEX_JSON.write ('totalItemsDiscount', 0);

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------

        APEX_JSON.open_array ('extraReceiptDiscountData');
        APEX_JSON.open_object;
        APEX_JSON.write ('amount', 0);
        APEX_JSON.write ('description', '0');
        APEX_JSON.write ('rate', 0);
        APEX_JSON.close_object;
        APEX_JSON.close_array;

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------

        APEX_JSON.write ('netAmount', l_total_sales_invoice);
        APEX_JSON.write ('feesAmount', 0);
        APEX_JSON.write ('totalAmount', l_total_invoice);

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------

        APEX_JSON.open_array ('taxTotals');
        APEX_JSON.open_object;
        APEX_JSON.write ('taxType', 'T1');
        APEX_JSON.write ('amount', NVL (l_total_tax, 0));
        APEX_JSON.close_object;
        APEX_JSON.close_array;

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------

        APEX_JSON.write ('paymentMethod', 'V');
        APEX_JSON.write ('adjustment', 0);

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------

        APEX_JSON.open_object ('contractor');
        APEX_JSON.write ('name', '0');
        APEX_JSON.write ('amount', 0);
        APEX_JSON.write ('rate', 0);
        APEX_JSON.close_object;

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------

        APEX_JSON.open_object ('beneficiary');
        APEX_JSON.write ('amount', 0);
        APEX_JSON.write ('rate', 0);
        APEX_JSON.close_object;

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------
        APEX_JSON.close_object;
        APEX_JSON.close_array;
        APEX_JSON.close_object;
        L_json                  := apex_json.get_clob_output;
        l_json                  := REPLACE (l_json, '"uuid":" "', '"uuid":""');
        --        l_json                 := REPLACE (l_json, '"previousUUID":" "', '"previousUUID":""');
        l_json                  := REPLACE (l_json, '"referenceOldUUID":" "', '"referenceOldUUID":""');
        l_json                  := REPLACE (l_json, '"id":" "', '"id":""');

        SELECT JSON_QUERY (l_json, '$' RETURNING CLOB) INTO l_body FROM DUAL;

        ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
        ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


        APEX_JSON.initialize_clob_output;



        --        APEX_JSON.open_object;
        APEX_JSON.open_object;

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------


        APEX_JSON.open_object ('header');

        SELECT h.TRX_NUMBER,
               h.BILL_TO_CUSTOMER_ID,
               H.INVOICE_CURRENCY_CODE,
               H.EXCHANGE_RATE,
               h.BILL_TO_SITE_USE_ID                                                                                                               --,
          -- TO_CHAR (SYSDATE - (3 / 24), 'YYYY-MM-DD"T"HH24:MI:SS"Z"')     inv_date
          --case when h.ATTRIBUTE11 = '0999' then nvl (h.PURCHASE_ORDER,0) else '0' end   PURCHASE_ORDER
          INTO l_TRX_NUMBER,
               l_BILL_TO_CUSTOMER_ID,
               L_CURRENCY,
               L_EXCHANGE_RATE,
               l_BILL_TO_SITE_USE_ID
          -- l_TRX_DATE
          --      L_PURCHASE
          FROM AG.EVA_RA_CUSTOMER_TRX_ALL h
         WHERE 1 = 1 AND h.CUSTOMER_TRX_ID = P_RECEIPT_ID;

        APEX_JSON.write ('dateTimeIssued', UPPER (l_TRX_DATE));
        APEX_JSON.write ('receiptNumber', UPPER (l_TRX_NUMBER));
        APEX_JSON.write ('uuid', ' ');
        APEX_JSON.write ('previousUUID', LAST_UUID);
        APEX_JSON.write ('referenceOldUUID', ' ');
        APEX_JSON.write ('currency', UPPER (L_CURRENCY));
        APEX_JSON.write ('exchangeRate', UPPER (L_EXCHANGE_RATE));
        APEX_JSON.write ('sOrderNameCode', '0');
        APEX_JSON.write ('orderdeliveryMode', 'FC');
        APEX_JSON.write ('grossWeight', '0');
        APEX_JSON.write ('netWeight', '0');
        APEX_JSON.close_object;
        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------

        APEX_JSON.open_object ('documentType');
        APEX_JSON.write ('receiptType', 'S');
        APEX_JSON.write ('typeVersion', '1.2');
        APEX_JSON.close_object;

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------

        APEX_JSON.open_object ('seller');
        APEX_JSON.write ('rin', '484380486');
        APEX_JSON.write ('companyTradeName', 'اسم الشركة');
        APEX_JSON.write ('branchCode', '0');
        -------------------------------------------
        APEX_JSON.open_object ('branchAddress');
        APEX_JSON.write ('country', 'EG');
        APEX_JSON.write ('governate', 'EGYPT');
        APEX_JSON.write ('regionCity', 'EGYPT');
        APEX_JSON.write ('street', 'GIZA');
        APEX_JSON.write ('buildingNumber', '13');
        APEX_JSON.write ('postalCode', '12311');
        APEX_JSON.write ('floor', '0');
        APEX_JSON.write ('room', '0');
        APEX_JSON.write ('landmark', '0');
        APEX_JSON.write ('additionalInformation', '0');
        APEX_JSON.close_object;
        -------------------------------------------
        APEX_JSON.write ('deviceSerialNumber', 'TRF4340ZFDSS5');
        APEX_JSON.write ('syndicateLicenseNumber', '0');
        APEX_JSON.write ('activityCode', '4882');
        APEX_JSON.close_object;


        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------



        FOR Buyer IN (SELECT h.CUST_ACCOUNT_ID,
                             SITE_USES.SITE_USE_ID,
                             CASE WHEN h.ATTRIBUTE11 IS NOT NULL THEN 'B' ELSE 'P' END    TYPE,
                             --h.ACCOUNT_NUMBER id,
                             0                                                            id,
                             -- loc.CITY                                                     id,
                             (SELECT DISTINCT h.ACCOUNT_NAME
                                FROM ONT.OE_ORDER_HEADERS_ALL    soh,
                                     AG.EVA_RA_CUSTOMER_TRX_ALL  CT,
                                     apps.HZ_CUST_SITE_USES_ALL  SITE_USES,
                                     apps.HZ_CUST_ACCOUNTS       h
                               WHERE     CT.CT_REFERENCE = SOH.ORDER_NUMBER
                                     AND CT.BILL_TO_CUSTOMER_ID = H.CUST_ACCOUNT_ID
                                     AND SOH.ORG_ID = 1963
                                     AND SOH.ORG_ID = CT.ORG_ID
                                     AND CT.BILL_TO_SITE_USE_ID = SITE_USES.SITE_USE_ID
                                     AND H.CUST_ACCOUNT_ID = l_BILL_TO_CUSTOMER_ID
                                     AND SITE_USES.SITE_USE_ID = l_BILL_TO_SITE_USE_ID
                                     AND CT.TRX_NUMBER = l_TRX_NUMBER
                                     AND SOH.ATTRIBUTE18 IS NOT NULL)                     name,
                             loc.COUNTRY                                                  country,
                             'Egypt'                                                      governate,
                             --                       'Egypt'                                regioncity,
                             --                       'Cairo - Egypt'                        street,
                             loc.ADDRESS1                                                 regionCity,
                             loc.ADDRESS1                                                 street,
                             ''                                                           buildingNumber,
                             ''                                                           postalCode,
                             ''                                                           FLOOR,
                             ''                                                           room,
                             ''                                                           landmark,
                             ''                                                           additionalInformation
                        FROM apps.HZ_CUST_ACCOUNTS        h,
                             apps.hz_parties              HP,
                             APPS.HZ_LOCATIONS            loc,
                             APPS.HZ_PARTY_SITES          party_sites,
                             apps.HZ_CUST_ACCT_SITES_ALL  ACCT_SITES,
                             APPS.HZ_CUST_ACCOUNTS_ALL    CUST_ACCOUNTS,
                             apps.HZ_CUST_SITE_USES_ALL   SITE_USES,
                             APPS.FND_FLEX_VALUES_VL      FLEX
                       WHERE     loc.LOCATION_ID = party_sites.LOCATION_ID
                             AND ACCT_SITES.PARTY_SITE_ID = party_sites.PARTY_SITE_ID
                             AND h.party_id = hp.party_id
                             AND HP.party_id = party_sites.party_id
                             AND CUST_ACCOUNTS.CUST_ACCOUNT_ID = ACCT_SITES.CUST_ACCOUNT_ID
                             AND SITE_USES.CUST_ACCT_SITE_ID = ACCT_SITES.CUST_ACCT_SITE_ID
                             /*****Updated by Mareham*****/
                             AND FLEX.FLEX_VALUE_SET_ID(+) = 1018193
                             AND FLEX.ENABLED_FLAG = 'Y'
                             AND FLEX.ATTRIBUTE3 = 'EG'
                             AND HP.PROVINCE = FLEX.FLEX_VALUE
                             /*************************/
                             --                       AND FLEX.FLEX_VALUE_SET_ID(+) = 1022025
                             --                       AND party_sites.ATTRIBUTE2 =
                             --                           FLEX.FLEX_VALUE_MEANING(+)
                             AND h.CUST_ACCOUNT_ID = CUST_ACCOUNTS.CUST_ACCOUNT_ID
                             AND h.CUST_ACCOUNT_ID IN (1836040,
                                                       2468432,
                                                       1339188,
                                                       2519757,
                                                       2596516,
                                                       2658528)
                             AND CUST_ACCOUNTS.CUST_ACCOUNT_ID = l_BILL_TO_CUSTOMER_ID
                             AND SITE_USES.SITE_USE_ID = l_BILL_TO_SITE_USE_ID)
        LOOP
            APEX_JSON.open_object ('buyer');
            APEX_JSON.write ('type', 'P');
            APEX_JSON.write ('id', ' ');
            APEX_JSON.write ('name', UPPER (Buyer.name));
            APEX_JSON.write ('mobileNumber', '0');
            APEX_JSON.write ('paymentNumber', '0');
            APEX_JSON.close_object;
        END LOOP;

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------
        APEX_JSON.open_array ('itemData');
        APEX_JSON.open_object;

        FOR cur_rec
            IN (WITH
                    mst
                    AS
                        (SELECT NVL (EGS_ITEM_CODE, i.segment1)          item_code,
                                i.segment1                               internalCode,
                                i.INVENTORY_ITEM_ID,
                                NVL (UOM, i.PRIMARY_UNIT_OF_MEASURE)     uom,
                                TAXABLE_TYPES,
                                TAX_SUBTYPES
                           FROM APPS.MTL_SYSTEM_ITEMS_FVL i, prd.ATR_ELECTRONIC_INVOICE_MAPPING_ITEMS MAP_ITEM
                          WHERE i.organization_id = 1964 AND MAP_ITEM.INVENTORY_ITEM_ID(+) = i.INVENTORY_ITEM_ID               -- AND item_type = 'FG'
                                                                                                                ),
                    CTAL
                    AS
                        (SELECT NVL (ctal.UNIT_STANDARD_PRICE, 0) * NVL (ctal.QUANTITY_INVOICED, 0) PRICE, ctal.CUSTOMER_TRX_LINE_ID
                           FROM AG.EVA_RA_CUSTOMER_TRX_LINES_ALL ctal
                          WHERE NVL (ctal.UNIT_SELLING_PRICE, 0) = 0)
                SELECT DISTINCT d.CUSTOMER_TRX_LINE_ID,
                                h.CUSTOMER_TRX_ID,
                                LINE_NUMBER,
                                h.EXCHANGE_RATE,
                                h.INVOICE_CURRENCY_CODE,
                                d.INVENTORY_ITEM_ID,
                                --DESCRIPTION description,
                                REGEXP_REPLACE (DESCRIPTION, '"')                                                           description,
                                'EGS'                                                                                       itemType,
                                'EG-484380486-' || mst.item_code                                                            itemCode,
                                mst.internalCode                                                                            internalCode,
                                mst.TAXABLE_TYPES                                                                           TAXABLE_TYPES,
                                CASE WHEN TAX_CLASSIFICATION_CODE = 'INPUT S_T 0%' THEN 'V003' ELSE MST.TAX_SUBTYPES END    TAX_SUBTYPES,
                                mst.uom                                                                                     unitType,
                                QUANTITY_INVOICED                                                                           quantity,
                                ROUND (NVL (UNIT_SELLING_PRICE, 0), 5)                                                      unitPrice,
                                ROUND (NVL (REVENUE_AMOUNT, 0), 5)                                                          salesTotal,
                                ROUND (
                                      NVL (REVENUE_AMOUNT, 0)
                                    + NVL (TAX_RECOVERABLE, 0)
                                    + NVL ((SELECT ROUND ((NVL (PAV.ADJUSTED_AMOUNT, 0)) * NVL (d.quantity_invoiced, 0), 2)
                                              FROM APPS.OE_PRICE_ADJUSTMENTS_V PAV
                                             WHERE PAV.LIST_LINE_TYPE_CODE = 'FREIGHT_CHARGE' AND PAV.LINE_ID = INTERFACE_LINE_ATTRIBUTE6),
                                           0),
                                    5)                                                                                      total,
                                CASE
                                    WHEN     (SELECT mst.TAX_SUBTYPES
                                                FROM prd.atr_E_INVOICE_TAXABLE_SUBTYPES ts
                                               WHERE ts.TAXABLE_CODE = mst.TAX_SUBTYPES) IN ('V009')
                                         AND d.unit_selling_price = 0
                                    THEN
                                        ROUND (
                                            (SELECT ROUND (
                                                          ROUND ((NVL (PAV.ADJUSTED_AMOUNT, 0)) * NVL (ctal.quantity_invoiced, 0), 2)
                                                        * 100
                                                        / 14,
                                                        5)    fre
                                               FROM APPS.OE_PRICE_ADJUSTMENTS_V PAV, AG.EVA_RA_CUSTOMER_TRX_LINES_ALL CTAL
                                              WHERE     PAV.LIST_LINE_TYPE_CODE = 'FREIGHT_CHARGE'
                                                    AND PAV.LINE_ID = CTAL.INTERFACE_LINE_ATTRIBUTE6
                                                    AND NVL (CTAL.UNIT_SELLING_PRICE, 0) = 0
                                                    AND ctal.CUSTOMER_TRX_ID = P_RECEIPT_ID
                                                    AND PAV.LINE_ID(+) = d.INTERFACE_LINE_ATTRIBUTE6),
                                            5)
                                    --   round(nvl(d.unit_standard_price,0) * nvl(d.quantity_invoiced,0),5)
                                    WHEN     ROUND (NVL (TAX_RECOVERABLE, 0), 5) <>
                                             TRUNC ((  NVL (REVENUE_AMOUNT, 0)
                                                     * (  (SELECT ts.TAX_VALUE
                                                             FROM prd.atr_E_INVOICE_TAXABLE_SUBTYPES ts
                                                            WHERE ts.TAXABLE_CODE = mst.TAX_SUBTYPES)
                                                        / 100)),
                                                    2)
                                         AND (SELECT mst.TAX_SUBTYPES
                                                FROM prd.atr_E_INVOICE_TAXABLE_SUBTYPES ts
                                               WHERE ts.TAXABLE_CODE = mst.TAX_SUBTYPES) IN ('V010')
                                    THEN
                                          ROUND (
                                                (  (ROUND (((  UNIT_SELLING_PRICE
                                                             * QUANTITY_INVOICED
                                                             * (  (SELECT ts.TAX_VALUE
                                                                     FROM prd.atr_E_INVOICE_TAXABLE_SUBTYPES ts
                                                                    WHERE ts.TAXABLE_CODE = mst.TAX_SUBTYPES)
                                                                / 100))),
                                                           5))
                                                 - (  (NVL (REVENUE_AMOUNT, 0) + NVL (TAX_RECOVERABLE, 0))
                                                    - ROUND (NVL (UNIT_SELLING_PRICE, 0) * NVL (QUANTITY_INVOICED, 0), 5)))
                                              * (100 / 14),
                                              5)
                                        * -1
                                    ELSE
                                        0
                                END                                                                                         valueDifference,
                                0                                                                                           totalTaxableFees,
                                --nvl(REVENUE_AMOUNT,0) + nvl(TAX_RECOVERABLE,0)
                                ROUND (NVL (REVENUE_AMOUNT, 0), 5)                                                          netTotal,
                                0                                                                                           itemsDiscount,
                                SALES_ORDER,
                                SALES_ORDER_DATE,
                                LINE_TYPE,
                                ROUND (EXTENDED_AMOUNT, 5)                                                                  EXTENDED_AMOUNT,
                                ROUND (LINE_RECOVERABLE, 5)                                                                 LINE_RECOVERABLE,
                                ROUND (TAX_RECOVERABLE, 5),
                                TAX_CLASSIFICATION_CODE
                  FROM AG.EVA_RA_CUSTOMER_TRX_ALL        h,
                       AG.EVA_RA_CUSTOMER_TRX_LINES_ALL  d,
                       mst,
                       CTAL
                 WHERE     h.CUSTOMER_TRX_ID = d.CUSTOMER_TRX_ID
                       AND h.CUSTOMER_TRX_ID = P_RECEIPT_ID
                       AND d.INVENTORY_ITEM_ID = mst.INVENTORY_ITEM_ID
                       AND d.CUSTOMER_TRX_LINE_ID <> 55590039                                                                             --22-05-2024
                       AND LINE_TYPE = 'LINE'
                       AND CTAL.CUSTOMER_TRX_LINE_ID(+) = d.CUSTOMER_TRX_LINE_ID
                       AND d.CUSTOMER_TRX_LINE_ID <> 36084217                                                                             --06/06/2023
                                                             )
        LOOP
            APEX_JSON.open_array ('itemData');
            APEX_JSON.open_object;
            APEX_JSON.write ('internalCode', UPPER (cur_rec.internalCode));
            APEX_JSON.write ('description', UPPER (cur_rec.description));
            APEX_JSON.write ('itemType', UPPER (cur_rec.itemType));
            APEX_JSON.write ('itemCode', UPPER (cur_rec.itemCode));
            APEX_JSON.write ('unitType', UPPER (cur_rec.unitType));
            APEX_JSON.write ('quantity', UPPER (cur_rec.quantity));
            APEX_JSON.write ('unitPrice', UPPER (cur_rec.unitPrice));
            APEX_JSON.write ('netSale', UPPER (cur_rec.netTotal));
            APEX_JSON.write ('totalSale', UPPER (cur_rec.netTotal));
            APEX_JSON.write ('total', UPPER (cur_rec.total));
            -------------------------------------------
            APEX_JSON.open_array ('commercialDiscountData');
            APEX_JSON.open_object;
            --            loop
            APEX_JSON.open_array ('commercialDiscountData');
            APEX_JSON.open_object;
            APEX_JSON.write ('amount', '0');
            APEX_JSON.write ('description', '0');
            APEX_JSON.write ('rate', '0');
            APEX_JSON.close_object;
            APEX_JSON.close_array;
            --            end loop;
            APEX_JSON.close_object;
            APEX_JSON.close_array;
            -------------------------------------------
            APEX_JSON.open_array ('itemDiscountData');
            APEX_JSON.open_object;
            APEX_JSON.open_array ('itemDiscountData');
            APEX_JSON.open_object;
            APEX_JSON.write ('amount', '0');
            APEX_JSON.write ('description', '0');
            APEX_JSON.write ('rate', '0');
            APEX_JSON.close_object;
            APEX_JSON.close_array;
            APEX_JSON.close_object;
            APEX_JSON.close_array;
            -------------------------------------------
            APEX_JSON.open_object ('additionalCommercialDiscount');
            APEX_JSON.write ('amount', '0');
            APEX_JSON.write ('description', '0');
            APEX_JSON.write ('rate', '0');
            APEX_JSON.close_object;
            -------------------------------------------
            APEX_JSON.open_object ('additionalItemDiscount');
            APEX_JSON.write ('amount', '0');
            APEX_JSON.write ('description', '0');
            APEX_JSON.write ('rate', '0');
            APEX_JSON.close_object;
            -------------------------------------------
            APEX_JSON.write ('valueDifference', UPPER (cur_rec.valueDifference));
            -------------------------------------------
            APEX_JSON.open_array ('taxableItems');
            APEX_JSON.open_object;

            FOR tax
                IN (SELECT tax.TAX_RATE_CODE,
                           PERCENTAGE_RATE,
                             d.TAX_RECOVERABLE
                           + NVL ((SELECT ROUND ((NVL (PAV.ADJUSTED_AMOUNT, 0)) * NVL (d.quantity_invoiced, 0), 2)
                                     FROM APPS.OE_PRICE_ADJUSTMENTS_V PAV
                                    WHERE PAV.LIST_LINE_TYPE_CODE = 'FREIGHT_CHARGE' AND PAV.LINE_ID = INTERFACE_LINE_ATTRIBUTE6),
                                  0)    TAX_RECOVERABLE
                      FROM ZX.ZX_RATES_B TAX, AG.EVA_RA_CUSTOMER_TRX_LINES_ALL d
                     WHERE     1 = 1
                           AND NVL (tax.ACTIVE_FLAG, 'Y') = 'Y'
                           AND d.TAX_CLASSIFICATION_CODE = TAX.TAX_RATE_CODE                                   -- and TAX.TAX_RATE_CODE ='PH_AR_P_14%'
                           AND SYSDATE BETWEEN TAX.EFFECTIVE_FROM AND NVL (TAX.EFFECTIVE_TO, SYSDATE + 1)
                           AND d.CUSTOMER_TRX_LINE_ID = cur_rec.CUSTOMER_TRX_LINE_ID)
            LOOP
                SELECT s.TAX_VALUE
                  INTO l_TAX_VALUE
                  FROM prd.atr_E_INVOICE_Taxable_Subtypes s
                 WHERE cur_rec.TAX_SUBTYPES = s.TAXABLE_CODE AND ROWNUM = 1;

                --                APEX_JSON.open_array ('taxableItems');
                --                APEX_JSON.open_object;
                APEX_JSON.open_array ('taxableItems');
                APEX_JSON.open_object;
                APEX_JSON.write ('taxType', NVL (UPPER (cur_rec.TAXABLE_TYPES), '0'));
                APEX_JSON.write (
                    'amount',
                    CASE
                        WHEN MOD (NVL (tax.TAX_RECOVERABLE, 0), 1) = 0 THEN TO_CHAR (NVL (tax.TAX_RECOVERABLE, 0), 'FM9999999990')
                        ELSE TO_CHAR (NVL (tax.TAX_RECOVERABLE, 0), 'FM9999999990.99')
                    END);
                APEX_JSON.write ('subType', NVL (UPPER (cur_rec.TAX_SUBTYPES), '0'));
                APEX_JSON.write ('rate', NVL (UPPER (l_TAX_VALUE), '0'));
                --                APEX_JSON.close_object;
                --                APEX_JSON.close_array;
                APEX_JSON.close_object;
                APEX_JSON.close_array;
            END LOOP;

            APEX_JSON.close_object;
            APEX_JSON.close_array;

            -------------------------------------------
            APEX_JSON.close_object;
            APEX_JSON.close_array;
        END LOOP;

        APEX_JSON.close_object;
        APEX_JSON.close_array;

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------
        WITH
            FR
            AS
                (SELECT ROUND ((NVL (PAV.ADJUSTED_AMOUNT, 0)) * NVL (ctal.quantity_invoiced, 0), 2) fre, PAV.LINE_ID
                   FROM APPS.OE_PRICE_ADJUSTMENTS_V PAV, AG.EVA_RA_CUSTOMER_TRX_LINES_ALL CTAL
                  WHERE     PAV.LIST_LINE_TYPE_CODE = 'FREIGHT_CHARGE'
                        AND PAV.LINE_ID = CTAL.INTERFACE_LINE_ATTRIBUTE6
                        AND NVL (CTAL.UNIT_SELLING_PRICE, 0) = 0
                        AND ctal.CUSTOMER_TRX_ID = P_RECEIPT_ID)
        SELECT ROUND (SUM (NVL (REVENUE_AMOUNT, 0)), 2)                                                 total_inv,
               ROUND (SUM (NVL (TAX_RECOVERABLE, 0)), 2)                                                total_tax,
               ROUND (SUM (NVL (REVENUE_AMOUNT, 0)), 2) + ROUND (SUM (NVL (TAX_RECOVERABLE, 0)), 2)     total_invoice
          INTO l_total_sales_invoice, l_total_tax, l_total_invoice
          FROM (SELECT NVL (REVENUE_AMOUNT, 0) REVENUE_AMOUNT, NVL (TAX_RECOVERABLE, 0) + NVL (fr.fre, 0) TAX_RECOVERABLE
                  --          INTO l_total_sales_invoice, l_total_tax, l_total_invoice
                  FROM AG.EVA_RA_CUSTOMER_TRX_ALL h, AG.EVA_RA_CUSTOMER_TRX_LINES_ALL d, FR
                 WHERE     h.CUSTOMER_TRX_ID = d.CUSTOMER_TRX_ID
                       AND h.CUSTOMER_TRX_ID = P_RECEIPT_ID
                       AND LINE_TYPE = 'LINE'
                       AND FR.LINE_ID(+) = d.INTERFACE_LINE_ATTRIBUTE6);

        APEX_JSON.write ('totalSales', UPPER (l_total_sales_invoice));
        APEX_JSON.write ('totalCommercialDiscount', '0');
        APEX_JSON.write ('totalItemsDiscount', '0');

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------

        APEX_JSON.open_array ('extraReceiptDiscountData');
        APEX_JSON.open_object;
        APEX_JSON.open_array ('extraReceiptDiscountData');
        APEX_JSON.open_object;
        APEX_JSON.write ('amount', '0');
        APEX_JSON.write ('description', '0');
        APEX_JSON.write ('rate', '0');
        APEX_JSON.close_object;
        APEX_JSON.close_array;
        APEX_JSON.close_object;
        APEX_JSON.close_array;

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------

        APEX_JSON.write ('netAmount', UPPER (l_total_sales_invoice));
        APEX_JSON.write ('feesAmount', '0');
        APEX_JSON.write ('totalAmount', UPPER (l_total_invoice));

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------

        APEX_JSON.open_array ('taxTotals');
        APEX_JSON.open_object;
        APEX_JSON.open_array ('taxTotals');
        APEX_JSON.open_object;
        APEX_JSON.write ('taxType', 'T1');
        APEX_JSON.write ('amount', NVL (UPPER (l_total_tax), '0'));
        APEX_JSON.close_object;
        APEX_JSON.close_array;
        APEX_JSON.close_object;
        APEX_JSON.close_array;

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------

        APEX_JSON.write ('paymentMethod', 'V');
        APEX_JSON.write ('adjustment', '0');

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------

        APEX_JSON.open_object ('contractor');
        APEX_JSON.write ('name', '0');
        APEX_JSON.write ('amount', '0');
        APEX_JSON.write ('rate', '0');
        APEX_JSON.close_object;

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------

        APEX_JSON.open_object ('beneficiary');
        APEX_JSON.write ('amount', '0');
        APEX_JSON.write ('rate', '0');
        APEX_JSON.close_object;

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------
        --        APEX_JSON.close_object;
        APEX_JSON.close_object;
        L_json_2                := apex_json.get_clob_output;
        L_json_2                := REPLACE (L_json_2, '"uuid":" "', '"uuid":""');
        --        L_json_2               := REPLACE (L_json_2, '"previousUUID":" "', '"previousUUID":""');
        L_json_2                := REPLACE (L_json_2, '"referenceOldUUID":" "', '"referenceOldUUID":""');
        L_json_2                := REPLACE (L_json_2, '"id":" "', '"id":""');

        --        dbms_output.put_line(L_json_2);

        SELECT JSON_QUERY (L_json_2, '$' RETURNING CLOB) INTO l_body_2 FROM DUAL;


        l_json_for_serialize    := l_body_2;
        obj                     := l_body;

        --        DBMS_OUTPUT.put_line ('for serialize' || l_json_for_serialize);
        --        DBMS_OUTPUT.put_line ('for send' || obj);

        SELECT TO_CLOB (
                   UPPER (
                       REPLACE (REPLACE (REPLACE (REPLACE (REPLACE ((SELECT l_json_for_serialize FROM DUAL), '{', ''), '}', ''), ',', ''), '[', ''),
                                ']',
                                '')))
          INTO l_serialization
          FROM DUAL;


        SELECT DBMS_LOB.SUBSTR (l_serialization, 4000, '50') INTO l_after_time FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (l_serialization, 4000, '4050') INTO l_after_time_2 FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (l_serialization, 4000, '8050') INTO l_after_time_3 FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (l_serialization, 4000, '12050') INTO l_after_time_4 FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (l_serialization, 4000, '16050') INTO l_after_time_5 FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (l_serialization, 4000, '20050') INTO l_after_time_6 FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (l_serialization, 4000, '24050') INTO l_after_time_7 FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (l_serialization, 4000, '28050') INTO l_after_time_8 FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (l_serialization, 4000, '32050') INTO l_after_time_9 FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (l_serialization, 4000, '36050') INTO l_after_time_10 FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (l_serialization, 26, '1') INTO l_before_time FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (l_serialization, 23, '27') INTO l_time FROM DUAL;

        SELECT    REPLACE (l_before_time, ':', '')
               || l_time
               || REPLACE (l_after_time, ':', '')
               || REPLACE (l_after_time_2, ':', '')
               || REPLACE (l_after_time_3, ':', '')
               || REPLACE (l_after_time_4, ':', '')
               || REPLACE (l_after_time_5, ':', '')
               || REPLACE (l_after_time_6, ':', '')
               || REPLACE (l_after_time_7, ':', '')
               || REPLACE (l_after_time_8, ':', '')
               || REPLACE (l_after_time_9, ':', '')
               || REPLACE (l_after_time_10, ':', '')
          INTO l_final_serialization
          FROM DUAL;

        l_final_serialization   := REPLACE (l_final_serialization, 'إ', 'ا');


        SELECT sys.DBMS_CRYPTO.hash (src => (l_final_serialization), typ => 4) INTO l_hash FROM DUAL;

        SELECT DBMS_LOB.INSTR (obj, 'uuid') + 6 INTO l_instr_1 FROM DUAL;

        SELECT DBMS_LOB.INSTR (obj, 'uuid') + 7 INTO l_instr_2 FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (l_serialization, 4000, l_instr_2) INTO l_substr FROM DUAL;


        SELECT DBMS_LOB.SUBSTR (obj, l_instr_1, 1) INTO f_json FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (obj, 18, l_instr_2) INTO last_json FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (obj, 4000, 121) INTO l_last_json FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (obj, 4000, 4121) INTO l_last_json_2 FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (obj, 4000, 8121) INTO l_last_json_3 FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (obj, 4000, 12121) INTO l_last_json_4 FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (obj, 4000, 16121) INTO l_last_json_5 FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (obj, 4000, 20121) INTO l_last_json_6 FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (obj, 4000, 24121) INTO l_last_json_7 FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (obj, 4000, 28121) INTO l_last_json_8 FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (obj, 4000, 32121) INTO l_last_json_9 FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (obj, 4000, 36121) INTO l_last_json_10 FROM DUAL;



        SELECT    f_json
               || l_hash
               || last_json
               || l_last_json
               || l_last_json_2
               || l_last_json_3
               || l_last_json_4
               || l_last_json_5
               || l_last_json_6
               || l_last_json_7
               || l_last_json_8
               || l_last_json_9
               || l_last_json_10
          INTO l_final_json
          FROM DUAL;

        l_final_json            := REPLACE (l_final_json, 'إ', 'ا');


        SELECT '"' || REPLACE ((l_final_json), '"', '\"') || '"' INTO l_body_wo_sign FROM DUAL;

        --        SELECT SUBSTR(l_body_wo_sign, 1, LENGTH(l_body_wo_sign) - 2) into l_try FROM dual;

        --        SELECT SUBSTR(l_body_wo_sign, 1, LENGTH(l_body_wo_sign) - 3) || SUBSTR(l_body_wo_sign, LENGTH(l_body_wo_sign)) into l_try FROM dual;

        SELECT    SUBSTR (l_body_wo_sign, 1, 1)
               || SUBSTR (l_body_wo_sign, 17, LENGTH (l_body_wo_sign) - 19)
               || SUBSTR (l_body_wo_sign, LENGTH (l_body_wo_sign))
          INTO l_try
          FROM DUAL;


        DBMS_OUTPUT.put_line ('uuid' || l_hash);

        get_invoice_signature (l_final_json,
                               P_server,
                               l_response,
                               l_out_signature);



        SELECT SUBSTR (REGEXP_SUBSTR (l_response, 'uuid.*",'), 8, REGEXP_INSTR (REGEXP_SUBSTR (l_response, 'uuid.*",'), '",') - 8)     uuid
          INTO l_uuid
          FROM DUAL;

        --
        --
        l_url_API               := get_url (P_server, 'API') || '/api/v1/receiptsubmissions';

        --          l_response :=
        --            apex_web_service.make_rest_request (
        --                p_url           => l_url_API,
        --                p_http_method   => 'POST',
        --                p_body          => l_final_json,
        --                p_wallet_path   => get_wallet_path,
        --                p_wallet_pwd    => get_wallet_pwd );
        --        /* Parsing Webservice Response as JSON */
        ----        apex_json.parse (l_response);
        --        SELECT SUBSTR (
        --                   REGEXP_SUBSTR (l_response, 'uuid.*",'),
        --                   8,
        --                     REGEXP_INSTR (REGEXP_SUBSTR (l_response, 'uuid.*",'),
        --                                   '",')
        --                   - 8)    uuid
        --          INTO l_uuid
        --          FROM DUAL;



        --dbms_output.put_line('uuid'||l_uuid);

        l_debug_result_id       := PRD.ATR_E_RECEIPT_DEBUG_RESULT_SEQ.NEXTVAL;

        --l_url_API   := get_url (P_server, 'API') || '/api/v1/receipts/:submissionUuid/details';


        INSERT INTO PRD.ATR_E_RECEIPT_DEBUG_RESULT (DEBUG_RESULT_ID,
                                                    URL,
                                                    STATUS_CODE,
                                                    WEB_SERVICE_NAME,
                                                    WEB_SERVICE_METHOD,
                                                    DEBUG_RESULT,
                                                    JSON_WITHOUT_SIGNATURE,
                                                    NODE_NAME,
                                                    CREATION_DATE,
                                                    CREATED_BY,
                                                    LAST_UPDATE_BY,
                                                    LAST_UPDATED_DATE,
                                                    SERIALIZATION,
                                                    Final_JSON,
                                                    UUID,
                                                    JSON_WITH_SIGNATURE,
                                                    response)
             VALUES (l_debug_result_id,
                     l_url_API,
                     apex_web_service.g_status_code,
                     '5.1 Submit Documents (JSON)',
                     'POST',
                     l_response,
                     l_body,
                     --                     l_out_signature,
                     P_server,
                     SYSDATE,
                     P_PERSON_ID,
                     P_PERSON_ID,
                     SYSDATE,
                     l_final_serialization,
                     l_final_json,
                     l_hash,
                     l_out_signature,
                     l_get_response_f);

        COMMIT;

        SELECT CASE WHEN JSON_VALUE (debug_result, '$.rejectedDocuments.size()') = 0 THEN 'valid' ELSE 'invalid' END
          INTO l_status
          FROM PRD.ATR_E_RECEIPT_DEBUG_RESULT
         WHERE debug_result_id = l_debug_result_id;

        INSERT INTO PRD.ATR_E_RECEIPT_HISTORY (DEBUG_RESULT_ID,
                                               INVOICE_ID,
                                               INVOICE_NUMBER,
                                               UUID,
                                               typeName,
                                               status,
                                               NODE_NAME,
                                               CREATION_DATE,
                                               CREATED_BY,
                                               LAST_UPDATE_BY,
                                               LAST_UPDATED_DATE)
             VALUES (l_debug_result_id,
                     P_RECEIPT_ID,
                     l_TRX_NUMBER,
                     l_uuid,
                     'I',
                     l_status,
                     P_server,
                     SYSDATE,
                     P_PERSON_ID,
                     P_PERSON_ID,
                     SYSDATE);

        COMMIT;
    END Submit_Documents_JSON;

    PROCEDURE Submit_Documents_credit (P_RECEIPT_ID IN NUMBER, P_PERSON_ID IN NUMBER, P_server IN VARCHAR2)
    AS
        l_url_API                 VARCHAR2 (4000);
        l_token                   VARCHAR (32000);
        l_TRX_DATE                VARCHAR (2000) := TO_CHAR (SYSDATE - (3 / 24), 'YYYY-MM-DD"T"HH24:MI:SS"Z"');
        l_TRX_NUMBER              VARCHAR (32000);
        l_BILL_TO_CUSTOMER_ID     NUMBER;
        L_CURRENCY                VARCHAR2 (40);
        L_EXCHANGE_RATE           NUMBER;
        l_BILL_TO_SITE_USE_ID     NUMBER;
        l_total_sales_invoice     NUMBER;
        l_total_tax               NUMBER;
        l_total_invoice           NUMBER;
        l_body                    CLOB;
        l_json                    CLOB;
        l_body_2                  CLOB;
        l_json_2                  CLOB;
        l_out_signature           CLOB;
        l_response                CLOB;
        l_get_response            CLOB;
        l_get_response_f          CLOB;
        l_TAX_VALUE               NUMBER;
        l_uuid                    VARCHAR (2000);
        l_SERIALZE                CLOB;
        l_serialize_inv           CLOB;
        l_amount                  VARCHAR2 (100);
        obj                       CLOB;
        l_hash                    RAW (5000);
        l_instr_1                 NUMBER;
        l_after_time              CLOB;
        l_after_time_2            CLOB;
        l_after_time_3            CLOB;
        l_after_time_4            CLOB;
        l_after_time_5            CLOB;
        l_after_time_6            CLOB;
        l_after_time_7            CLOB;
        l_after_time_8            CLOB;
        l_after_time_9            CLOB;
        l_after_time_10           CLOB;
        l_before_time             CLOB;
        l_final_serialization     CLOB;
        l_final_serialization_2   CLOB;
        l_time                    VARCHAR (6000);
        l_instr_2                 VARCHAR (32000);
        l_instr_3                 VARCHAR (32000);
        l_substr                  VARCHAR (6000);
        l_substr_1                VARCHAR (10000);
        l_serialization           CLOB;
        l_json_for_serialize      CLOB;
        last_json                 CLOB;
        f_json                    CLOB;
        l_last_json               CLOB;
        l_last_json_2             CLOB;
        l_last_json_3             CLOB;
        l_last_json_4             CLOB;
        l_last_json_5             CLOB;
        l_last_json_6             CLOB;
        l_last_json_7             CLOB;
        l_last_json_8             CLOB;
        l_last_json_9             CLOB;
        l_last_json_10            CLOB;
        l_final_json              CLOB;
        LAST_UUID                 VARCHAR2 (2000);
        l_debug_result_id         NUMBER;
        l_body_wo_sign            CLOB;
        l_try                     CLOB;
        l_success                 BOOLEAN := FALSE;
        l_status                  VARCHAR2 (10000);
        l_reference_trx_id        VARCHAR2 (1000);
        L_REFERENCE_UUID          VARCHAR2 (1000);
    BEGIN
        --        l_url_API   := get_url (P_server, 'API') || '/api/v1/receiptsubmissions/:submissionUuid/details?';


        SELECT json_value (prd.atr_electronic_receipt.Login_as_Taxpayer_System (P_server), '$.access_token') INTO l_token FROM DUAL;

        SELECT APPLIED_CUSTOMER_TRX_ID
          INTO l_reference_trx_id
          FROM apps.AR_RECEIVABLE_APPLICATIONS_ALL
         WHERE CUSTOMER_TRX_ID = P_RECEIPT_ID;

        SELECT DISTINCT his.uuid
          INTO L_REFERENCE_UUID
          FROM PRD.ATR_E_RECEIPT_HISTORY his
         WHERE his.invoice_id = l_reference_trx_id AND his.uuid IS NOT NULL;


        APEX_JSON.initialize_clob_output;
        APEX_JSON.open_object;
        APEX_JSON.open_array ('receipts');
        APEX_JSON.open_object;

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------


        APEX_JSON.open_object ('header');

        SELECT h.TRX_NUMBER,
               h.BILL_TO_CUSTOMER_ID,
               H.INVOICE_CURRENCY_CODE,
               H.EXCHANGE_RATE,
               h.BILL_TO_SITE_USE_ID                                                                                                               --,
          --TO_CHAR (SYSDATE - (3 / 24), 'YYYY-MM-DD"T"HH24:MI:SS"Z"')     inv_date
          --case when h.ATTRIBUTE11 = '0999' then nvl (h.PURCHASE_ORDER,0) else '0' end   PURCHASE_ORDER
          INTO l_TRX_NUMBER,
               l_BILL_TO_CUSTOMER_ID,
               L_CURRENCY,
               L_EXCHANGE_RATE,
               l_BILL_TO_SITE_USE_ID                                                                                                               --,
          --l_TRX_DATE
          --      L_PURCHASE
          FROM AG.EVA_RA_CUSTOMER_TRX_ALL h
         WHERE 1 = 1 AND h.CUSTOMER_TRX_ID = P_RECEIPT_ID;

        SELECT UUID
          INTO LAST_UUID
          FROM PRD.ATR_E_RECEIPT_DEBUG_RESULT
         WHERE DEBUG_RESULT_ID = (SELECT MAX (DEBUG_RESULT_ID) FROM PRD.ATR_E_RECEIPT_DEBUG_RESULT);

        --          SELECT ''
        --          INTO LAST_UUID
        --          FROM dual;

        APEX_JSON.write ('dateTimeIssued', l_TRX_DATE);
        APEX_JSON.write ('receiptNumber', l_TRX_NUMBER);
        APEX_JSON.write ('uuid', ' ');
        APEX_JSON.write ('previousUUID', LAST_UUID);
        APEX_JSON.write ('referenceUUID', L_REFERENCE_UUID);
        APEX_JSON.write ('referenceOldUUID', ' ');
        APEX_JSON.write ('currency', UPPER (L_CURRENCY));
        APEX_JSON.write ('exchangeRate', L_EXCHANGE_RATE);
        APEX_JSON.write ('sOrderNameCode', '0');
        APEX_JSON.write ('orderdeliveryMode', 'FC');
        APEX_JSON.write ('grossWeight', 0);
        APEX_JSON.write ('netWeight', 0);
        APEX_JSON.close_object;
        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------

        APEX_JSON.open_object ('documentType');
        APEX_JSON.write ('receiptType', 'r');
        APEX_JSON.write ('typeVersion', '1.2');
        APEX_JSON.close_object;

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------

        APEX_JSON.open_object ('seller');
        APEX_JSON.write ('rin', '484380486');
        APEX_JSON.write ('companyTradeName', 'اخناتون للتجارة والتوزيع');
        APEX_JSON.write ('branchCode', '0');
        -------------------------------------------
        APEX_JSON.open_object ('branchAddress');
        APEX_JSON.write ('country', 'EG');
        APEX_JSON.write ('governate', 'EGYPT');
        APEX_JSON.write ('regionCity', 'EGYPT');
        APEX_JSON.write ('street', 'GIZA');
        APEX_JSON.write ('buildingNumber', '13');
        APEX_JSON.write ('postalCode', '12311');
        APEX_JSON.write ('floor', '0');
        APEX_JSON.write ('room', '0');
        APEX_JSON.write ('landmark', '0');
        APEX_JSON.write ('additionalInformation', '0');
        APEX_JSON.close_object;
        -------------------------------------------
        APEX_JSON.write ('deviceSerialNumber', 'TRF4340ZS5');
        APEX_JSON.write ('syndicateLicenseNumber', '0');
        APEX_JSON.write ('activityCode', '4772');
        APEX_JSON.close_object;


        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------

        APEX_JSON.open_object ('buyer');

        FOR Buyer IN (SELECT h.CUST_ACCOUNT_ID,
                             SITE_USES.SITE_USE_ID,
                             CASE WHEN h.ATTRIBUTE11 IS NOT NULL THEN 'B' ELSE 'P' END    TYPE,
                             --h.ACCOUNT_NUMBER id,
                             0                                                            id,
                             -- loc.CITY                                                     id,
                             (SELECT DISTINCT h.ACCOUNT_NAME
                                FROM ONT.OE_ORDER_HEADERS_ALL    soh,
                                     AG.EVA_RA_CUSTOMER_TRX_ALL  CT,
                                     apps.HZ_CUST_SITE_USES_ALL  SITE_USES,
                                     apps.HZ_CUST_ACCOUNTS       h
                               WHERE     CT.CT_REFERENCE = SOH.ORDER_NUMBER
                                     AND CT.BILL_TO_CUSTOMER_ID = H.CUST_ACCOUNT_ID
                                     AND SOH.ORG_ID = 1963
                                     AND SOH.ORG_ID = CT.ORG_ID
                                     AND CT.BILL_TO_SITE_USE_ID = SITE_USES.SITE_USE_ID
                                     AND H.CUST_ACCOUNT_ID = l_BILL_TO_CUSTOMER_ID
                                     AND SITE_USES.SITE_USE_ID = l_BILL_TO_SITE_USE_ID
                                     AND CT.TRX_NUMBER = l_TRX_NUMBER
                                     AND SOH.ATTRIBUTE18 IS NOT NULL)                     name,
                             loc.COUNTRY                                                  country,
                             'Egypt'                                                      governate,
                             --                       'Egypt'                                regioncity,
                             --                       'Cairo - Egypt'                        street,
                             loc.ADDRESS1                                                 regionCity,
                             loc.ADDRESS1                                                 street,
                             ''                                                           buildingNumber,
                             ''                                                           postalCode,
                             ''                                                           FLOOR,
                             ''                                                           room,
                             ''                                                           landmark,
                             ''                                                           additionalInformation
                        FROM apps.HZ_CUST_ACCOUNTS        h,
                             apps.hz_parties              HP,
                             APPS.HZ_LOCATIONS            loc,
                             APPS.HZ_PARTY_SITES          party_sites,
                             apps.HZ_CUST_ACCT_SITES_ALL  ACCT_SITES,
                             APPS.HZ_CUST_ACCOUNTS_ALL    CUST_ACCOUNTS,
                             apps.HZ_CUST_SITE_USES_ALL   SITE_USES,
                             APPS.FND_FLEX_VALUES_VL      FLEX
                       WHERE     loc.LOCATION_ID = party_sites.LOCATION_ID
                             AND ACCT_SITES.PARTY_SITE_ID = party_sites.PARTY_SITE_ID
                             AND h.party_id = hp.party_id
                             AND HP.party_id = party_sites.party_id
                             AND CUST_ACCOUNTS.CUST_ACCOUNT_ID = ACCT_SITES.CUST_ACCOUNT_ID
                             AND SITE_USES.CUST_ACCT_SITE_ID = ACCT_SITES.CUST_ACCT_SITE_ID
                             /*****Updated by Mareham*****/
                             AND FLEX.FLEX_VALUE_SET_ID(+) = 1018193
                             AND FLEX.ENABLED_FLAG = 'Y'
                             AND FLEX.ATTRIBUTE3 = 'EG'
                             AND HP.PROVINCE = FLEX.FLEX_VALUE
                             /*************************/
                             --                       AND FLEX.FLEX_VALUE_SET_ID(+) = 1022025
                             --                       AND party_sites.ATTRIBUTE2 =
                             --                           FLEX.FLEX_VALUE_MEANING(+)
                             AND h.CUST_ACCOUNT_ID = CUST_ACCOUNTS.CUST_ACCOUNT_ID
                             AND h.CUST_ACCOUNT_ID IN (1836040,
                                                       2468432,
                                                       1339188,
                                                       2519757,
                                                       2596516,
                                                       2658528)
                             AND CUST_ACCOUNTS.CUST_ACCOUNT_ID = l_BILL_TO_CUSTOMER_ID
                             AND SITE_USES.SITE_USE_ID = l_BILL_TO_SITE_USE_ID)
        LOOP
            APEX_JSON.write ('type', 'P');
            APEX_JSON.write ('id', ' ');
            APEX_JSON.write ('name', UPPER (Buyer.name));
            APEX_JSON.write ('mobileNumber', '0');
            APEX_JSON.write ('paymentNumber', '0');
            APEX_JSON.close_object;
        END LOOP;

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------
        APEX_JSON.open_array ('itemData');

        FOR cur_rec
            IN (WITH
                    mst
                    AS
                        (SELECT NVL (EGS_ITEM_CODE, i.segment1)          item_code,
                                i.segment1                               internalCode,
                                i.INVENTORY_ITEM_ID,
                                NVL (UOM, i.PRIMARY_UNIT_OF_MEASURE)     uom,
                                TAXABLE_TYPES,
                                TAX_SUBTYPES
                           FROM APPS.MTL_SYSTEM_ITEMS_FVL i, prd.ATR_ELECTRONIC_INVOICE_MAPPING_ITEMS MAP_ITEM
                          WHERE i.organization_id = 1964 AND MAP_ITEM.INVENTORY_ITEM_ID(+) = i.INVENTORY_ITEM_ID               -- AND item_type = 'FG'
                                                                                                                ),
                    CTAL
                    AS
                        (SELECT NVL (ctal.UNIT_STANDARD_PRICE, 0) * NVL (ctal.QUANTITY_INVOICED, 0) PRICE, ctal.CUSTOMER_TRX_LINE_ID
                           FROM AG.EVA_RA_CUSTOMER_TRX_LINES_ALL ctal
                          WHERE NVL (ctal.UNIT_SELLING_PRICE, 0) = 0)
                SELECT DISTINCT d.CUSTOMER_TRX_LINE_ID,
                                h.CUSTOMER_TRX_ID,
                                LINE_NUMBER,
                                h.EXCHANGE_RATE,
                                h.INVOICE_CURRENCY_CODE,
                                d.INVENTORY_ITEM_ID,
                                --DESCRIPTION description,
                                REGEXP_REPLACE (DESCRIPTION, '"')                                                           description,
                                'EGS'                                                                                       itemType,
                                'EG-484380486-' || mst.item_code                                                            itemCode,
                                mst.internalCode                                                                            internalCode,
                                mst.TAXABLE_TYPES                                                                           TAXABLE_TYPES,
                                CASE WHEN TAX_CLASSIFICATION_CODE = 'INPUT S_T 0%' THEN 'V003' ELSE MST.TAX_SUBTYPES END    TAX_SUBTYPES,
                                mst.uom                                                                                     unitType,
                                ABS (QUANTITY_CREDITED)                                                                     quantity,
                                ROUND (NVL (UNIT_SELLING_PRICE, 0), 5)                                                      unitPrice,
                                ROUND (NVL (REVENUE_AMOUNT, 0), 5)                                                          salesTotal,
                                ROUND (
                                      NVL (REVENUE_AMOUNT, 0)
                                    + NVL (TAX_RECOVERABLE, 0)
                                    + NVL ((SELECT ROUND ((NVL (PAV.ADJUSTED_AMOUNT, 0)) * NVL (d.quantity_invoiced, 0), 2)
                                              FROM APPS.OE_PRICE_ADJUSTMENTS_V PAV
                                             WHERE PAV.LIST_LINE_TYPE_CODE = 'FREIGHT_CHARGE' AND PAV.LINE_ID = INTERFACE_LINE_ATTRIBUTE6),
                                           0),
                                    5)                                                                                      total,
                                CASE
                                    WHEN     (SELECT mst.TAX_SUBTYPES
                                                FROM prd.atr_E_INVOICE_TAXABLE_SUBTYPES ts
                                               WHERE ts.TAXABLE_CODE = mst.TAX_SUBTYPES) IN ('V009')
                                         AND d.unit_selling_price = 0
                                    THEN
                                        ROUND (
                                            (SELECT ROUND (
                                                          ROUND ((NVL (PAV.ADJUSTED_AMOUNT, 0)) * NVL (ctal.quantity_invoiced, 0), 2)
                                                        * 100
                                                        / 14,
                                                        5)    fre
                                               FROM APPS.OE_PRICE_ADJUSTMENTS_V PAV, AG.EVA_RA_CUSTOMER_TRX_LINES_ALL CTAL
                                              WHERE     PAV.LIST_LINE_TYPE_CODE = 'FREIGHT_CHARGE'
                                                    AND PAV.LINE_ID = CTAL.INTERFACE_LINE_ATTRIBUTE6
                                                    AND NVL (CTAL.UNIT_SELLING_PRICE, 0) = 0
                                                    AND ctal.CUSTOMER_TRX_ID = P_RECEIPT_ID
                                                    AND PAV.LINE_ID(+) = d.INTERFACE_LINE_ATTRIBUTE6),
                                            5)
                                    --   round(nvl(d.unit_standard_price,0) * nvl(d.quantity_invoiced,0),5)
                                    WHEN     ROUND (NVL (TAX_RECOVERABLE, 0), 5) <>
                                             TRUNC ((  NVL (REVENUE_AMOUNT, 0)
                                                     * (  (SELECT ts.TAX_VALUE
                                                             FROM prd.atr_E_INVOICE_TAXABLE_SUBTYPES ts
                                                            WHERE ts.TAXABLE_CODE = mst.TAX_SUBTYPES)
                                                        / 100)),
                                                    2)
                                         AND (SELECT mst.TAX_SUBTYPES
                                                FROM prd.atr_E_INVOICE_TAXABLE_SUBTYPES ts
                                               WHERE ts.TAXABLE_CODE = mst.TAX_SUBTYPES) IN ('V010')
                                    THEN
                                          ROUND (
                                                (  (ROUND (((  UNIT_SELLING_PRICE
                                                             * QUANTITY_INVOICED
                                                             * (  (SELECT ts.TAX_VALUE
                                                                     FROM prd.atr_E_INVOICE_TAXABLE_SUBTYPES ts
                                                                    WHERE ts.TAXABLE_CODE = mst.TAX_SUBTYPES)
                                                                / 100))),
                                                           5))
                                                 - (  (NVL (REVENUE_AMOUNT, 0) + NVL (TAX_RECOVERABLE, 0))
                                                    - ROUND (NVL (UNIT_SELLING_PRICE, 0) * NVL (QUANTITY_INVOICED, 0), 5)))
                                              * (100 / 14),
                                              5)
                                        * -1
                                    ELSE
                                        0
                                END                                                                                         valueDifference,
                                0                                                                                           totalTaxableFees,
                                --nvl(REVENUE_AMOUNT,0) + nvl(TAX_RECOVERABLE,0)
                                ROUND (NVL (REVENUE_AMOUNT, 0), 5)                                                          netTotal,
                                0                                                                                           itemsDiscount,
                                SALES_ORDER,
                                SALES_ORDER_DATE,
                                LINE_TYPE,
                                ROUND (EXTENDED_AMOUNT, 5)                                                                  EXTENDED_AMOUNT,
                                ROUND (LINE_RECOVERABLE, 5)                                                                 LINE_RECOVERABLE,
                                ROUND (TAX_RECOVERABLE, 5),
                                TAX_CLASSIFICATION_CODE
                  FROM AG.EVA_RA_CUSTOMER_TRX_ALL        h,
                       AG.EVA_RA_CUSTOMER_TRX_LINES_ALL  d,
                       mst,
                       CTAL
                 WHERE     h.CUSTOMER_TRX_ID = d.CUSTOMER_TRX_ID
                       AND h.CUSTOMER_TRX_ID = P_RECEIPT_ID
                       AND d.INVENTORY_ITEM_ID = mst.INVENTORY_ITEM_ID
                       AND d.CUSTOMER_TRX_LINE_ID <> 55590039                                                                             --22-05-2024
                       AND LINE_TYPE = 'LINE'
                       AND CTAL.CUSTOMER_TRX_LINE_ID(+) = d.CUSTOMER_TRX_LINE_ID
                       AND d.CUSTOMER_TRX_LINE_ID <> 36084217                                                                             --06/06/2023
                                                             )
        LOOP
            APEX_JSON.open_object;
            APEX_JSON.write ('internalCode', UPPER (cur_rec.internalCode));
            APEX_JSON.write ('description', UPPER (cur_rec.description));
            APEX_JSON.write ('itemType', UPPER (cur_rec.itemType));
            APEX_JSON.write ('itemCode', UPPER (cur_rec.itemCode));
            APEX_JSON.write ('unitType', UPPER (cur_rec.unitType));
            APEX_JSON.write ('quantity', NVL (cur_rec.quantity, 0));
            APEX_JSON.write ('unitPrice', cur_rec.unitPrice);
            APEX_JSON.write ('netSale', ABS (cur_rec.netTotal));
            APEX_JSON.write ('totalSale', ABS (cur_rec.netTotal));
            APEX_JSON.write ('total', ABS (cur_rec.total));
            -------------------------------------------
            APEX_JSON.open_array ('commercialDiscountData');
            APEX_JSON.open_object;
            APEX_JSON.write ('amount', 0);
            APEX_JSON.write ('description', '0');
            APEX_JSON.write ('rate', 0);
            APEX_JSON.close_object;
            APEX_JSON.close_array;
            -------------------------------------------
            APEX_JSON.open_array ('itemDiscountData');
            APEX_JSON.open_object;
            APEX_JSON.write ('amount', 0);
            APEX_JSON.write ('description', '0');
            APEX_JSON.write ('rate', 0);
            APEX_JSON.close_object;
            APEX_JSON.close_array;
            -------------------------------------------
            APEX_JSON.open_object ('additionalCommercialDiscount');
            APEX_JSON.write ('amount', 0);
            APEX_JSON.write ('description', '0');
            APEX_JSON.write ('rate', 0);
            APEX_JSON.close_object;
            -------------------------------------------
            APEX_JSON.open_object ('additionalItemDiscount');
            APEX_JSON.write ('amount', 0);
            APEX_JSON.write ('description', '0');
            APEX_JSON.write ('rate', 0);
            APEX_JSON.close_object;
            -------------------------------------------
            APEX_JSON.write ('valueDifference', cur_rec.valueDifference);
            -------------------------------------------

            APEX_JSON.open_array ('taxableItems');

            FOR tax
                IN (SELECT tax.TAX_RATE_CODE,
                           PERCENTAGE_RATE,
                             d.TAX_RECOVERABLE
                           + NVL ((SELECT ROUND ((NVL (PAV.ADJUSTED_AMOUNT, 0)) * NVL (d.quantity_invoiced, 0), 2)
                                     FROM APPS.OE_PRICE_ADJUSTMENTS_V PAV
                                    WHERE PAV.LIST_LINE_TYPE_CODE = 'FREIGHT_CHARGE' AND PAV.LINE_ID = INTERFACE_LINE_ATTRIBUTE6),
                                  0)    TAX_RECOVERABLE
                      FROM ZX.ZX_RATES_B TAX, AG.EVA_RA_CUSTOMER_TRX_LINES_ALL d
                     WHERE     1 = 1
                           AND NVL (tax.ACTIVE_FLAG, 'Y') = 'Y'
                           AND d.TAX_CLASSIFICATION_CODE = TAX.TAX_RATE_CODE
                           AND SYSDATE BETWEEN TAX.EFFECTIVE_FROM AND NVL (TAX.EFFECTIVE_TO, SYSDATE + 1)
                           AND d.CUSTOMER_TRX_LINE_ID = cur_rec.CUSTOMER_TRX_LINE_ID)
            LOOP
                SELECT s.TAX_VALUE
                  INTO l_TAX_VALUE
                  FROM prd.atr_E_INVOICE_Taxable_Subtypes s
                 WHERE cur_rec.TAX_SUBTYPES = s.TAXABLE_CODE AND ROWNUM = 1;

                APEX_JSON.open_object;
                APEX_JSON.write ('taxType', NVL (UPPER (cur_rec.TAXABLE_TYPES), '0'));
                APEX_JSON.write ('amount', NVL ((tax.TAX_RECOVERABLE), 0));
                APEX_JSON.write ('subType', NVL (UPPER (cur_rec.TAX_SUBTYPES), '0'));
                APEX_JSON.write ('rate', NVL (l_TAX_VALUE, 0));
                APEX_JSON.close_object;
            END LOOP;

            APEX_JSON.close_array;

            -------------------------------------------
            APEX_JSON.close_object;
        END LOOP;

        APEX_JSON.close_array;

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------
        WITH
            FR
            AS
                (SELECT ROUND ((NVL (PAV.ADJUSTED_AMOUNT, 0)) * NVL (ctal.quantity_invoiced, 0), 2) fre, PAV.LINE_ID
                   FROM APPS.OE_PRICE_ADJUSTMENTS_V PAV, AG.EVA_RA_CUSTOMER_TRX_LINES_ALL CTAL
                  WHERE     PAV.LIST_LINE_TYPE_CODE = 'FREIGHT_CHARGE'
                        AND PAV.LINE_ID = CTAL.INTERFACE_LINE_ATTRIBUTE6
                        AND NVL (CTAL.UNIT_SELLING_PRICE, 0) = 0
                        AND ctal.CUSTOMER_TRX_ID = P_RECEIPT_ID)
        SELECT ROUND (SUM (NVL (REVENUE_AMOUNT, 0)), 2)                                                 total_inv,
               ROUND (SUM (NVL (TAX_RECOVERABLE, 0)), 2)                                                total_tax,
               ROUND (SUM (NVL (REVENUE_AMOUNT, 0)), 2) + ROUND (SUM (NVL (TAX_RECOVERABLE, 0)), 2)     total_invoice
          INTO l_total_sales_invoice, l_total_tax, l_total_invoice
          FROM (SELECT NVL (REVENUE_AMOUNT, 0) REVENUE_AMOUNT, NVL (TAX_RECOVERABLE, 0) + NVL (fr.fre, 0) TAX_RECOVERABLE
                  --          INTO l_total_sales_invoice, l_total_tax, l_total_invoice
                  FROM AG.EVA_RA_CUSTOMER_TRX_ALL h, AG.EVA_RA_CUSTOMER_TRX_LINES_ALL d, FR
                 WHERE     h.CUSTOMER_TRX_ID = d.CUSTOMER_TRX_ID
                       AND h.CUSTOMER_TRX_ID = P_RECEIPT_ID
                       AND LINE_TYPE = 'LINE'
                       AND FR.LINE_ID(+) = d.INTERFACE_LINE_ATTRIBUTE6);

        APEX_JSON.write ('totalSales', ABS (l_total_sales_invoice));
        APEX_JSON.write ('totalCommercialDiscount', 0);
        APEX_JSON.write ('totalItemsDiscount', 0);

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------

        APEX_JSON.open_array ('extraReceiptDiscountData');
        APEX_JSON.open_object;
        APEX_JSON.write ('amount', 0);
        APEX_JSON.write ('description', '0');
        APEX_JSON.write ('rate', 0);
        APEX_JSON.close_object;
        APEX_JSON.close_array;

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------

        APEX_JSON.write ('netAmount', ABS (l_total_sales_invoice));
        APEX_JSON.write ('feesAmount', 0);
        APEX_JSON.write ('totalAmount', ABS (l_total_invoice));

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------

        APEX_JSON.open_array ('taxTotals');
        APEX_JSON.open_object;
        APEX_JSON.write ('taxType', 'T1');
        APEX_JSON.write ('amount', NVL (ABS (l_total_tax), 0));
        APEX_JSON.close_object;
        APEX_JSON.close_array;

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------

        APEX_JSON.write ('paymentMethod', 'V');
        APEX_JSON.write ('adjustment', 0);

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------

        APEX_JSON.open_object ('contractor');
        APEX_JSON.write ('name', '0');
        APEX_JSON.write ('amount', 0);
        APEX_JSON.write ('rate', 0);
        APEX_JSON.close_object;

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------

        APEX_JSON.open_object ('beneficiary');
        APEX_JSON.write ('amount', 0);
        APEX_JSON.write ('rate', 0);
        APEX_JSON.close_object;

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------
        APEX_JSON.close_object;
        APEX_JSON.close_array;
        APEX_JSON.close_object;
        L_json                 := apex_json.get_clob_output;
        l_json                 := REPLACE (l_json, '"uuid":" "', '"uuid":""');
        --        l_json                 := REPLACE (l_json, '"previousUUID":" "', '"previousUUID":""');
        l_json                 := REPLACE (l_json, '"referenceOldUUID":" "', '"referenceOldUUID":""');
        --        l_json                 := REPLACE (l_json, '"referenceUUID":" "', '"referenceUUID":""');
        l_json                 := REPLACE (l_json, '"id":" "', '"id":""');

        SELECT JSON_QUERY (l_json, '$' RETURNING CLOB) INTO l_body FROM DUAL;

        ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
        ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


        APEX_JSON.initialize_clob_output;



        --        APEX_JSON.open_object;
        APEX_JSON.open_object;

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------


        APEX_JSON.open_object ('header');

        SELECT h.TRX_NUMBER,
               h.BILL_TO_CUSTOMER_ID,
               H.INVOICE_CURRENCY_CODE,
               H.EXCHANGE_RATE,
               h.BILL_TO_SITE_USE_ID                                                                                                               --,
          -- TO_CHAR (SYSDATE - (3 / 24), 'YYYY-MM-DD"T"HH24:MI:SS"Z"')     inv_date
          --case when h.ATTRIBUTE11 = '0999' then nvl (h.PURCHASE_ORDER,0) else '0' end   PURCHASE_ORDER
          INTO l_TRX_NUMBER,
               l_BILL_TO_CUSTOMER_ID,
               L_CURRENCY,
               L_EXCHANGE_RATE,
               l_BILL_TO_SITE_USE_ID                                                                                                               --,
          --l_TRX_DATE
          --      L_PURCHASE
          FROM AG.EVA_RA_CUSTOMER_TRX_ALL h
         WHERE 1 = 1 AND h.CUSTOMER_TRX_ID = P_RECEIPT_ID;

        APEX_JSON.write ('dateTimeIssued', UPPER (l_TRX_DATE));
        APEX_JSON.write ('receiptNumber', UPPER (l_TRX_NUMBER));
        APEX_JSON.write ('uuid', ' ');
        APEX_JSON.write ('previousUUID', LAST_UUID);
        APEX_JSON.write ('referenceUUID', L_REFERENCE_UUID);
        APEX_JSON.write ('referenceOldUUID', ' ');
        APEX_JSON.write ('currency', UPPER (L_CURRENCY));
        APEX_JSON.write ('exchangeRate', UPPER (L_EXCHANGE_RATE));
        APEX_JSON.write ('sOrderNameCode', '0');
        APEX_JSON.write ('orderdeliveryMode', 'FC');
        APEX_JSON.write ('grossWeight', '0');
        APEX_JSON.write ('netWeight', '0');
        APEX_JSON.close_object;
        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------

        APEX_JSON.open_object ('documentType');
        APEX_JSON.write ('receiptType', 'r');
        APEX_JSON.write ('typeVersion', '1.2');
        APEX_JSON.close_object;

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------

        APEX_JSON.open_object ('seller');
        APEX_JSON.write ('rin', '484380486');
        APEX_JSON.write ('companyTradeName', 'اخناتون للتجارة والتوزيع');
        APEX_JSON.write ('branchCode', '0');
        -------------------------------------------
        APEX_JSON.open_object ('branchAddress');
        APEX_JSON.write ('country', 'EG');
        APEX_JSON.write ('governate', 'EGYPT');
        APEX_JSON.write ('regionCity', 'EGYPT');
        APEX_JSON.write ('street', 'GIZA');
        APEX_JSON.write ('buildingNumber', '13');
        APEX_JSON.write ('postalCode', '12311');
        APEX_JSON.write ('floor', '0');
        APEX_JSON.write ('room', '0');
        APEX_JSON.write ('landmark', '0');
        APEX_JSON.write ('additionalInformation', '0');
        APEX_JSON.close_object;
        -------------------------------------------
        APEX_JSON.write ('deviceSerialNumber', 'TRF4340ZS5');
        APEX_JSON.write ('syndicateLicenseNumber', '0');
        APEX_JSON.write ('activityCode', '4772');
        APEX_JSON.close_object;


        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------



        FOR Buyer IN (SELECT h.CUST_ACCOUNT_ID,
                             SITE_USES.SITE_USE_ID,
                             CASE WHEN h.ATTRIBUTE11 IS NOT NULL THEN 'B' ELSE 'P' END    TYPE,
                             --h.ACCOUNT_NUMBER id,
                             0                                                            id,
                             --loc.CITY                                                     id,
                             (SELECT DISTINCT h.ACCOUNT_NAME
                                FROM ONT.OE_ORDER_HEADERS_ALL    soh,
                                     AG.EVA_RA_CUSTOMER_TRX_ALL  CT,
                                     apps.HZ_CUST_SITE_USES_ALL  SITE_USES,
                                     apps.HZ_CUST_ACCOUNTS       h
                               WHERE     CT.CT_REFERENCE = SOH.ORDER_NUMBER
                                     AND CT.BILL_TO_CUSTOMER_ID = H.CUST_ACCOUNT_ID
                                     AND SOH.ORG_ID = 1963
                                     AND SOH.ORG_ID = CT.ORG_ID
                                     AND CT.BILL_TO_SITE_USE_ID = SITE_USES.SITE_USE_ID
                                     AND H.CUST_ACCOUNT_ID = l_BILL_TO_CUSTOMER_ID
                                     AND SITE_USES.SITE_USE_ID = l_BILL_TO_SITE_USE_ID
                                     AND CT.TRX_NUMBER = l_TRX_NUMBER
                                     AND SOH.ATTRIBUTE18 IS NOT NULL)                     name,
                             loc.COUNTRY                                                  country,
                             'Egypt'                                                      governate,
                             --                       'Egypt'                                regioncity,
                             --                       'Cairo - Egypt'                        street,
                             loc.ADDRESS1                                                 regionCity,
                             loc.ADDRESS1                                                 street,
                             ''                                                           buildingNumber,
                             ''                                                           postalCode,
                             ''                                                           FLOOR,
                             ''                                                           room,
                             ''                                                           landmark,
                             ''                                                           additionalInformation
                        FROM apps.HZ_CUST_ACCOUNTS        h,
                             apps.hz_parties              HP,
                             APPS.HZ_LOCATIONS            loc,
                             APPS.HZ_PARTY_SITES          party_sites,
                             apps.HZ_CUST_ACCT_SITES_ALL  ACCT_SITES,
                             APPS.HZ_CUST_ACCOUNTS_ALL    CUST_ACCOUNTS,
                             apps.HZ_CUST_SITE_USES_ALL   SITE_USES,
                             APPS.FND_FLEX_VALUES_VL      FLEX
                       WHERE     loc.LOCATION_ID = party_sites.LOCATION_ID
                             AND ACCT_SITES.PARTY_SITE_ID = party_sites.PARTY_SITE_ID
                             AND h.party_id = hp.party_id
                             AND HP.party_id = party_sites.party_id
                             AND CUST_ACCOUNTS.CUST_ACCOUNT_ID = ACCT_SITES.CUST_ACCOUNT_ID
                             AND SITE_USES.CUST_ACCT_SITE_ID = ACCT_SITES.CUST_ACCT_SITE_ID
                             /*****Updated by Mareham*****/
                             AND FLEX.FLEX_VALUE_SET_ID(+) = 1018193
                             AND FLEX.ENABLED_FLAG = 'Y'
                             AND FLEX.ATTRIBUTE3 = 'EG'
                             AND HP.PROVINCE = FLEX.FLEX_VALUE
                             /*************************/
                             --                       AND FLEX.FLEX_VALUE_SET_ID(+) = 1022025
                             --                       AND party_sites.ATTRIBUTE2 =
                             --                           FLEX.FLEX_VALUE_MEANING(+)
                             AND h.CUST_ACCOUNT_ID = CUST_ACCOUNTS.CUST_ACCOUNT_ID
                             AND h.CUST_ACCOUNT_ID IN (1836040,
                                                       2468432,
                                                       1339188,
                                                       2519757,
                                                       2596516,
                                                       2658528)
                             AND CUST_ACCOUNTS.CUST_ACCOUNT_ID = l_BILL_TO_CUSTOMER_ID
                             AND SITE_USES.SITE_USE_ID = l_BILL_TO_SITE_USE_ID)
        LOOP
            APEX_JSON.open_object ('buyer');
            APEX_JSON.write ('type', 'P');
            APEX_JSON.write ('id', ' ');
            APEX_JSON.write ('name', UPPER (Buyer.name));
            APEX_JSON.write ('mobileNumber', '0');
            APEX_JSON.write ('paymentNumber', '0');
            APEX_JSON.close_object;
        END LOOP;

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------
        APEX_JSON.open_array ('itemData');
        APEX_JSON.open_object;

        FOR cur_rec
            IN (WITH
                    mst
                    AS
                        (SELECT NVL (EGS_ITEM_CODE, i.segment1)          item_code,
                                i.segment1                               internalCode,
                                i.INVENTORY_ITEM_ID,
                                NVL (UOM, i.PRIMARY_UNIT_OF_MEASURE)     uom,
                                TAXABLE_TYPES,
                                TAX_SUBTYPES
                           FROM APPS.MTL_SYSTEM_ITEMS_FVL i, prd.ATR_ELECTRONIC_INVOICE_MAPPING_ITEMS MAP_ITEM
                          WHERE i.organization_id = 1964 AND MAP_ITEM.INVENTORY_ITEM_ID(+) = i.INVENTORY_ITEM_ID               -- AND item_type = 'FG'
                                                                                                                ),
                    CTAL
                    AS
                        (SELECT NVL (ctal.UNIT_STANDARD_PRICE, 0) * NVL (ctal.QUANTITY_INVOICED, 0) PRICE, ctal.CUSTOMER_TRX_LINE_ID
                           FROM AG.EVA_RA_CUSTOMER_TRX_LINES_ALL ctal
                          WHERE NVL (ctal.UNIT_SELLING_PRICE, 0) = 0)
                SELECT DISTINCT d.CUSTOMER_TRX_LINE_ID,
                                h.CUSTOMER_TRX_ID,
                                LINE_NUMBER,
                                h.EXCHANGE_RATE,
                                h.INVOICE_CURRENCY_CODE,
                                d.INVENTORY_ITEM_ID,
                                --DESCRIPTION description,
                                REGEXP_REPLACE (DESCRIPTION, '"')                                                           description,
                                'EGS'                                                                                       itemType,
                                'EG-484380486-' || mst.item_code                                                            itemCode,
                                mst.internalCode                                                                            internalCode,
                                mst.TAXABLE_TYPES                                                                           TAXABLE_TYPES,
                                CASE WHEN TAX_CLASSIFICATION_CODE = 'INPUT S_T 0%' THEN 'V003' ELSE MST.TAX_SUBTYPES END    TAX_SUBTYPES,
                                mst.uom                                                                                     unitType,
                                ABS (QUANTITY_CREDITED)                                                                     quantity,
                                ROUND (NVL (UNIT_SELLING_PRICE, 0), 5)                                                      unitPrice,
                                ROUND (NVL (REVENUE_AMOUNT, 0), 5)                                                          salesTotal,
                                ROUND (
                                      NVL (REVENUE_AMOUNT, 0)
                                    + NVL (TAX_RECOVERABLE, 0)
                                    + NVL ((SELECT ROUND ((NVL (PAV.ADJUSTED_AMOUNT, 0)) * NVL (d.quantity_invoiced, 0), 2)
                                              FROM APPS.OE_PRICE_ADJUSTMENTS_V PAV
                                             WHERE PAV.LIST_LINE_TYPE_CODE = 'FREIGHT_CHARGE' AND PAV.LINE_ID = INTERFACE_LINE_ATTRIBUTE6),
                                           0),
                                    5)                                                                                      total,
                                CASE
                                    WHEN     (SELECT mst.TAX_SUBTYPES
                                                FROM prd.atr_E_INVOICE_TAXABLE_SUBTYPES ts
                                               WHERE ts.TAXABLE_CODE = mst.TAX_SUBTYPES) IN ('V009')
                                         AND d.unit_selling_price = 0
                                    THEN
                                        ROUND (
                                            (SELECT ROUND (
                                                          ROUND ((NVL (PAV.ADJUSTED_AMOUNT, 0)) * NVL (ctal.quantity_invoiced, 0), 2)
                                                        * 100
                                                        / 14,
                                                        5)    fre
                                               FROM APPS.OE_PRICE_ADJUSTMENTS_V PAV, AG.EVA_RA_CUSTOMER_TRX_LINES_ALL CTAL
                                              WHERE     PAV.LIST_LINE_TYPE_CODE = 'FREIGHT_CHARGE'
                                                    AND PAV.LINE_ID = CTAL.INTERFACE_LINE_ATTRIBUTE6
                                                    AND NVL (CTAL.UNIT_SELLING_PRICE, 0) = 0
                                                    AND ctal.CUSTOMER_TRX_ID = P_RECEIPT_ID
                                                    AND PAV.LINE_ID(+) = d.INTERFACE_LINE_ATTRIBUTE6),
                                            5)
                                    --   round(nvl(d.unit_standard_price,0) * nvl(d.quantity_invoiced,0),5)
                                    WHEN     ROUND (NVL (TAX_RECOVERABLE, 0), 5) <>
                                             TRUNC ((  NVL (REVENUE_AMOUNT, 0)
                                                     * (  (SELECT ts.TAX_VALUE
                                                             FROM prd.atr_E_INVOICE_TAXABLE_SUBTYPES ts
                                                            WHERE ts.TAXABLE_CODE = mst.TAX_SUBTYPES)
                                                        / 100)),
                                                    2)
                                         AND (SELECT mst.TAX_SUBTYPES
                                                FROM prd.atr_E_INVOICE_TAXABLE_SUBTYPES ts
                                               WHERE ts.TAXABLE_CODE = mst.TAX_SUBTYPES) IN ('V010')
                                    THEN
                                          ROUND (
                                                (  (ROUND (((  UNIT_SELLING_PRICE
                                                             * QUANTITY_INVOICED
                                                             * (  (SELECT ts.TAX_VALUE
                                                                     FROM prd.atr_E_INVOICE_TAXABLE_SUBTYPES ts
                                                                    WHERE ts.TAXABLE_CODE = mst.TAX_SUBTYPES)
                                                                / 100))),
                                                           5))
                                                 - (  (NVL (REVENUE_AMOUNT, 0) + NVL (TAX_RECOVERABLE, 0))
                                                    - ROUND (NVL (UNIT_SELLING_PRICE, 0) * NVL (QUANTITY_INVOICED, 0), 5)))
                                              * (100 / 14),
                                              5)
                                        * -1
                                    ELSE
                                        0
                                END                                                                                         valueDifference,
                                0                                                                                           totalTaxableFees,
                                --nvl(REVENUE_AMOUNT,0) + nvl(TAX_RECOVERABLE,0)
                                ROUND (NVL (REVENUE_AMOUNT, 0), 5)                                                          netTotal,
                                0                                                                                           itemsDiscount,
                                SALES_ORDER,
                                SALES_ORDER_DATE,
                                LINE_TYPE,
                                ROUND (EXTENDED_AMOUNT, 5)                                                                  EXTENDED_AMOUNT,
                                ROUND (LINE_RECOVERABLE, 5)                                                                 LINE_RECOVERABLE,
                                ROUND (TAX_RECOVERABLE, 5),
                                TAX_CLASSIFICATION_CODE
                  FROM AG.EVA_RA_CUSTOMER_TRX_ALL        h,
                       AG.EVA_RA_CUSTOMER_TRX_LINES_ALL  d,
                       mst,
                       CTAL
                 WHERE     h.CUSTOMER_TRX_ID = d.CUSTOMER_TRX_ID
                       AND h.CUSTOMER_TRX_ID = P_RECEIPT_ID
                       AND d.INVENTORY_ITEM_ID = mst.INVENTORY_ITEM_ID
                       AND d.CUSTOMER_TRX_LINE_ID <> 55590039                                                                             --22-05-2024
                       AND LINE_TYPE = 'LINE'
                       AND CTAL.CUSTOMER_TRX_LINE_ID(+) = d.CUSTOMER_TRX_LINE_ID
                       AND d.CUSTOMER_TRX_LINE_ID <> 36084217                                                                             --06/06/2023
                                                             )
        LOOP
            APEX_JSON.open_array ('itemData');
            APEX_JSON.open_object;
            APEX_JSON.write ('internalCode', UPPER (cur_rec.internalCode));
            APEX_JSON.write ('description', UPPER (cur_rec.description));
            APEX_JSON.write ('itemType', UPPER (cur_rec.itemType));
            APEX_JSON.write ('itemCode', UPPER (cur_rec.itemCode));
            APEX_JSON.write ('unitType', UPPER (cur_rec.unitType));
            APEX_JSON.write ('quantity', UPPER (NVL (cur_rec.quantity, 0)));
            APEX_JSON.write ('unitPrice', UPPER (cur_rec.unitPrice));
            APEX_JSON.write ('netSale', UPPER (ABS (cur_rec.netTotal)));
            APEX_JSON.write ('totalSale', UPPER (ABS (cur_rec.netTotal)));
            APEX_JSON.write ('total', UPPER (ABS (cur_rec.total)));
            -------------------------------------------
            APEX_JSON.open_array ('commercialDiscountData');
            APEX_JSON.open_object;
            APEX_JSON.open_array ('commercialDiscountData');
            APEX_JSON.open_object;
            APEX_JSON.write ('amount', '0');
            APEX_JSON.write ('description', '0');
            APEX_JSON.write ('rate', '0');
            APEX_JSON.close_object;
            APEX_JSON.close_array;
            APEX_JSON.close_object;
            APEX_JSON.close_array;
            -------------------------------------------
            APEX_JSON.open_array ('itemDiscountData');
            APEX_JSON.open_object;
            APEX_JSON.open_array ('itemDiscountData');
            APEX_JSON.open_object;
            APEX_JSON.write ('amount', '0');
            APEX_JSON.write ('description', '0');
            APEX_JSON.write ('rate', '0');
            APEX_JSON.close_object;
            APEX_JSON.close_array;
            APEX_JSON.close_object;
            APEX_JSON.close_array;
            -------------------------------------------
            APEX_JSON.open_object ('additionalCommercialDiscount');
            APEX_JSON.write ('amount', '0');
            APEX_JSON.write ('description', '0');
            APEX_JSON.write ('rate', '0');
            APEX_JSON.close_object;
            -------------------------------------------
            APEX_JSON.open_object ('additionalItemDiscount');
            APEX_JSON.write ('amount', '0');
            APEX_JSON.write ('description', '0');
            APEX_JSON.write ('rate', '0');
            APEX_JSON.close_object;
            -------------------------------------------
            APEX_JSON.write ('valueDifference', UPPER (cur_rec.valueDifference));
            -------------------------------------------
            APEX_JSON.open_array ('taxableItems');
            APEX_JSON.open_object;

            FOR tax
                IN (SELECT tax.TAX_RATE_CODE,
                           PERCENTAGE_RATE,
                             d.TAX_RECOVERABLE
                           + NVL ((SELECT ROUND ((NVL (PAV.ADJUSTED_AMOUNT, 0)) * NVL (d.quantity_invoiced, 0), 2)
                                     FROM APPS.OE_PRICE_ADJUSTMENTS_V PAV
                                    WHERE PAV.LIST_LINE_TYPE_CODE = 'FREIGHT_CHARGE' AND PAV.LINE_ID = INTERFACE_LINE_ATTRIBUTE6),
                                  0)    TAX_RECOVERABLE
                      FROM ZX.ZX_RATES_B TAX, AG.EVA_RA_CUSTOMER_TRX_LINES_ALL d
                     WHERE     1 = 1
                           AND NVL (tax.ACTIVE_FLAG, 'Y') = 'Y'
                           AND d.TAX_CLASSIFICATION_CODE = TAX.TAX_RATE_CODE                                   -- and TAX.TAX_RATE_CODE ='PH_AR_P_14%'
                           AND SYSDATE BETWEEN TAX.EFFECTIVE_FROM AND NVL (TAX.EFFECTIVE_TO, SYSDATE + 1)
                           AND d.CUSTOMER_TRX_LINE_ID = cur_rec.CUSTOMER_TRX_LINE_ID)
            LOOP
                SELECT s.TAX_VALUE
                  INTO l_TAX_VALUE
                  FROM prd.atr_E_INVOICE_Taxable_Subtypes s
                 WHERE cur_rec.TAX_SUBTYPES = s.TAXABLE_CODE AND ROWNUM = 1;

                --                APEX_JSON.open_array ('taxableItems');
                --                APEX_JSON.open_object;
                APEX_JSON.open_array ('taxableItems');
                APEX_JSON.open_object;
                APEX_JSON.write ('taxType', NVL (UPPER (cur_rec.TAXABLE_TYPES), '0'));
                APEX_JSON.write (
                    'amount',
                    CASE
                        WHEN MOD (NVL (tax.TAX_RECOVERABLE, 0), 1) = 0 THEN TO_CHAR (NVL (tax.TAX_RECOVERABLE, 0), 'FM9999999990')
                        ELSE TO_CHAR (NVL (tax.TAX_RECOVERABLE, 0), 'FM9999999990.99')
                    END);
                APEX_JSON.write ('subType', NVL (UPPER (cur_rec.TAX_SUBTYPES), '0'));
                APEX_JSON.write ('rate', NVL (UPPER (l_TAX_VALUE), '0'));
                --                APEX_JSON.close_object;
                --                APEX_JSON.close_array;
                APEX_JSON.close_object;
                APEX_JSON.close_array;
            END LOOP;

            APEX_JSON.close_object;
            APEX_JSON.close_array;

            -------------------------------------------
            APEX_JSON.close_object;
            APEX_JSON.close_array;
        END LOOP;

        APEX_JSON.close_object;
        APEX_JSON.close_array;

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------
        WITH
            FR
            AS
                (SELECT ROUND ((NVL (PAV.ADJUSTED_AMOUNT, 0)) * NVL (ctal.quantity_invoiced, 0), 2) fre, PAV.LINE_ID
                   FROM APPS.OE_PRICE_ADJUSTMENTS_V PAV, AG.EVA_RA_CUSTOMER_TRX_LINES_ALL CTAL
                  WHERE     PAV.LIST_LINE_TYPE_CODE = 'FREIGHT_CHARGE'
                        AND PAV.LINE_ID = CTAL.INTERFACE_LINE_ATTRIBUTE6
                        AND NVL (CTAL.UNIT_SELLING_PRICE, 0) = 0
                        AND ctal.CUSTOMER_TRX_ID = P_RECEIPT_ID)
        SELECT ROUND (SUM (NVL (REVENUE_AMOUNT, 0)), 2)                                                 total_inv,
               ROUND (SUM (NVL (TAX_RECOVERABLE, 0)), 2)                                                total_tax,
               ROUND (SUM (NVL (REVENUE_AMOUNT, 0)), 2) + ROUND (SUM (NVL (TAX_RECOVERABLE, 0)), 2)     total_invoice
          INTO l_total_sales_invoice, l_total_tax, l_total_invoice
          FROM (SELECT NVL (REVENUE_AMOUNT, 0) REVENUE_AMOUNT, NVL (TAX_RECOVERABLE, 0) + NVL (fr.fre, 0) TAX_RECOVERABLE
                  --          INTO l_total_sales_invoice, l_total_tax, l_total_invoice
                  FROM AG.EVA_RA_CUSTOMER_TRX_ALL h, AG.EVA_RA_CUSTOMER_TRX_LINES_ALL d, FR
                 WHERE     h.CUSTOMER_TRX_ID = d.CUSTOMER_TRX_ID
                       AND h.CUSTOMER_TRX_ID = P_RECEIPT_ID
                       AND LINE_TYPE = 'LINE'
                       AND FR.LINE_ID(+) = d.INTERFACE_LINE_ATTRIBUTE6);

        APEX_JSON.write ('totalSales', UPPER (ABS (l_total_sales_invoice)));
        APEX_JSON.write ('totalCommercialDiscount', '0');
        APEX_JSON.write ('totalItemsDiscount', '0');

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------

        APEX_JSON.open_array ('extraReceiptDiscountData');
        APEX_JSON.open_object;
        APEX_JSON.open_array ('extraReceiptDiscountData');
        APEX_JSON.open_object;
        APEX_JSON.write ('amount', '0');
        APEX_JSON.write ('description', '0');
        APEX_JSON.write ('rate', '0');
        APEX_JSON.close_object;
        APEX_JSON.close_array;
        APEX_JSON.close_object;
        APEX_JSON.close_array;

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------

        APEX_JSON.write ('netAmount', UPPER (ABS (l_total_sales_invoice)));
        APEX_JSON.write ('feesAmount', '0');
        APEX_JSON.write ('totalAmount', UPPER (ABS (l_total_invoice)));

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------

        APEX_JSON.open_array ('taxTotals');
        APEX_JSON.open_object;
        APEX_JSON.open_array ('taxTotals');
        APEX_JSON.open_object;
        APEX_JSON.write ('taxType', 'T1');
        APEX_JSON.write ('amount', NVL (UPPER (ABS (l_total_tax)), '0'));
        APEX_JSON.close_object;
        APEX_JSON.close_array;
        APEX_JSON.close_object;
        APEX_JSON.close_array;

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------

        APEX_JSON.write ('paymentMethod', 'V');
        APEX_JSON.write ('adjustment', '0');

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------

        APEX_JSON.open_object ('contractor');
        APEX_JSON.write ('name', '0');
        APEX_JSON.write ('amount', '0');
        APEX_JSON.write ('rate', '0');
        APEX_JSON.close_object;

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------

        APEX_JSON.open_object ('beneficiary');
        APEX_JSON.write ('amount', '0');
        APEX_JSON.write ('rate', '0');
        APEX_JSON.close_object;

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------
        --        APEX_JSON.close_object;
        APEX_JSON.close_object;
        L_json_2               := apex_json.get_clob_output;
        L_json_2               := REPLACE (L_json_2, '"uuid":" "', '"uuid":""');
        --        L_json_2               := REPLACE (L_json_2, '"previousUUID":" "', '"previousUUID":""');
        L_json_2               := REPLACE (L_json_2, '"referenceOldUUID":" "', '"referenceOldUUID":""');
        --        L_json_2               := REPLACE (L_json_2, '"referenceUUID":" "', '"referenceUUID":""');
        L_json_2               := REPLACE (L_json_2, '"id":" "', '"id":""');

        --        dbms_output.put_line(L_json_2);

        SELECT JSON_QUERY (L_json_2, '$' RETURNING CLOB) INTO l_body_2 FROM DUAL;


        l_json_for_serialize   := l_body_2;
        obj                    := l_body;

        --        DBMS_OUTPUT.put_line ('for serialize' || l_json_for_serialize);
        --        DBMS_OUTPUT.put_line ('for send' || obj);

        SELECT TO_CLOB (
                   (UPPER (
                        REPLACE (REPLACE (REPLACE (REPLACE (REPLACE ((SELECT l_json_for_serialize FROM DUAL), '{', ''), '}', ''), ',', ''), '[', ''),
                                 ']',
                                 ''))))
          INTO l_serialization
          FROM DUAL;

        --        l_serialization := replace ((l_serialization),'"RECEIPTTYPE""R"','"RECEIPTTYPE""r"');

        SELECT DBMS_LOB.SUBSTR (l_serialization, 4000, '50') INTO l_after_time FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (l_serialization, 4000, '4050') INTO l_after_time_2 FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (l_serialization, 4000, '8050') INTO l_after_time_3 FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (l_serialization, 4000, '12050') INTO l_after_time_4 FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (l_serialization, 4000, '16050') INTO l_after_time_5 FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (l_serialization, 4000, '20050') INTO l_after_time_6 FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (l_serialization, 4000, '24050') INTO l_after_time_7 FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (l_serialization, 4000, '28050') INTO l_after_time_8 FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (l_serialization, 4000, '32050') INTO l_after_time_9 FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (l_serialization, 4000, '36050') INTO l_after_time_10 FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (l_serialization, 26, '1') INTO l_before_time FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (l_serialization, 23, '27') INTO l_time FROM DUAL;

        SELECT    REPLACE (l_before_time, ':', '')
               || l_time
               || REPLACE (l_after_time, ':', '')
               || REPLACE (l_after_time_2, ':', '')
               || REPLACE (l_after_time_3, ':', '')
               || REPLACE (l_after_time_4, ':', '')
               || REPLACE (l_after_time_5, ':', '')
               || REPLACE (l_after_time_6, ':', '')
               || REPLACE (l_after_time_7, ':', '')
               || REPLACE (l_after_time_8, ':', '')
               || REPLACE (l_after_time_9, ':', '')
               || REPLACE (l_after_time_10, ':', '')
          INTO l_final_serialization
          FROM DUAL;

        SELECT REGEXP_REPLACE (l_final_serialization, '"RECEIPTTYPE""R"', '"RECEIPTTYPE""r"') INTO l_final_serialization_2 FROM DUAL;

        SELECT sys.DBMS_CRYPTO.hash (src => (l_final_serialization_2), typ => 4) INTO l_hash FROM DUAL;

        SELECT DBMS_LOB.INSTR (obj, 'uuid') + 6 INTO l_instr_1 FROM DUAL;

        SELECT DBMS_LOB.INSTR (obj, 'uuid') + 7 INTO l_instr_2 FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (l_serialization, 4000, l_instr_2) INTO l_substr FROM DUAL;


        SELECT DBMS_LOB.SUBSTR (obj, l_instr_1, 1) INTO f_json FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (obj, 18, l_instr_2) INTO last_json FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (obj, 4000, 121) INTO l_last_json FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (obj, 4000, 4121) INTO l_last_json_2 FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (obj, 4000, 8121) INTO l_last_json_3 FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (obj, 4000, 12121) INTO l_last_json_4 FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (obj, 4000, 16121) INTO l_last_json_5 FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (obj, 4000, 20121) INTO l_last_json_6 FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (obj, 4000, 24121) INTO l_last_json_7 FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (obj, 4000, 28121) INTO l_last_json_8 FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (obj, 4000, 32121) INTO l_last_json_9 FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (obj, 4000, 36121) INTO l_last_json_10 FROM DUAL;



        SELECT    f_json
               || l_hash
               || last_json
               || l_last_json
               || l_last_json_2
               || l_last_json_3
               || l_last_json_4
               || l_last_json_5
               || l_last_json_6
               || l_last_json_7
               || l_last_json_8
               || l_last_json_9
               || l_last_json_10
          INTO l_final_json
          FROM DUAL;



        SELECT '"' || REPLACE ((l_final_json), '"', '\"') || '"' INTO l_body_wo_sign FROM DUAL;

        --        SELECT SUBSTR(l_body_wo_sign, 1, LENGTH(l_body_wo_sign) - 2) into l_try FROM dual;

        --        SELECT SUBSTR(l_body_wo_sign, 1, LENGTH(l_body_wo_sign) - 3) || SUBSTR(l_body_wo_sign, LENGTH(l_body_wo_sign)) into l_try FROM dual;

        SELECT    SUBSTR (l_body_wo_sign, 1, 1)
               || SUBSTR (l_body_wo_sign, 17, LENGTH (l_body_wo_sign) - 19)
               || SUBSTR (l_body_wo_sign, LENGTH (l_body_wo_sign))
          INTO l_try
          FROM DUAL;


        DBMS_OUTPUT.put_line ('uuid' || l_hash);

        get_invoice_signature (l_final_json,
                               P_server,
                               l_response,
                               l_out_signature);



        SELECT SUBSTR (REGEXP_SUBSTR (l_response, 'uuid.*",'), 8, REGEXP_INSTR (REGEXP_SUBSTR (l_response, 'uuid.*",'), '",') - 8)     uuid
          INTO l_uuid
          FROM DUAL;

        --
        --
        l_url_API              := get_url (P_server, 'API') || '/api/v1/receiptsubmissions';

        --          l_response :=
        --            apex_web_service.make_rest_request (
        --                p_url           => l_url_API,
        --                p_http_method   => 'POST',
        --                p_body          => l_final_json,
        --                p_wallet_path   => get_wallet_path,
        --                p_wallet_pwd    => get_wallet_pwd );
        --        /* Parsing Webservice Response as JSON */
        ----        apex_json.parse (l_response);
        --        SELECT SUBSTR (
        --                   REGEXP_SUBSTR (l_response, 'uuid.*",'),
        --                   8,
        --                     REGEXP_INSTR (REGEXP_SUBSTR (l_response, 'uuid.*",'),
        --                                   '",')
        --                   - 8)    uuid
        --          INTO l_uuid
        --          FROM DUAL;



        --dbms_output.put_line('uuid'||l_uuid);

        l_debug_result_id      := PRD.ATR_E_RECEIPT_DEBUG_RESULT_SEQ.NEXTVAL;

        --l_url_API   := get_url (P_server, 'API') || '/api/v1/receipts/:submissionUuid/details';


        INSERT INTO PRD.ATR_E_RECEIPT_DEBUG_RESULT (DEBUG_RESULT_ID,
                                                    URL,
                                                    STATUS_CODE,
                                                    WEB_SERVICE_NAME,
                                                    WEB_SERVICE_METHOD,
                                                    DEBUG_RESULT,
                                                    JSON_WITHOUT_SIGNATURE,
                                                    NODE_NAME,
                                                    CREATION_DATE,
                                                    CREATED_BY,
                                                    LAST_UPDATE_BY,
                                                    LAST_UPDATED_DATE,
                                                    SERIALIZATION,
                                                    Final_JSON,
                                                    UUID,
                                                    JSON_WITH_SIGNATURE,
                                                    response)
             VALUES (l_debug_result_id,
                     l_url_API,
                     apex_web_service.g_status_code,
                     '5.1 Submit Documents Credit (JSON)',
                     'POST',
                     l_response,
                     l_body,
                     --                     l_out_signature,
                     P_server,
                     SYSDATE,
                     P_PERSON_ID,
                     P_PERSON_ID,
                     SYSDATE,
                     l_final_serialization_2,
                     l_final_json,
                     l_hash,
                     l_out_signature,
                     l_get_response_f);

        COMMIT;

        SELECT JSON_VALUE (debug_result, '$.receipt.status' RETURNING VARCHAR2)
          INTO l_status
          FROM PRD.ATR_E_RECEIPT_DEBUG_RESULT
         WHERE debug_result_id = l_debug_result_id;

        INSERT INTO PRD.ATR_E_RECEIPT_HISTORY (DEBUG_RESULT_ID,
                                               INVOICE_ID,
                                               INVOICE_NUMBER,
                                               UUID,
                                               typeName,
                                               status,
                                               NODE_NAME,
                                               CREATION_DATE,
                                               CREATED_BY,
                                               LAST_UPDATE_BY,
                                               LAST_UPDATED_DATE)
             VALUES (l_debug_result_id,
                     P_RECEIPT_ID,
                     l_TRX_NUMBER,
                     l_uuid,
                     'I',
                     l_status,
                     P_server,
                     SYSDATE,
                     P_PERSON_ID,
                     P_PERSON_ID,
                     SYSDATE);

        COMMIT;
    END Submit_Documents_credit;



    PROCEDURE Submit_Documents_no_reference (P_RECEIPT_ID IN NUMBER, P_PERSON_ID IN NUMBER, P_server IN VARCHAR2)
    AS
        l_url_API                 VARCHAR2 (4000);
        l_token                   VARCHAR (32000);
        l_TRX_DATE                VARCHAR (2000);
        l_TRX_NUMBER              VARCHAR (32000);
        l_BILL_TO_CUSTOMER_ID     NUMBER;
        L_CURRENCY                VARCHAR2 (40);
        L_EXCHANGE_RATE           NUMBER;
        l_BILL_TO_SITE_USE_ID     NUMBER;
        l_total_sales_invoice     NUMBER;
        l_total_tax               NUMBER;
        l_total_invoice           NUMBER;
        l_body                    CLOB;
        l_json                    CLOB;
        l_body_2                  CLOB;
        l_json_2                  CLOB;
        l_out_signature           CLOB;
        l_response                CLOB;
        l_get_response            CLOB;
        l_get_response_f          CLOB;
        l_TAX_VALUE               NUMBER;
        l_uuid                    VARCHAR (2000);
        l_SERIALZE                CLOB;
        l_serialize_inv           CLOB;
        l_amount                  VARCHAR2 (100);
        obj                       CLOB;
        l_hash                    RAW (5000);
        l_instr_1                 NUMBER;
        l_after_time              CLOB;
        l_after_time_2            CLOB;
        l_after_time_3            CLOB;
        l_after_time_4            CLOB;
        l_after_time_5            CLOB;
        l_after_time_6            CLOB;
        l_after_time_7            CLOB;
        l_after_time_8            CLOB;
        l_after_time_9            CLOB;
        l_after_time_10           CLOB;
        l_after_time_11           CLOB;
        l_after_time_12           CLOB;
        l_before_time             CLOB;
        l_final_serialization     CLOB;
        l_final_serialization_2   CLOB;
        l_time                    VARCHAR (6000);
        l_instr_2                 VARCHAR (32000);
        l_instr_3                 VARCHAR (32000);
        l_substr                  VARCHAR (6000);
        l_substr_1                VARCHAR (10000);
        l_serialization           CLOB;
        l_json_for_serialize      CLOB;
        last_json                 CLOB;
        f_json                    CLOB;
        l_last_json               CLOB;
        l_last_json_2             CLOB;
        l_last_json_3             CLOB;
        l_last_json_4             CLOB;
        l_last_json_5             CLOB;
        l_last_json_6             CLOB;
        l_last_json_7             CLOB;
        l_last_json_8             CLOB;
        l_last_json_9             CLOB;
        l_last_json_10            CLOB;
        l_last_json_11            CLOB;
        l_last_json_12            CLOB;
        l_final_json              CLOB;
        LAST_UUID                 VARCHAR2 (2000);
        l_debug_result_id         NUMBER;
        l_body_wo_sign            CLOB;
        l_try                     CLOB;
        l_success                 BOOLEAN := FALSE;
        l_status                  VARCHAR2 (10000);
        l_reference_trx_id        VARCHAR2 (1000);
        L_REFERENCE_UUID          VARCHAR2 (1000);
        l_reference_date          VARCHAR2 (1000);
        v_start                   NUMBER;
        v_timeString              VARCHAR2 (8);
        v_newTimeString           VARCHAR2 (10);
    BEGIN
        --        l_url_API   := get_url (P_server, 'API') || '/api/v1/receiptsubmissions/:submissionUuid/details?';


        SELECT json_value (prd.atr_electronic_receipt.Login_as_Taxpayer_System (P_server), '$.access_token') INTO l_token FROM DUAL;

        SELECT APPLIED_CUSTOMER_TRX_ID
          INTO l_reference_trx_id
          FROM apps.AR_RECEIVABLE_APPLICATIONS_ALL
         WHERE CUSTOMER_TRX_ID = P_RECEIPT_ID;

        --        SELECT TO_CHAR (TRX_DATE, 'YYYY-MM-DD"T"HH24:MI:SS"Z"')
        --          INTO l_reference_date
        --          FROM AG.EVA_RA_CUSTOMER_TRX_ALL
        --         WHERE CUSTOMER_TRX_ID = l_reference_trx_id;

        --
        --    SELECT DISTINCT his.uuid
        --      INTO L_REFERENCE_UUID
        --      FROM PRD.ATR_E_RECEIPT_HISTORY his
        --     WHERE his.invoice_id = l_reference_trx_id AND his.uuid IS NOT NULL;


        APEX_JSON.initialize_clob_output;
        APEX_JSON.open_object;
        APEX_JSON.open_array ('receipts');
        APEX_JSON.open_object;

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------


        APEX_JSON.open_object ('header');

        SELECT h.TRX_NUMBER,
               h.BILL_TO_CUSTOMER_ID,
               H.INVOICE_CURRENCY_CODE,
               H.EXCHANGE_RATE,
               h.BILL_TO_SITE_USE_ID,
               TO_CHAR (SYSDATE - (3 / 24), 'YYYY-MM-DD"T"HH24:MI:SS"Z"')                       inv_date,
               TO_CHAR (TO_DATE ('2024/09/25', 'YYYY/MM/DD'), 'YYYY-MM-DD"T"HH24:MI:SS"Z"')     ref_date
          --case when h.ATTRIBUTE11 = '0999' then nvl (h.PURCHASE_ORDER,0) else '0' end   PURCHASE_ORDER
          INTO l_TRX_NUMBER,
               l_BILL_TO_CUSTOMER_ID,
               L_CURRENCY,
               L_EXCHANGE_RATE,
               l_BILL_TO_SITE_USE_ID,
               l_TRX_DATE,
               l_reference_date
          --      L_PURCHASE
          FROM AG.EVA_RA_CUSTOMER_TRX_ALL h
         WHERE 1 = 1 AND h.CUSTOMER_TRX_ID = P_RECEIPT_ID;

        SELECT UUID
          INTO LAST_UUID
          FROM PRD.ATR_E_RECEIPT_DEBUG_RESULT
         WHERE DEBUG_RESULT_ID = (SELECT MAX (DEBUG_RESULT_ID) FROM PRD.ATR_E_RECEIPT_DEBUG_RESULT);

        --          SELECT ''
        --          INTO LAST_UUID
        --          FROM dual;

        APEX_JSON.write ('dateTimeIssued', l_TRX_DATE);
        APEX_JSON.write ('receiptNumber', l_TRX_NUMBER);
        APEX_JSON.write ('uuid', ' ');
        APEX_JSON.write ('previousUUID', LAST_UUID);
        APEX_JSON.write ('referenceUUID', ' ');
        APEX_JSON.write ('referenceOldUUID', ' ');
        APEX_JSON.write ('currency', UPPER (L_CURRENCY));
        APEX_JSON.write ('exchangeRate', L_EXCHANGE_RATE);
        APEX_JSON.write ('sOrderNameCode', '0');
        APEX_JSON.write ('orderdeliveryMode', 'FC');
        APEX_JSON.write ('grossWeight', 0);
        APEX_JSON.write ('netWeight', 0);
        APEX_JSON.write ('documentUseReason', 'B');
        APEX_JSON.write ('salesIssuedDateTime', l_reference_date);
        APEX_JSON.close_object;
        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------

        APEX_JSON.open_object ('documentType');
        APEX_JSON.write ('receiptType', 'RWR');
        APEX_JSON.write ('typeVersion', '1.2');
        APEX_JSON.close_object;

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------

        APEX_JSON.open_object ('seller');
        APEX_JSON.write ('rin', '484380486');
        APEX_JSON.write ('companyTradeName', 'اخناتون للتجارة والتوزيع');
        APEX_JSON.write ('branchCode', '0');
        -------------------------------------------
        APEX_JSON.open_object ('branchAddress');
        APEX_JSON.write ('country', 'EG');
        APEX_JSON.write ('governate', 'EGYPT');
        APEX_JSON.write ('regionCity', 'EGYPT');
        APEX_JSON.write ('street', 'GIZA');
        APEX_JSON.write ('buildingNumber', '13');
        APEX_JSON.write ('postalCode', '12311');
        APEX_JSON.write ('floor', '0');
        APEX_JSON.write ('room', '0');
        APEX_JSON.write ('landmark', '0');
        APEX_JSON.write ('additionalInformation', '0');
        APEX_JSON.close_object;
        -------------------------------------------
        APEX_JSON.write ('deviceSerialNumber', 'TRF4340ZS5');
        APEX_JSON.write ('syndicateLicenseNumber', '0');
        APEX_JSON.write ('activityCode', '4772');
        APEX_JSON.close_object;


        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------

        APEX_JSON.open_object ('buyer');

        FOR Buyer IN (SELECT h.CUST_ACCOUNT_ID,
                             SITE_USES.SITE_USE_ID,
                             CASE WHEN h.ATTRIBUTE11 IS NOT NULL THEN 'B' ELSE 'P' END    TYPE,
                             --h.ACCOUNT_NUMBER id,
                             0                                                            id,
                             -- loc.CITY                                                     id,
                             (SELECT DISTINCT h.ACCOUNT_NAME
                                FROM ONT.OE_ORDER_HEADERS_ALL    soh,
                                     AG.EVA_RA_CUSTOMER_TRX_ALL  CT,
                                     apps.HZ_CUST_SITE_USES_ALL  SITE_USES,
                                     apps.HZ_CUST_ACCOUNTS       h
                               WHERE     CT.CT_REFERENCE = SOH.ORDER_NUMBER
                                     AND CT.BILL_TO_CUSTOMER_ID = H.CUST_ACCOUNT_ID
                                     AND SOH.ORG_ID = 1963
                                     AND SOH.ORG_ID = CT.ORG_ID
                                     AND CT.BILL_TO_SITE_USE_ID = SITE_USES.SITE_USE_ID
                                     AND H.CUST_ACCOUNT_ID = l_BILL_TO_CUSTOMER_ID
                                     AND SITE_USES.SITE_USE_ID = l_BILL_TO_SITE_USE_ID
                                     AND CT.TRX_NUMBER = l_TRX_NUMBER
                                     AND SOH.ATTRIBUTE18 IS NOT NULL)                     name,
                             loc.COUNTRY                                                  country,
                             'Egypt'                                                      governate,
                             --                       'Egypt'                                regioncity,
                             --                       'Cairo - Egypt'                        street,
                             loc.ADDRESS1                                                 regionCity,
                             loc.ADDRESS1                                                 street,
                             ''                                                           buildingNumber,
                             ''                                                           postalCode,
                             ''                                                           FLOOR,
                             ''                                                           room,
                             ''                                                           landmark,
                             ''                                                           additionalInformation
                        FROM apps.HZ_CUST_ACCOUNTS        h,
                             apps.hz_parties              HP,
                             APPS.HZ_LOCATIONS            loc,
                             APPS.HZ_PARTY_SITES          party_sites,
                             apps.HZ_CUST_ACCT_SITES_ALL  ACCT_SITES,
                             APPS.HZ_CUST_ACCOUNTS_ALL    CUST_ACCOUNTS,
                             apps.HZ_CUST_SITE_USES_ALL   SITE_USES,
                             APPS.FND_FLEX_VALUES_VL      FLEX
                       WHERE     loc.LOCATION_ID = party_sites.LOCATION_ID
                             AND ACCT_SITES.PARTY_SITE_ID = party_sites.PARTY_SITE_ID
                             AND h.party_id = hp.party_id
                             AND HP.party_id = party_sites.party_id
                             AND CUST_ACCOUNTS.CUST_ACCOUNT_ID = ACCT_SITES.CUST_ACCOUNT_ID
                             AND SITE_USES.CUST_ACCT_SITE_ID = ACCT_SITES.CUST_ACCT_SITE_ID
                             /*****Updated by Mareham*****/
                             AND FLEX.FLEX_VALUE_SET_ID(+) = 1018193
                             AND FLEX.ENABLED_FLAG = 'Y'
                             AND FLEX.ATTRIBUTE3 = 'EG'
                             AND HP.PROVINCE = FLEX.FLEX_VALUE
                             /*************************/
                             --                       AND FLEX.FLEX_VALUE_SET_ID(+) = 1022025
                             --                       AND party_sites.ATTRIBUTE2 =
                             --                           FLEX.FLEX_VALUE_MEANING(+)
                             AND h.CUST_ACCOUNT_ID = CUST_ACCOUNTS.CUST_ACCOUNT_ID
                             AND h.CUST_ACCOUNT_ID IN (1836040,
                                                       2468432,
                                                       1339188,
                                                       2519757,
                                                       2596516,
                                                       2658528)
                             AND CUST_ACCOUNTS.CUST_ACCOUNT_ID = l_BILL_TO_CUSTOMER_ID
                             AND SITE_USES.SITE_USE_ID = l_BILL_TO_SITE_USE_ID)
        LOOP
            APEX_JSON.write ('type', 'P');
            APEX_JSON.write ('id', ' ');
            APEX_JSON.write ('name', UPPER (Buyer.name));
            APEX_JSON.write ('mobileNumber', '0');
            APEX_JSON.write ('paymentNumber', '0');
            APEX_JSON.close_object;
        END LOOP;

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------
        APEX_JSON.open_array ('itemData');

        FOR cur_rec
            IN (WITH
                    mst
                    AS
                        (SELECT NVL (EGS_ITEM_CODE, i.segment1)          item_code,
                                i.segment1                               internalCode,
                                i.INVENTORY_ITEM_ID,
                                NVL (UOM, i.PRIMARY_UNIT_OF_MEASURE)     uom,
                                TAXABLE_TYPES,
                                TAX_SUBTYPES
                           FROM APPS.MTL_SYSTEM_ITEMS_FVL i, prd.ATR_ELECTRONIC_INVOICE_MAPPING_ITEMS MAP_ITEM
                          WHERE i.organization_id = 1964 AND MAP_ITEM.INVENTORY_ITEM_ID(+) = i.INVENTORY_ITEM_ID               -- AND item_type = 'FG'
                                                                                                                ),
                    CTAL
                    AS
                        (SELECT NVL (ctal.UNIT_STANDARD_PRICE, 0) * NVL (ctal.QUANTITY_INVOICED, 0) PRICE, ctal.CUSTOMER_TRX_LINE_ID
                           FROM AG.EVA_RA_CUSTOMER_TRX_LINES_ALL ctal
                          WHERE NVL (ctal.UNIT_SELLING_PRICE, 0) = 0)
                SELECT DISTINCT d.CUSTOMER_TRX_LINE_ID,
                                h.CUSTOMER_TRX_ID,
                                LINE_NUMBER,
                                h.EXCHANGE_RATE,
                                h.INVOICE_CURRENCY_CODE,
                                d.INVENTORY_ITEM_ID,
                                --DESCRIPTION description,
                                REGEXP_REPLACE (DESCRIPTION, '"')                                                           description,
                                'EGS'                                                                                       itemType,
                                'EG-484380486-' || mst.item_code                                                            itemCode,
                                mst.internalCode                                                                            internalCode,
                                mst.TAXABLE_TYPES                                                                           TAXABLE_TYPES,
                                CASE WHEN TAX_CLASSIFICATION_CODE = 'INPUT S_T 0%' THEN 'V003' ELSE MST.TAX_SUBTYPES END    TAX_SUBTYPES,
                                mst.uom                                                                                     unitType,
                                ABS (QUANTITY_CREDITED)                                                                     quantity,
                                ROUND (NVL (UNIT_SELLING_PRICE, 0), 5)                                                      unitPrice,
                                ROUND (NVL (REVENUE_AMOUNT, 0), 5)                                                          salesTotal,
                                ROUND (
                                      NVL (REVENUE_AMOUNT, 0)
                                    + NVL (TAX_RECOVERABLE, 0)
                                    + NVL ((SELECT ROUND ((NVL (PAV.ADJUSTED_AMOUNT, 0)) * NVL (d.quantity_invoiced, 0), 2)
                                              FROM APPS.OE_PRICE_ADJUSTMENTS_V PAV
                                             WHERE PAV.LIST_LINE_TYPE_CODE = 'FREIGHT_CHARGE' AND PAV.LINE_ID = INTERFACE_LINE_ATTRIBUTE6),
                                           0),
                                    5)                                                                                      total,
                                CASE
                                    WHEN     (SELECT mst.TAX_SUBTYPES
                                                FROM prd.atr_E_INVOICE_TAXABLE_SUBTYPES ts
                                               WHERE ts.TAXABLE_CODE = mst.TAX_SUBTYPES) IN ('V009')
                                         AND d.unit_selling_price = 0
                                    THEN
                                        ROUND (
                                            (SELECT ROUND (
                                                          ROUND ((NVL (PAV.ADJUSTED_AMOUNT, 0)) * NVL (ctal.quantity_invoiced, 0), 2)
                                                        * 100
                                                        / 14,
                                                        5)    fre
                                               FROM APPS.OE_PRICE_ADJUSTMENTS_V PAV, AG.EVA_RA_CUSTOMER_TRX_LINES_ALL CTAL
                                              WHERE     PAV.LIST_LINE_TYPE_CODE = 'FREIGHT_CHARGE'
                                                    AND PAV.LINE_ID = CTAL.INTERFACE_LINE_ATTRIBUTE6
                                                    AND NVL (CTAL.UNIT_SELLING_PRICE, 0) = 0
                                                    AND ctal.CUSTOMER_TRX_ID = P_RECEIPT_ID
                                                    AND PAV.LINE_ID(+) = d.INTERFACE_LINE_ATTRIBUTE6),
                                            5)
                                    --   round(nvl(d.unit_standard_price,0) * nvl(d.quantity_invoiced,0),5)
                                    WHEN     ROUND (NVL (TAX_RECOVERABLE, 0), 5) <>
                                             TRUNC ((  NVL (REVENUE_AMOUNT, 0)
                                                     * (  (SELECT ts.TAX_VALUE
                                                             FROM prd.atr_E_INVOICE_TAXABLE_SUBTYPES ts
                                                            WHERE ts.TAXABLE_CODE = mst.TAX_SUBTYPES)
                                                        / 100)),
                                                    2)
                                         AND (SELECT mst.TAX_SUBTYPES
                                                FROM prd.atr_E_INVOICE_TAXABLE_SUBTYPES ts
                                               WHERE ts.TAXABLE_CODE = mst.TAX_SUBTYPES) IN ('V010')
                                    THEN
                                          ROUND (
                                                (  (ROUND (((  UNIT_SELLING_PRICE
                                                             * QUANTITY_INVOICED
                                                             * (  (SELECT ts.TAX_VALUE
                                                                     FROM prd.atr_E_INVOICE_TAXABLE_SUBTYPES ts
                                                                    WHERE ts.TAXABLE_CODE = mst.TAX_SUBTYPES)
                                                                / 100))),
                                                           5))
                                                 - (  (NVL (REVENUE_AMOUNT, 0) + NVL (TAX_RECOVERABLE, 0))
                                                    - ROUND (NVL (UNIT_SELLING_PRICE, 0) * NVL (QUANTITY_INVOICED, 0), 5)))
                                              * (100 / 14),
                                              5)
                                        * -1
                                    ELSE
                                        0
                                END                                                                                         valueDifference,
                                0                                                                                           totalTaxableFees,
                                --nvl(REVENUE_AMOUNT,0) + nvl(TAX_RECOVERABLE,0)
                                ROUND (NVL (REVENUE_AMOUNT, 0), 5)                                                          netTotal,
                                0                                                                                           itemsDiscount,
                                SALES_ORDER,
                                SALES_ORDER_DATE,
                                LINE_TYPE,
                                ROUND (EXTENDED_AMOUNT, 5)                                                                  EXTENDED_AMOUNT,
                                ROUND (LINE_RECOVERABLE, 5)                                                                 LINE_RECOVERABLE,
                                ROUND (TAX_RECOVERABLE, 5),
                                TAX_CLASSIFICATION_CODE
                  FROM AG.EVA_RA_CUSTOMER_TRX_ALL        h,
                       AG.EVA_RA_CUSTOMER_TRX_LINES_ALL  d,
                       mst,
                       CTAL
                 WHERE     h.CUSTOMER_TRX_ID = d.CUSTOMER_TRX_ID
                       AND h.CUSTOMER_TRX_ID = P_RECEIPT_ID
                       AND d.INVENTORY_ITEM_ID = mst.INVENTORY_ITEM_ID
                       AND d.CUSTOMER_TRX_LINE_ID <> 55590039                                                                             --22-05-2024
                       AND LINE_TYPE = 'LINE'
                       AND CTAL.CUSTOMER_TRX_LINE_ID(+) = d.CUSTOMER_TRX_LINE_ID
                       AND d.CUSTOMER_TRX_LINE_ID <> 36084217                                                                             --06/06/2023
                                                             )
        LOOP
            APEX_JSON.open_object;
            APEX_JSON.write ('internalCode', UPPER (cur_rec.internalCode));
            APEX_JSON.write ('description', UPPER (cur_rec.description));
            APEX_JSON.write ('itemType', UPPER (cur_rec.itemType));
            APEX_JSON.write ('itemCode', UPPER (cur_rec.itemCode));
            APEX_JSON.write ('unitType', UPPER (cur_rec.unitType));
            APEX_JSON.write ('quantity', NVL (cur_rec.quantity, 0));
            APEX_JSON.write ('unitPrice', cur_rec.unitPrice);
            APEX_JSON.write ('netSale', ABS (cur_rec.netTotal));
            APEX_JSON.write ('totalSale', ABS (cur_rec.netTotal));
            APEX_JSON.write ('total', ABS (cur_rec.total));
            -------------------------------------------
            APEX_JSON.open_array ('commercialDiscountData');
            APEX_JSON.open_object;
            APEX_JSON.write ('amount', 0);
            APEX_JSON.write ('description', '0');
            APEX_JSON.write ('rate', 0);
            APEX_JSON.close_object;
            APEX_JSON.close_array;
            -------------------------------------------
            APEX_JSON.open_array ('itemDiscountData');
            APEX_JSON.open_object;
            APEX_JSON.write ('amount', 0);
            APEX_JSON.write ('description', '0');
            APEX_JSON.write ('rate', 0);
            APEX_JSON.close_object;
            APEX_JSON.close_array;
            -------------------------------------------
            APEX_JSON.open_object ('additionalCommercialDiscount');
            APEX_JSON.write ('amount', 0);
            APEX_JSON.write ('description', '0');
            APEX_JSON.write ('rate', 0);
            APEX_JSON.close_object;
            -------------------------------------------
            APEX_JSON.open_object ('additionalItemDiscount');
            APEX_JSON.write ('amount', 0);
            APEX_JSON.write ('description', '0');
            APEX_JSON.write ('rate', 0);
            APEX_JSON.close_object;
            -------------------------------------------
            APEX_JSON.write ('valueDifference', cur_rec.valueDifference);
            -------------------------------------------

            APEX_JSON.open_array ('taxableItems');

            FOR tax
                IN (SELECT tax.TAX_RATE_CODE,
                           PERCENTAGE_RATE,
                             d.TAX_RECOVERABLE
                           + NVL ((SELECT ROUND ((NVL (PAV.ADJUSTED_AMOUNT, 0)) * NVL (d.quantity_invoiced, 0), 2)
                                     FROM APPS.OE_PRICE_ADJUSTMENTS_V PAV
                                    WHERE PAV.LIST_LINE_TYPE_CODE = 'FREIGHT_CHARGE' AND PAV.LINE_ID = INTERFACE_LINE_ATTRIBUTE6),
                                  0)    TAX_RECOVERABLE
                      FROM ZX.ZX_RATES_B TAX, AG.EVA_RA_CUSTOMER_TRX_LINES_ALL d
                     WHERE     1 = 1
                           AND NVL (tax.ACTIVE_FLAG, 'Y') = 'Y'
                           AND d.TAX_CLASSIFICATION_CODE = TAX.TAX_RATE_CODE
                           AND SYSDATE BETWEEN TAX.EFFECTIVE_FROM AND NVL (TAX.EFFECTIVE_TO, SYSDATE + 1)
                           AND d.CUSTOMER_TRX_LINE_ID = cur_rec.CUSTOMER_TRX_LINE_ID)
            LOOP
                SELECT s.TAX_VALUE
                  INTO l_TAX_VALUE
                  FROM prd.atr_E_INVOICE_Taxable_Subtypes s
                 WHERE cur_rec.TAX_SUBTYPES = s.TAXABLE_CODE AND ROWNUM = 1;

                APEX_JSON.open_object;
                APEX_JSON.write ('taxType', NVL (UPPER (cur_rec.TAXABLE_TYPES), '0'));
                APEX_JSON.write ('amount', NVL (ABS (tax.TAX_RECOVERABLE), 0));
                APEX_JSON.write ('subType', NVL (UPPER (cur_rec.TAX_SUBTYPES), '0'));
                APEX_JSON.write ('rate', NVL (l_TAX_VALUE, 0));
                APEX_JSON.close_object;
            END LOOP;

            APEX_JSON.close_array;

            -------------------------------------------
            APEX_JSON.close_object;
        END LOOP;

        APEX_JSON.close_array;

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------
        WITH
            FR
            AS
                (SELECT ROUND ((NVL (PAV.ADJUSTED_AMOUNT, 0)) * NVL (ctal.quantity_invoiced, 0), 2) fre, PAV.LINE_ID
                   FROM APPS.OE_PRICE_ADJUSTMENTS_V PAV, AG.EVA_RA_CUSTOMER_TRX_LINES_ALL CTAL
                  WHERE     PAV.LIST_LINE_TYPE_CODE = 'FREIGHT_CHARGE'
                        AND PAV.LINE_ID = CTAL.INTERFACE_LINE_ATTRIBUTE6
                        AND NVL (CTAL.UNIT_SELLING_PRICE, 0) = 0
                        AND ctal.CUSTOMER_TRX_ID = P_RECEIPT_ID)
        SELECT ROUND (SUM (NVL (REVENUE_AMOUNT, 0)), 2)                                                 total_inv,
               ROUND (SUM (NVL (TAX_RECOVERABLE, 0)), 2)                                                total_tax,
               ROUND (SUM (NVL (REVENUE_AMOUNT, 0)), 2) + ROUND (SUM (NVL (TAX_RECOVERABLE, 0)), 2)     total_invoice
          INTO l_total_sales_invoice, l_total_tax, l_total_invoice
          FROM (SELECT NVL (REVENUE_AMOUNT, 0) REVENUE_AMOUNT, NVL (TAX_RECOVERABLE, 0) + NVL (fr.fre, 0) TAX_RECOVERABLE
                  --          INTO l_total_sales_invoice, l_total_tax, l_total_invoice
                  FROM AG.EVA_RA_CUSTOMER_TRX_ALL h, AG.EVA_RA_CUSTOMER_TRX_LINES_ALL d, FR
                 WHERE     h.CUSTOMER_TRX_ID = d.CUSTOMER_TRX_ID
                       AND h.CUSTOMER_TRX_ID = P_RECEIPT_ID
                       AND LINE_TYPE = 'LINE'
                       AND FR.LINE_ID(+) = d.INTERFACE_LINE_ATTRIBUTE6);

        APEX_JSON.write ('totalSales', ABS (l_total_sales_invoice));
        APEX_JSON.write ('totalCommercialDiscount', 0);
        APEX_JSON.write ('totalItemsDiscount', 0);

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------

        APEX_JSON.open_array ('extraReceiptDiscountData');
        APEX_JSON.open_object;
        APEX_JSON.write ('amount', 0);
        APEX_JSON.write ('description', '0');
        APEX_JSON.write ('rate', 0);
        APEX_JSON.close_object;
        APEX_JSON.close_array;

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------

        APEX_JSON.write ('netAmount', ABS (l_total_sales_invoice));
        APEX_JSON.write ('feesAmount', 0);
        APEX_JSON.write ('totalAmount', ABS (l_total_invoice));

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------

        APEX_JSON.open_array ('taxTotals');
        APEX_JSON.open_object;
        APEX_JSON.write ('taxType', 'T1');
        APEX_JSON.write ('amount', NVL (ABS (l_total_tax), 0));
        APEX_JSON.close_object;
        APEX_JSON.close_array;

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------

        APEX_JSON.write ('paymentMethod', 'V');
        APEX_JSON.write ('adjustment', 0);

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------

        APEX_JSON.open_object ('contractor');
        APEX_JSON.write ('name', '0');
        APEX_JSON.write ('amount', 0);
        APEX_JSON.write ('rate', 0);
        APEX_JSON.close_object;

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------

        APEX_JSON.open_object ('beneficiary');
        APEX_JSON.write ('amount', 0);
        APEX_JSON.write ('rate', 0);
        APEX_JSON.close_object;

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------
        APEX_JSON.close_object;
        APEX_JSON.close_array;
        APEX_JSON.close_object;
        L_json                    := apex_json.get_clob_output;
        l_json                    := REPLACE (l_json, '"uuid":" "', '"uuid":""');
        --        l_json                 := REPLACE (l_json, '"previousUUID":" "', '"previousUUID":""');
        l_json                    := REPLACE (l_json, '"referenceOldUUID":" "', '"referenceOldUUID":""');
        l_json                    := REPLACE (l_json, '"referenceUUID":" "', '"referenceUUID":""');
        l_json                    := REPLACE (l_json, '"id":" "', '"id":""');

        SELECT JSON_QUERY (l_json, '$' RETURNING CLOB) INTO l_body FROM DUAL;

        ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
        ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


        APEX_JSON.initialize_clob_output;



        --        APEX_JSON.open_object;
        APEX_JSON.open_object;

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------


        APEX_JSON.open_object ('header');

        SELECT h.TRX_NUMBER,
               h.BILL_TO_CUSTOMER_ID,
               H.INVOICE_CURRENCY_CODE,
               H.EXCHANGE_RATE,
               h.BILL_TO_SITE_USE_ID,
               TO_CHAR (SYSDATE - (3 / 24), 'YYYY-MM-DD"T"HH24:MI:SS"Z"')                       inv_date,
               TO_CHAR (TO_DATE ('2024/09/25', 'YYYY/MM/DD'), 'YYYY-MM-DD"T"HH24:MI:SS"Z"')     ref_date
          --case when h.ATTRIBUTE11 = '0999' then nvl (h.PURCHASE_ORDER,0) else '0' end   PURCHASE_ORDER
          INTO l_TRX_NUMBER,
               l_BILL_TO_CUSTOMER_ID,
               L_CURRENCY,
               L_EXCHANGE_RATE,
               l_BILL_TO_SITE_USE_ID,
               l_TRX_DATE,
               l_reference_date
          --      L_PURCHASE
          FROM AG.EVA_RA_CUSTOMER_TRX_ALL h
         WHERE 1 = 1 AND h.CUSTOMER_TRX_ID = P_RECEIPT_ID;

        APEX_JSON.write ('dateTimeIssued', UPPER (l_TRX_DATE));
        APEX_JSON.write ('receiptNumber', UPPER (l_TRX_NUMBER));
        APEX_JSON.write ('uuid', ' ');
        APEX_JSON.write ('previousUUID', LAST_UUID);
        APEX_JSON.write ('referenceUUID', ' ');
        APEX_JSON.write ('referenceOldUUID', ' ');
        APEX_JSON.write ('currency', UPPER (L_CURRENCY));
        APEX_JSON.write ('exchangeRate', UPPER (L_EXCHANGE_RATE));
        APEX_JSON.write ('sOrderNameCode', '0');
        APEX_JSON.write ('orderdeliveryMode', 'FC');
        APEX_JSON.write ('grossWeight', '0');
        APEX_JSON.write ('netWeight', '0');
        APEX_JSON.write ('documentUseReason', 'B');
        APEX_JSON.write ('salesIssuedDateTime', l_reference_date);
        APEX_JSON.close_object;
        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------

        APEX_JSON.open_object ('documentType');
        APEX_JSON.write ('receiptType', 'RWR');
        APEX_JSON.write ('typeVersion', '1.2');
        APEX_JSON.close_object;

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------

        APEX_JSON.open_object ('seller');
        APEX_JSON.write ('rin', '484380486');
        APEX_JSON.write ('companyTradeName', 'اخناتون للتجارة والتوزيع');
        APEX_JSON.write ('branchCode', '0');
        -------------------------------------------
        APEX_JSON.open_object ('branchAddress');
        APEX_JSON.write ('country', 'EG');
        APEX_JSON.write ('governate', 'EGYPT');
        APEX_JSON.write ('regionCity', 'EGYPT');
        APEX_JSON.write ('street', 'GIZA');
        APEX_JSON.write ('buildingNumber', '13');
        APEX_JSON.write ('postalCode', '12311');
        APEX_JSON.write ('floor', '0');
        APEX_JSON.write ('room', '0');
        APEX_JSON.write ('landmark', '0');
        APEX_JSON.write ('additionalInformation', '0');
        APEX_JSON.close_object;
        -------------------------------------------
        APEX_JSON.write ('deviceSerialNumber', 'TRF4340ZS5');
        APEX_JSON.write ('syndicateLicenseNumber', '0');
        APEX_JSON.write ('activityCode', '4772');
        APEX_JSON.close_object;


        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------



        FOR Buyer IN (SELECT h.CUST_ACCOUNT_ID,
                             SITE_USES.SITE_USE_ID,
                             CASE WHEN h.ATTRIBUTE11 IS NOT NULL THEN 'B' ELSE 'P' END    TYPE,
                             --h.ACCOUNT_NUMBER id,
                             0                                                            id,
                             --loc.CITY                                                     id,
                             (SELECT DISTINCT h.ACCOUNT_NAME
                                FROM ONT.OE_ORDER_HEADERS_ALL    soh,
                                     AG.EVA_RA_CUSTOMER_TRX_ALL  CT,
                                     apps.HZ_CUST_SITE_USES_ALL  SITE_USES,
                                     apps.HZ_CUST_ACCOUNTS       h
                               WHERE     CT.CT_REFERENCE = SOH.ORDER_NUMBER
                                     AND CT.BILL_TO_CUSTOMER_ID = H.CUST_ACCOUNT_ID
                                     AND SOH.ORG_ID = 1963
                                     AND SOH.ORG_ID = CT.ORG_ID
                                     AND CT.BILL_TO_SITE_USE_ID = SITE_USES.SITE_USE_ID
                                     AND H.CUST_ACCOUNT_ID = l_BILL_TO_CUSTOMER_ID
                                     AND SITE_USES.SITE_USE_ID = l_BILL_TO_SITE_USE_ID
                                     AND CT.TRX_NUMBER = l_TRX_NUMBER
                                     AND SOH.ATTRIBUTE18 IS NOT NULL)                     name,
                             loc.COUNTRY                                                  country,
                             'Egypt'                                                      governate,
                             --                       'Egypt'                                regioncity,
                             --                       'Cairo - Egypt'                        street,
                             loc.ADDRESS1                                                 regionCity,
                             loc.ADDRESS1                                                 street,
                             ''                                                           buildingNumber,
                             ''                                                           postalCode,
                             ''                                                           FLOOR,
                             ''                                                           room,
                             ''                                                           landmark,
                             ''                                                           additionalInformation
                        FROM apps.HZ_CUST_ACCOUNTS        h,
                             apps.hz_parties              HP,
                             APPS.HZ_LOCATIONS            loc,
                             APPS.HZ_PARTY_SITES          party_sites,
                             apps.HZ_CUST_ACCT_SITES_ALL  ACCT_SITES,
                             APPS.HZ_CUST_ACCOUNTS_ALL    CUST_ACCOUNTS,
                             apps.HZ_CUST_SITE_USES_ALL   SITE_USES,
                             APPS.FND_FLEX_VALUES_VL      FLEX
                       WHERE     loc.LOCATION_ID = party_sites.LOCATION_ID
                             AND ACCT_SITES.PARTY_SITE_ID = party_sites.PARTY_SITE_ID
                             AND h.party_id = hp.party_id
                             AND HP.party_id = party_sites.party_id
                             AND CUST_ACCOUNTS.CUST_ACCOUNT_ID = ACCT_SITES.CUST_ACCOUNT_ID
                             AND SITE_USES.CUST_ACCT_SITE_ID = ACCT_SITES.CUST_ACCT_SITE_ID
                             /*****Updated by Mareham*****/
                             AND FLEX.FLEX_VALUE_SET_ID(+) = 1018193
                             AND FLEX.ENABLED_FLAG = 'Y'
                             AND FLEX.ATTRIBUTE3 = 'EG'
                             AND HP.PROVINCE = FLEX.FLEX_VALUE
                             /*************************/
                             --                       AND FLEX.FLEX_VALUE_SET_ID(+) = 1022025
                             --                       AND party_sites.ATTRIBUTE2 =
                             --                           FLEX.FLEX_VALUE_MEANING(+)
                             AND h.CUST_ACCOUNT_ID = CUST_ACCOUNTS.CUST_ACCOUNT_ID
                             AND h.CUST_ACCOUNT_ID IN (1836040,
                                                       2468432,
                                                       1339188,
                                                       2519757,
                                                       2596516,
                                                       2658528)
                             AND CUST_ACCOUNTS.CUST_ACCOUNT_ID = l_BILL_TO_CUSTOMER_ID
                             AND SITE_USES.SITE_USE_ID = l_BILL_TO_SITE_USE_ID)
        LOOP
            APEX_JSON.open_object ('buyer');
            APEX_JSON.write ('type', 'P');
            APEX_JSON.write ('id', ' ');
            APEX_JSON.write ('name', UPPER (Buyer.name));
            APEX_JSON.write ('mobileNumber', '0');
            APEX_JSON.write ('paymentNumber', '0');
            APEX_JSON.close_object;
        END LOOP;

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------
        APEX_JSON.open_array ('itemData');
        APEX_JSON.open_object;

        FOR cur_rec
            IN (WITH
                    mst
                    AS
                        (SELECT NVL (EGS_ITEM_CODE, i.segment1)          item_code,
                                i.segment1                               internalCode,
                                i.INVENTORY_ITEM_ID,
                                NVL (UOM, i.PRIMARY_UNIT_OF_MEASURE)     uom,
                                TAXABLE_TYPES,
                                TAX_SUBTYPES
                           FROM APPS.MTL_SYSTEM_ITEMS_FVL i, prd.ATR_ELECTRONIC_INVOICE_MAPPING_ITEMS MAP_ITEM
                          WHERE i.organization_id = 1964 AND MAP_ITEM.INVENTORY_ITEM_ID(+) = i.INVENTORY_ITEM_ID               -- AND item_type = 'FG'
                                                                                                                ),
                    CTAL
                    AS
                        (SELECT NVL (ctal.UNIT_STANDARD_PRICE, 0) * NVL (ctal.QUANTITY_INVOICED, 0) PRICE, ctal.CUSTOMER_TRX_LINE_ID
                           FROM AG.EVA_RA_CUSTOMER_TRX_LINES_ALL ctal
                          WHERE NVL (ctal.UNIT_SELLING_PRICE, 0) = 0)
                SELECT DISTINCT d.CUSTOMER_TRX_LINE_ID,
                                h.CUSTOMER_TRX_ID,
                                LINE_NUMBER,
                                h.EXCHANGE_RATE,
                                h.INVOICE_CURRENCY_CODE,
                                d.INVENTORY_ITEM_ID,
                                --DESCRIPTION description,
                                REGEXP_REPLACE (DESCRIPTION, '"')                                                           description,
                                'EGS'                                                                                       itemType,
                                'EG-484380486-' || mst.item_code                                                            itemCode,
                                mst.internalCode                                                                            internalCode,
                                mst.TAXABLE_TYPES                                                                           TAXABLE_TYPES,
                                CASE WHEN TAX_CLASSIFICATION_CODE = 'INPUT S_T 0%' THEN 'V003' ELSE MST.TAX_SUBTYPES END    TAX_SUBTYPES,
                                mst.uom                                                                                     unitType,
                                ABS (QUANTITY_CREDITED)                                                                     quantity,
                                ROUND (NVL (UNIT_SELLING_PRICE, 0), 5)                                                      unitPrice,
                                ROUND (NVL (REVENUE_AMOUNT, 0), 5)                                                          salesTotal,
                                ROUND (
                                      NVL (REVENUE_AMOUNT, 0)
                                    + NVL (TAX_RECOVERABLE, 0)
                                    + NVL ((SELECT ROUND ((NVL (PAV.ADJUSTED_AMOUNT, 0)) * NVL (d.quantity_invoiced, 0), 2)
                                              FROM APPS.OE_PRICE_ADJUSTMENTS_V PAV
                                             WHERE PAV.LIST_LINE_TYPE_CODE = 'FREIGHT_CHARGE' AND PAV.LINE_ID = INTERFACE_LINE_ATTRIBUTE6),
                                           0),
                                    5)                                                                                      total,
                                CASE
                                    WHEN     (SELECT mst.TAX_SUBTYPES
                                                FROM prd.atr_E_INVOICE_TAXABLE_SUBTYPES ts
                                               WHERE ts.TAXABLE_CODE = mst.TAX_SUBTYPES) IN ('V009')
                                         AND d.unit_selling_price = 0
                                    THEN
                                        ROUND (
                                            (SELECT ROUND (
                                                          ROUND ((NVL (PAV.ADJUSTED_AMOUNT, 0)) * NVL (ctal.quantity_invoiced, 0), 2)
                                                        * 100
                                                        / 14,
                                                        5)    fre
                                               FROM APPS.OE_PRICE_ADJUSTMENTS_V PAV, AG.EVA_RA_CUSTOMER_TRX_LINES_ALL CTAL
                                              WHERE     PAV.LIST_LINE_TYPE_CODE = 'FREIGHT_CHARGE'
                                                    AND PAV.LINE_ID = CTAL.INTERFACE_LINE_ATTRIBUTE6
                                                    AND NVL (CTAL.UNIT_SELLING_PRICE, 0) = 0
                                                    AND ctal.CUSTOMER_TRX_ID = P_RECEIPT_ID
                                                    AND PAV.LINE_ID(+) = d.INTERFACE_LINE_ATTRIBUTE6),
                                            5)
                                    --   round(nvl(d.unit_standard_price,0) * nvl(d.quantity_invoiced,0),5)
                                    WHEN     ROUND (NVL (TAX_RECOVERABLE, 0), 5) <>
                                             TRUNC ((  NVL (REVENUE_AMOUNT, 0)
                                                     * (  (SELECT ts.TAX_VALUE
                                                             FROM prd.atr_E_INVOICE_TAXABLE_SUBTYPES ts
                                                            WHERE ts.TAXABLE_CODE = mst.TAX_SUBTYPES)
                                                        / 100)),
                                                    2)
                                         AND (SELECT mst.TAX_SUBTYPES
                                                FROM prd.atr_E_INVOICE_TAXABLE_SUBTYPES ts
                                               WHERE ts.TAXABLE_CODE = mst.TAX_SUBTYPES) IN ('V010')
                                    THEN
                                          ROUND (
                                                (  (ROUND (((  UNIT_SELLING_PRICE
                                                             * QUANTITY_INVOICED
                                                             * (  (SELECT ts.TAX_VALUE
                                                                     FROM prd.atr_E_INVOICE_TAXABLE_SUBTYPES ts
                                                                    WHERE ts.TAXABLE_CODE = mst.TAX_SUBTYPES)
                                                                / 100))),
                                                           5))
                                                 - (  (NVL (REVENUE_AMOUNT, 0) + NVL (TAX_RECOVERABLE, 0))
                                                    - ROUND (NVL (UNIT_SELLING_PRICE, 0) * NVL (QUANTITY_INVOICED, 0), 5)))
                                              * (100 / 14),
                                              5)
                                        * -1
                                    ELSE
                                        0
                                END                                                                                         valueDifference,
                                0                                                                                           totalTaxableFees,
                                --nvl(REVENUE_AMOUNT,0) + nvl(TAX_RECOVERABLE,0)
                                ROUND (NVL (REVENUE_AMOUNT, 0), 5)                                                          netTotal,
                                0                                                                                           itemsDiscount,
                                SALES_ORDER,
                                SALES_ORDER_DATE,
                                LINE_TYPE,
                                ROUND (EXTENDED_AMOUNT, 5)                                                                  EXTENDED_AMOUNT,
                                ROUND (LINE_RECOVERABLE, 5)                                                                 LINE_RECOVERABLE,
                                ROUND (TAX_RECOVERABLE, 5),
                                TAX_CLASSIFICATION_CODE
                  FROM AG.EVA_RA_CUSTOMER_TRX_ALL        h,
                       AG.EVA_RA_CUSTOMER_TRX_LINES_ALL  d,
                       mst,
                       CTAL
                 WHERE     h.CUSTOMER_TRX_ID = d.CUSTOMER_TRX_ID
                       AND h.CUSTOMER_TRX_ID = P_RECEIPT_ID
                       AND d.INVENTORY_ITEM_ID = mst.INVENTORY_ITEM_ID
                       AND d.CUSTOMER_TRX_LINE_ID <> 55590039                                                                             --22-05-2024
                       AND LINE_TYPE = 'LINE'
                       AND CTAL.CUSTOMER_TRX_LINE_ID(+) = d.CUSTOMER_TRX_LINE_ID
                       AND d.CUSTOMER_TRX_LINE_ID <> 36084217                                                                             --06/06/2023
                                                             )
        LOOP
            APEX_JSON.open_array ('itemData');
            APEX_JSON.open_object;
            APEX_JSON.write ('internalCode', UPPER (cur_rec.internalCode));
            APEX_JSON.write ('description', UPPER (cur_rec.description));
            APEX_JSON.write ('itemType', UPPER (cur_rec.itemType));
            APEX_JSON.write ('itemCode', UPPER (cur_rec.itemCode));
            APEX_JSON.write ('unitType', UPPER (cur_rec.unitType));
            APEX_JSON.write ('quantity', UPPER (NVL (cur_rec.quantity, 0)));
            APEX_JSON.write ('unitPrice', UPPER (cur_rec.unitPrice));
            APEX_JSON.write ('netSale', UPPER (ABS (cur_rec.netTotal)));
            APEX_JSON.write ('totalSale', UPPER (ABS (cur_rec.netTotal)));
            APEX_JSON.write ('total', UPPER (ABS (cur_rec.total)));
            -------------------------------------------
            APEX_JSON.open_array ('commercialDiscountData');
            APEX_JSON.open_object;
            APEX_JSON.open_array ('commercialDiscountData');
            APEX_JSON.open_object;
            APEX_JSON.write ('amount', '0');
            APEX_JSON.write ('description', '0');
            APEX_JSON.write ('rate', '0');
            APEX_JSON.close_object;
            APEX_JSON.close_array;
            APEX_JSON.close_object;
            APEX_JSON.close_array;
            -------------------------------------------
            APEX_JSON.open_array ('itemDiscountData');
            APEX_JSON.open_object;
            APEX_JSON.open_array ('itemDiscountData');
            APEX_JSON.open_object;
            APEX_JSON.write ('amount', '0');
            APEX_JSON.write ('description', '0');
            APEX_JSON.write ('rate', '0');
            APEX_JSON.close_object;
            APEX_JSON.close_array;
            APEX_JSON.close_object;
            APEX_JSON.close_array;
            -------------------------------------------
            APEX_JSON.open_object ('additionalCommercialDiscount');
            APEX_JSON.write ('amount', '0');
            APEX_JSON.write ('description', '0');
            APEX_JSON.write ('rate', '0');
            APEX_JSON.close_object;
            -------------------------------------------
            APEX_JSON.open_object ('additionalItemDiscount');
            APEX_JSON.write ('amount', '0');
            APEX_JSON.write ('description', '0');
            APEX_JSON.write ('rate', '0');
            APEX_JSON.close_object;
            -------------------------------------------
            APEX_JSON.write ('valueDifference', UPPER (cur_rec.valueDifference));
            -------------------------------------------
            APEX_JSON.open_array ('taxableItems');
            APEX_JSON.open_object;

            FOR tax
                IN (SELECT tax.TAX_RATE_CODE,
                           PERCENTAGE_RATE,
                             d.TAX_RECOVERABLE
                           + NVL ((SELECT ROUND ((NVL (PAV.ADJUSTED_AMOUNT, 0)) * NVL (d.quantity_invoiced, 0), 2)
                                     FROM APPS.OE_PRICE_ADJUSTMENTS_V PAV
                                    WHERE PAV.LIST_LINE_TYPE_CODE = 'FREIGHT_CHARGE' AND PAV.LINE_ID = INTERFACE_LINE_ATTRIBUTE6),
                                  0)    TAX_RECOVERABLE
                      FROM ZX.ZX_RATES_B TAX, AG.EVA_RA_CUSTOMER_TRX_LINES_ALL d
                     WHERE     1 = 1
                           AND NVL (tax.ACTIVE_FLAG, 'Y') = 'Y'
                           AND d.TAX_CLASSIFICATION_CODE = TAX.TAX_RATE_CODE                                   -- and TAX.TAX_RATE_CODE ='PH_AR_P_14%'
                           AND SYSDATE BETWEEN TAX.EFFECTIVE_FROM AND NVL (TAX.EFFECTIVE_TO, SYSDATE + 1)
                           AND d.CUSTOMER_TRX_LINE_ID = cur_rec.CUSTOMER_TRX_LINE_ID)
            LOOP
                SELECT s.TAX_VALUE
                  INTO l_TAX_VALUE
                  FROM prd.atr_E_INVOICE_Taxable_Subtypes s
                 WHERE cur_rec.TAX_SUBTYPES = s.TAXABLE_CODE AND ROWNUM = 1;

                --                APEX_JSON.open_array ('taxableItems');
                --                APEX_JSON.open_object;
                APEX_JSON.open_array ('taxableItems');
                APEX_JSON.open_object;
                APEX_JSON.write ('taxType', NVL (UPPER (cur_rec.TAXABLE_TYPES), '0'));
                APEX_JSON.write (
                    'amount',
                    CASE
                        WHEN MOD (NVL (tax.TAX_RECOVERABLE, 0), 1) = 0 THEN TO_CHAR (NVL (tax.TAX_RECOVERABLE, 0), 'FM9999999990')
                        ELSE TO_CHAR (NVL (tax.TAX_RECOVERABLE, 0), 'FM9999999990.99')
                    END);
                APEX_JSON.write ('subType', NVL (UPPER (cur_rec.TAX_SUBTYPES), '0'));
                APEX_JSON.write ('rate', NVL (UPPER (l_TAX_VALUE), '0'));
                --                APEX_JSON.close_object;
                --                APEX_JSON.close_array;
                APEX_JSON.close_object;
                APEX_JSON.close_array;
            END LOOP;

            APEX_JSON.close_object;
            APEX_JSON.close_array;

            -------------------------------------------
            APEX_JSON.close_object;
            APEX_JSON.close_array;
        END LOOP;

        APEX_JSON.close_object;
        APEX_JSON.close_array;

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------
        WITH
            FR
            AS
                (SELECT ROUND ((NVL (PAV.ADJUSTED_AMOUNT, 0)) * NVL (ctal.quantity_invoiced, 0), 2) fre, PAV.LINE_ID
                   FROM APPS.OE_PRICE_ADJUSTMENTS_V PAV, AG.EVA_RA_CUSTOMER_TRX_LINES_ALL CTAL
                  WHERE     PAV.LIST_LINE_TYPE_CODE = 'FREIGHT_CHARGE'
                        AND PAV.LINE_ID = CTAL.INTERFACE_LINE_ATTRIBUTE6
                        AND NVL (CTAL.UNIT_SELLING_PRICE, 0) = 0
                        AND ctal.CUSTOMER_TRX_ID = P_RECEIPT_ID)
        SELECT ROUND (SUM (NVL (REVENUE_AMOUNT, 0)), 2)                                                 total_inv,
               ROUND (SUM (NVL (TAX_RECOVERABLE, 0)), 2)                                                total_tax,
               ROUND (SUM (NVL (REVENUE_AMOUNT, 0)), 2) + ROUND (SUM (NVL (TAX_RECOVERABLE, 0)), 2)     total_invoice
          INTO l_total_sales_invoice, l_total_tax, l_total_invoice
          FROM (SELECT NVL (REVENUE_AMOUNT, 0) REVENUE_AMOUNT, NVL (TAX_RECOVERABLE, 0) + NVL (fr.fre, 0) TAX_RECOVERABLE
                  --          INTO l_total_sales_invoice, l_total_tax, l_total_invoice
                  FROM AG.EVA_RA_CUSTOMER_TRX_ALL h, AG.EVA_RA_CUSTOMER_TRX_LINES_ALL d, FR
                 WHERE     h.CUSTOMER_TRX_ID = d.CUSTOMER_TRX_ID
                       AND h.CUSTOMER_TRX_ID = P_RECEIPT_ID
                       AND LINE_TYPE = 'LINE'
                       AND FR.LINE_ID(+) = d.INTERFACE_LINE_ATTRIBUTE6);

        APEX_JSON.write ('totalSales', UPPER (ABS (l_total_sales_invoice)));
        APEX_JSON.write ('totalCommercialDiscount', '0');
        APEX_JSON.write ('totalItemsDiscount', '0');

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------

        APEX_JSON.open_array ('extraReceiptDiscountData');
        APEX_JSON.open_object;
        APEX_JSON.open_array ('extraReceiptDiscountData');
        APEX_JSON.open_object;
        APEX_JSON.write ('amount', '0');
        APEX_JSON.write ('description', '0');
        APEX_JSON.write ('rate', '0');
        APEX_JSON.close_object;
        APEX_JSON.close_array;
        APEX_JSON.close_object;
        APEX_JSON.close_array;

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------

        APEX_JSON.write ('netAmount', UPPER (ABS (l_total_sales_invoice)));
        APEX_JSON.write ('feesAmount', '0');
        APEX_JSON.write ('totalAmount', UPPER (ABS (l_total_invoice)));

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------

        APEX_JSON.open_array ('taxTotals');
        APEX_JSON.open_object;
        APEX_JSON.open_array ('taxTotals');
        APEX_JSON.open_object;
        APEX_JSON.write ('taxType', 'T1');
        APEX_JSON.write ('amount', NVL (UPPER (ABS (l_total_tax)), '0'));
        APEX_JSON.close_object;
        APEX_JSON.close_array;
        APEX_JSON.close_object;
        APEX_JSON.close_array;

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------

        APEX_JSON.write ('paymentMethod', 'V');
        APEX_JSON.write ('adjustment', '0');

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------

        APEX_JSON.open_object ('contractor');
        APEX_JSON.write ('name', '0');
        APEX_JSON.write ('amount', '0');
        APEX_JSON.write ('rate', '0');
        APEX_JSON.close_object;

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------

        APEX_JSON.open_object ('beneficiary');
        APEX_JSON.write ('amount', '0');
        APEX_JSON.write ('rate', '0');
        APEX_JSON.close_object;

        -----------------------------------------------------------------------------
        -----------------------------------------------------------------------------
        --        APEX_JSON.close_object;
        APEX_JSON.close_object;
        L_json_2                  := apex_json.get_clob_output;
        L_json_2                  := REPLACE (L_json_2, '"uuid":" "', '"uuid":""');
        --        L_json_2               := REPLACE (L_json_2, '"previousUUID":" "', '"previousUUID":""');
        L_json_2                  := REPLACE (L_json_2, '"referenceOldUUID":" "', '"referenceOldUUID":""');
        L_json_2                  := REPLACE (L_json_2, '"referenceUUID":" "', '"referenceUUID":""');
        L_json_2                  := REPLACE (L_json_2, '"id":" "', '"id":""');

        --        dbms_output.put_line(L_json_2);

        SELECT JSON_QUERY (L_json_2, '$' RETURNING CLOB) INTO l_body_2 FROM DUAL;


        l_json_for_serialize      := l_body_2;
        obj                       := l_body;

        --        DBMS_OUTPUT.put_line ('for serialize' || l_json_for_serialize);
        --        DBMS_OUTPUT.put_line ('for send' || obj);

        SELECT TO_CLOB (
                   (UPPER (
                        REPLACE (REPLACE (REPLACE (REPLACE (REPLACE ((SELECT l_json_for_serialize FROM DUAL), '{', ''), '}', ''), ',', ''), '[', ''),
                                 ']',
                                 ''))))
          INTO l_serialization
          FROM DUAL;

        --        l_serialization := replace ((l_serialization),'"RECEIPTTYPE""R"','"RECEIPTTYPE""r"');

        SELECT DBMS_LOB.SUBSTR (l_serialization, 4000, '50') INTO l_after_time FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (l_serialization, 4000, '4050') INTO l_after_time_2 FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (l_serialization, 4000, '8050') INTO l_after_time_3 FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (l_serialization, 4000, '12050') INTO l_after_time_4 FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (l_serialization, 4000, '16050') INTO l_after_time_5 FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (l_serialization, 4000, '20050') INTO l_after_time_6 FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (l_serialization, 4000, '24050') INTO l_after_time_7 FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (l_serialization, 4000, '28050') INTO l_after_time_8 FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (l_serialization, 4000, '32050') INTO l_after_time_9 FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (l_serialization, 4000, '36050') INTO l_after_time_10 FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (l_serialization, 4000, '40050') INTO l_after_time_11 FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (l_serialization, 4000, '44050') INTO l_after_time_12 FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (l_serialization, 26, '1') INTO l_before_time FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (l_serialization, 23, '27') INTO l_time FROM DUAL;

        SELECT    REPLACE (l_before_time, ':', '')
               || l_time
               || REPLACE (l_after_time, ':', '')
               || REPLACE (l_after_time_2, ':', '')
               || REPLACE (l_after_time_3, ':', '')
               || REPLACE (l_after_time_4, ':', '')
               || REPLACE (l_after_time_5, ':', '')
               || REPLACE (l_after_time_6, ':', '')
               || REPLACE (l_after_time_7, ':', '')
               || REPLACE (l_after_time_8, ':', '')
               || REPLACE (l_after_time_9, ':', '')
               || REPLACE (l_after_time_10, ':', '')
               || REPLACE (l_after_time_11, ':', '')
               || REPLACE (l_after_time_12, ':', '')
          INTO l_final_serialization
          FROM DUAL;


        v_start                   := INSTR (l_final_serialization, 'SALESISSUEDDATETIME""') + LENGTH ('SALESISSUEDDATETIME""') + 11; -- إضافة 10 لحساب التاريخ
        v_timeString              := SUBSTR (l_final_serialization, v_start, 6);
        v_newTimeString           := SUBSTR (v_timeString, 1, 2) || ':' || SUBSTR (v_timeString, 3, 2) || ':' || SUBSTR (v_timeString, 5, 2);
        l_final_serialization_2   := SUBSTR (l_final_serialization, 1, v_start - 1) || v_newTimeString || SUBSTR (l_final_serialization, v_start + 6);

        -- 2024-10-21T0:73:624Z



        --        SELECT REGEXP_REPLACE (l_final_serialization, 'T000000Z"', 'T00:00:00Z"') INTO l_final_serialization_2 FROM DUAL;

        --        SELECT REGEXP_REPLACE (l_final_serialization, '"RECEIPTTYPE""RWR"', '"RECEIPTTYPE""RWR"') INTO l_final_serialization_2 FROM DUAL;

        SELECT sys.DBMS_CRYPTO.hash (src => (l_final_serialization_2), typ => 4) INTO l_hash FROM DUAL;

        SELECT DBMS_LOB.INSTR (obj, 'uuid') + 6 INTO l_instr_1 FROM DUAL;

        SELECT DBMS_LOB.INSTR (obj, 'uuid') + 7 INTO l_instr_2 FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (l_serialization, 4000, l_instr_2) INTO l_substr FROM DUAL;


        SELECT DBMS_LOB.SUBSTR (obj, l_instr_1, 1) INTO f_json FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (obj, 18, l_instr_2) INTO last_json FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (obj, 4000, 121) INTO l_last_json FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (obj, 4000, 4121) INTO l_last_json_2 FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (obj, 4000, 8121) INTO l_last_json_3 FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (obj, 4000, 12121) INTO l_last_json_4 FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (obj, 4000, 16121) INTO l_last_json_5 FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (obj, 4000, 20121) INTO l_last_json_6 FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (obj, 4000, 24121) INTO l_last_json_7 FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (obj, 4000, 28121) INTO l_last_json_8 FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (obj, 4000, 32121) INTO l_last_json_9 FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (obj, 4000, 36121) INTO l_last_json_10 FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (obj, 4000, 40121) INTO l_last_json_11 FROM DUAL;

        SELECT DBMS_LOB.SUBSTR (obj, 4000, 44121) INTO l_last_json_12 FROM DUAL;



        SELECT    f_json
               || l_hash
               || last_json
               || l_last_json
               || l_last_json_2
               || l_last_json_3
               || l_last_json_4
               || l_last_json_5
               || l_last_json_6
               || l_last_json_7
               || l_last_json_8
               || l_last_json_9
               || l_last_json_10
               || l_last_json_11
               || l_last_json_12
          INTO l_final_json
          FROM DUAL;



        SELECT '"' || REPLACE ((l_final_json), '"', '\"') || '"' INTO l_body_wo_sign FROM DUAL;

        --        SELECT SUBSTR(l_body_wo_sign, 1, LENGTH(l_body_wo_sign) - 2) into l_try FROM dual;

        --        SELECT SUBSTR(l_body_wo_sign, 1, LENGTH(l_body_wo_sign) - 3) || SUBSTR(l_body_wo_sign, LENGTH(l_body_wo_sign)) into l_try FROM dual;

        SELECT    SUBSTR (l_body_wo_sign, 1, 1)
               || SUBSTR (l_body_wo_sign, 17, LENGTH (l_body_wo_sign) - 19)
               || SUBSTR (l_body_wo_sign, LENGTH (l_body_wo_sign))
          INTO l_try
          FROM DUAL;


        DBMS_OUTPUT.put_line ('uuid' || l_hash);

        --        SELECT REGEXP_REPLACE (l_final_json, '"receiptType":"RWR"', '"receiptType":"rwr"') INTO l_final_json FROM DUAL;

        get_invoice_signature (l_final_json,
                               P_server,
                               l_response,
                               l_out_signature);



        SELECT SUBSTR (REGEXP_SUBSTR (l_response, 'uuid.*",'), 8, REGEXP_INSTR (REGEXP_SUBSTR (l_response, 'uuid.*",'), '",') - 8)     uuid
          INTO l_uuid
          FROM DUAL;

        --
        --
        l_url_API                 := get_url (P_server, 'API') || '/api/v1/receiptsubmissions';

        --          l_response :=
        --            apex_web_service.make_rest_request (
        --                p_url           => l_url_API,
        --                p_http_method   => 'POST',
        --                p_body          => l_final_json,
        --                p_wallet_path   => get_wallet_path,
        --                p_wallet_pwd    => get_wallet_pwd );
        --        /* Parsing Webservice Response as JSON */
        ----        apex_json.parse (l_response);
        --        SELECT SUBSTR (
        --                   REGEXP_SUBSTR (l_response, 'uuid.*",'),
        --                   8,
        --                     REGEXP_INSTR (REGEXP_SUBSTR (l_response, 'uuid.*",'),
        --                                   '",')
        --                   - 8)    uuid
        --          INTO l_uuid
        --          FROM DUAL;



        --dbms_output.put_line('uuid'||l_uuid);

        l_debug_result_id         := PRD.ATR_E_RECEIPT_DEBUG_RESULT_SEQ.NEXTVAL;

        --l_url_API   := get_url (P_server, 'API') || '/api/v1/receipts/:submissionUuid/details';


        INSERT INTO PRD.ATR_E_RECEIPT_DEBUG_RESULT (DEBUG_RESULT_ID,
                                                    URL,
                                                    STATUS_CODE,
                                                    WEB_SERVICE_NAME,
                                                    WEB_SERVICE_METHOD,
                                                    DEBUG_RESULT,
                                                    JSON_WITHOUT_SIGNATURE,
                                                    NODE_NAME,
                                                    CREATION_DATE,
                                                    CREATED_BY,
                                                    LAST_UPDATE_BY,
                                                    LAST_UPDATED_DATE,
                                                    SERIALIZATION,
                                                    Final_JSON,
                                                    UUID,
                                                    JSON_WITH_SIGNATURE,
                                                    response)
             VALUES (l_debug_result_id,
                     l_url_API,
                     apex_web_service.g_status_code,
                     '5.1 Submit Documents no reference (JSON)',
                     'POST',
                     l_response,
                     l_body,
                     --                     l_out_signature,
                     P_server,
                     SYSDATE,
                     P_PERSON_ID,
                     P_PERSON_ID,
                     SYSDATE,
                     l_final_serialization_2,
                     l_final_json,
                     l_hash,
                     l_out_signature,
                     l_get_response_f);

        COMMIT;

        SELECT JSON_VALUE (debug_result, '$.receipt.status' RETURNING VARCHAR2)
          INTO l_status
          FROM PRD.ATR_E_RECEIPT_DEBUG_RESULT
         WHERE debug_result_id = l_debug_result_id;

        INSERT INTO PRD.ATR_E_RECEIPT_HISTORY (DEBUG_RESULT_ID,
                                               INVOICE_ID,
                                               INVOICE_NUMBER,
                                               UUID,
                                               typeName,
                                               status,
                                               NODE_NAME,
                                               CREATION_DATE,
                                               CREATED_BY,
                                               LAST_UPDATE_BY,
                                               LAST_UPDATED_DATE)
             VALUES (l_debug_result_id,
                     P_RECEIPT_ID,
                     l_TRX_NUMBER,
                     l_uuid,
                     'I',
                     l_status,
                     P_server,
                     SYSDATE,
                     P_PERSON_ID,
                     P_PERSON_ID,
                     SYSDATE);

        COMMIT;
    END Submit_Documents_no_reference;



    PROCEDURE AutoSubmit_RECEIPT (errbuf OUT NOCOPY VARCHAR2, retcode OUT NOCOPY NUMBER)
    IS
    BEGIN
        FOR i IN (  SELECT h.CUSTOMER_TRX_ID
                      FROM APPS.EVA_RA_CUSTOMER_TRX_ALL h, AG.EVA_RA_CUSTOMER_TRX_LINES_ALL d
                     WHERE     1 = 1
                           AND h.TRX_DATE >= TRUNC (SYSDATE, 'yyyy')
                           AND h.ORG_ID = 1963
                           AND h.CUSTOMER_TRX_ID = d.CUSTOMER_TRX_ID
                           AND BILL_TO_CUSTOMER_ID IN (1836040,
                                                       2468432,
                                                       1339188,
                                                       2519757,
                                                       2596516,
                                                       2658528)
                           AND h.BATCH_SOURCE_ID NOT IN (2001, 70096, 61096)
                           AND EXISTS
                                   (SELECT 1
                                      FROM AR.RA_CUST_TRX_TYPES_ALL trx
                                     WHERE trx.CUST_TRX_TYPE_ID = h.CUST_TRX_TYPE_ID AND TYPE = 'INV')
                           AND NOT EXISTS
                                   (SELECT 1
                                      FROM PRD.ATR_E_RECEIPT_HISTORY r
                                     WHERE     h.CUSTOMER_TRX_ID = r.INVOICE_ID
                                           AND NODE_NAME = 'Prod'
                                           AND (   status IN ('Valid',
                                                              'InProgress',
                                                              'valid',
                                                              'invalid',
                                                              'Invalid',
                                                              'Submitted')
                                                OR uuid IS NULL
                                                OR status IS NULL))
                           AND NOT EXISTS
                                   (SELECT 1
                                      FROM PRD.ATR_E_INVOICE_HISTORY r
                                     WHERE     h.CUSTOMER_TRX_ID = r.INVOICE_ID
                                           AND NODE_NAME = 'Prod'
                                           AND (   status IN ('Valid',
                                                              'InProgress',
                                                              'valid',
                                                              'invalid',
                                                              'Invalid',
                                                              'Submitted')
                                                OR uuid IS NULL
                                                OR status IS NULL))
                  GROUP BY h.CUSTOMER_TRX_ID)
        LOOP
            Submit_Documents_JSON (i.CUSTOMER_TRX_ID, -1, 'Prod');
        END LOOP;


        FOR j IN (  SELECT h.CUSTOMER_TRX_ID
                      FROM APPS.EVA_RA_CUSTOMER_TRX_ALL h, AG.EVA_RA_CUSTOMER_TRX_LINES_ALL d
                     WHERE     1 = 1
                           AND h.TRX_DATE >= TRUNC (SYSDATE, 'yyyy')
                           AND h.ORG_ID = 1963
                           AND BILL_TO_CUSTOMER_ID IN (1836040)                                                                             --,2468432
                           AND h.BATCH_SOURCE_ID NOT IN (2001, 70096, 61096)
                           --         AND h.BATCH_SOURCE_ID <> 2001
                           --         AND h.BATCH_SOURCE_ID <> 70096
                           AND h.CUSTOMER_TRX_ID = d.CUSTOMER_TRX_ID
                           --         AND h.INVOICE_CURRENCY_CODE = 'EGP'
                           AND EXISTS
                                   (SELECT 1
                                      FROM AR.RA_CUST_TRX_TYPES_ALL trx
                                     WHERE trx.CUST_TRX_TYPE_ID = h.CUST_TRX_TYPE_ID AND TYPE = 'CM')
                           AND NOT EXISTS
                                   (SELECT 1
                                      FROM PRD.ATR_E_RECEIPT_HISTORY r
                                     WHERE     h.CUSTOMER_TRX_ID = r.INVOICE_ID
                                           AND NODE_NAME = 'Prod'
                                           AND (   status IN ('Valid',
                                                              'InProgress',
                                                              'valid',
                                                              'invalid',
                                                              'Invalid',
                                                              'Submitted')
                                                OR uuid IS NULL
                                                OR status IS NULL))
                           AND NOT EXISTS
                                   (SELECT 1
                                      FROM PRD.ATR_E_INVOICE_HISTORY r
                                     WHERE     h.CUSTOMER_TRX_ID = r.INVOICE_ID
                                           AND NODE_NAME = 'Prod'
                                           AND (   status IN ('Valid',
                                                              'InProgress',
                                                              'valid',
                                                              'invalid',
                                                              'Invalid',
                                                              'Submitted')
                                                OR uuid IS NULL
                                                OR status IS NULL))
                  GROUP BY h.CUSTOMER_TRX_ID)
        LOOP
            Submit_Documents_Credit (j.CUSTOMER_TRX_ID, -1, 'Prod');
        END LOOP;

        DBMS_SESSION.SLEEP (40);

        FOR rec IN (SELECT uuid
                      FROM PRD.ATR_E_RECEIPT_DEBUG_RESULT
                     WHERE     TRUNC (CREATION_DATE) = TRUNC (SYSDATE)
                           AND UUID IS NOT NULL
                           AND WEB_SERVICE_METHOD = 'POST'
                           AND NOT EXISTS
                                   (SELECT 1
                                      FROM PRD.ATR_E_RECEIPT_DEBUG_RESULT T2
                                     WHERE T2.UUID = PRD.ATR_E_RECEIPT_DEBUG_RESULT.UUID AND T2.WEB_SERVICE_METHOD = 'GET'))
        LOOP
            PRD.ATR_ELECTRONIC_RECEIPT.get_receipt (rec.uuid);
            DBMS_SESSION.SLEEP (1);
        END LOOP;


        COMMIT;
    END AutoSubmit_RECEIPT;



    PROCEDURE AutoGET_RECEIPT (errbuf OUT NOCOPY VARCHAR2, retcode OUT NOCOPY NUMBER)
    AS
    --    cursor cur IS
    --
    --SELECT uuid
    --  FROM PRD.ATR_E_RECEIPT_DEBUG_RESULT
    -- WHERE     TRUNC (CREATION_DATE) = TRUNC (SYSDATE)
    --       AND UUID IS NOT NULL
    --       AND WEB_SERVICE_METHOD = 'POST'
    --       AND NOT EXISTS
    --               (SELECT 1
    --                  FROM PRD.ATR_E_RECEIPT_DEBUG_RESULT T2
    --                 WHERE     T2.UUID = PRD.ATR_E_RECEIPT_DEBUG_RESULT.UUID
    --                       AND T2.WEB_SERVICE_METHOD = 'GET');

    BEGIN
        FOR rec IN (SELECT uuid
                      FROM PRD.ATR_E_RECEIPT_DEBUG_RESULT
                     WHERE     TRUNC (CREATION_DATE) = TRUNC (SYSDATE)
                           AND UUID IS NOT NULL
                           AND WEB_SERVICE_METHOD = 'POST'
                           AND NOT EXISTS
                                   (SELECT 1
                                      FROM PRD.ATR_E_RECEIPT_DEBUG_RESULT T2
                                     WHERE T2.UUID = PRD.ATR_E_RECEIPT_DEBUG_RESULT.UUID AND T2.WEB_SERVICE_METHOD = 'GET'))
        LOOP
            PRD.ATR_ELECTRONIC_RECEIPT.get_receipt (rec.uuid);
            DBMS_SESSION.SLEEP (0.5);
        END LOOP;
    END AutoGET_RECEIPT;
END ATR_ELECTRONIC_RECEIPT;
/