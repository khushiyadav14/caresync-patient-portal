# main.py
# CareSync Dashboard Backend
#
# This file is a FastAPI application.
# It connects to the MySQL database and provides two API endpoints.
# The Vue.js frontend will call these endpoints to get data.
#
# To run this file:
#   uvicorn main:app --reload
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

import mysql.connector
from mysql.connector import Error                            # connects to MySQL

# ── Create the FastAPI application ──────────────────────────────────────────
app = FastAPI(title='CareSync Dashboard API')

# ── CORS Configuration ───────────────────────────────────────────────────────
# CORS stands for Cross-Origin Resource Sharing.
# Without this, the browser will block the Vue.js page from calling this API.
# allow_origins=['*'] means: accept requests from any browser tab.
# In a production system, you would list specific allowed addresses.
app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['GET'],
    allow_headers=['*'],
)

# ── Database connection helper ───────────────────────────────────────────────
# This function creates a fresh connection to MySQL every time it is called.
# We do not reuse a single connection because MySQL closes idle connections.
def get_db():
    return mysql.connector.connect(
        host="127.0.0.1",
        port=3307,
        user="root",
        password="admin",
        database="caresync",
        use_pure=True
    )

# ── ENDPOINT 1: Summary numbers ──────────────────────────────────────────────
# URL: http://127.0.0.1:8000/summary
# Returns: total counts for patients, doctors, appointments, and bills
@app.get('/summary')
def get_summary():
    db     = get_db()
    cursor = db.cursor(dictionary=True)

    # Count active patients only (soft delete filter)
    cursor.execute('SELECT COUNT(*) AS total FROM patient WHERE is_deleted = 0')
    patients = cursor.fetchone()['total']

    # Count active doctors only
    cursor.execute('SELECT COUNT(*) AS total FROM doctor WHERE is_active = 1')
    doctors = cursor.fetchone()['total']

    # Count all appointments
    cursor.execute('SELECT COUNT(*) AS total FROM appointment')
    appointments = cursor.fetchone()['total']

    # Count all bills
    cursor.execute('SELECT COUNT(*) AS total FROM billing')
    bills = cursor.fetchone()['total']

    # Count rejected bills
    cursor.execute("SELECT COUNT(*) AS total FROM billing WHERE status = 'Rejected'")
    rejected = cursor.fetchone()['total']

    # Calculate rejection percentage
    rejection_rate = round((rejected / bills * 100), 1) if bills > 0 else 0

    # Total revenue collected
    cursor.execute('SELECT ROUND(SUM(amount_paid), 2) AS total FROM billing')
    revenue = cursor.fetchone()['total'] or 0

    cursor.close()
    db.close()

    # Return all values as a JSON object
    return {
        'total_patients':     patients,
        'total_doctors':      doctors,
        'total_appointments': appointments,
        'total_bills':        bills,
        'rejection_rate':     rejection_rate,
        'total_revenue':      float(revenue),
    }

# ── ENDPOINT 2: Patient list ─────────────────────────────────────────────────
# URL: http://127.0.0.1:8000/patients
# Returns: list of 50 most recent active patients
@app.get('/patients')
def get_patients():
    db     = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        '''
        SELECT
            patient_id,
            full_name,
            gender,
            blood_group,
            DATE_FORMAT(date_of_birth, '%d %b %Y') AS date_of_birth,
            DATE_FORMAT(created_at,    '%d %b %Y') AS registered_on
        FROM patient
        WHERE is_deleted = 0
        ORDER BY created_at DESC
        LIMIT 50
        '''
    )
    patients = cursor.fetchall()

    cursor.close()
    db.close()

    return {'patients': patients}

# ── ENDPOINT 3: Billing summary ──────────────────────────────────────────────
# URL: http://127.0.0.1:8000/billing
# Returns: recent 50 bills with patient name and status
@app.get('/billing')
def get_billing():
    db     = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        '''
        SELECT
            b.bill_id,
            p.full_name                           AS patient_name,
            b.total_amount,
            b.amount_paid,
            b.status,
            DATE_FORMAT(b.bill_date, '%d %b %Y') AS bill_date
        FROM billing b
        JOIN patient p ON p.patient_id = b.patient_id
        ORDER BY b.created_at DESC
        LIMIT 50
        '''
    )
    bills = cursor.fetchall()

    # Convert Decimal types to float so JSON serialisation works correctly
    for bill in bills:
        bill['total_amount'] = float(bill['total_amount'])
        bill['amount_paid']  = float(bill['amount_paid'])

    cursor.close()
    db.close()

    return {'bills': bills}

# ── ENDPOINT 4: Doctor list ──────────────────────────────────────────────────
# URL: http://127.0.0.1:8000/doctors
# Returns: all active doctors with appointment count
@app.get('/doctors')
def get_doctors():
    db     = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        '''
        SELECT
            d.doctor_id,
            d.full_name,
            d.specialisation,
            COUNT(a.appointment_id) AS total_appointments
        FROM doctor d
        LEFT JOIN appointment a ON a.doctor_id = d.doctor_id
            AND a.status = 'Completed'
        WHERE d.is_active = 1
        GROUP BY d.doctor_id, d.full_name, d.specialisation
        ORDER BY total_appointments DESC
        '''

    )
    doctors = cursor.fetchall()

    cursor.close()
    db.close()

    return {'doctors': doctors}

# ── ENDPOINT 5: Revenue Trend ─────────────────────────────────────────────────
# URL: http://127.0.0.1:8000/revenue-trend
# Returns: Monthly billed amount and collected amount for last 12 months

@app.get('/revenue-trend')
def get_revenue_trend():
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        '''
        SELECT
            DATE_FORMAT(bill_date, '%Y-%m') AS month_key,
            DATE_FORMAT(bill_date, '%b %Y') AS month,
            ROUND(SUM(total_amount), 2) AS billed,
            ROUND(SUM(amount_paid), 2) AS collected
        FROM billing
        WHERE bill_date >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH)
        GROUP BY
            DATE_FORMAT(bill_date, '%Y-%m'),
            DATE_FORMAT(bill_date, '%b %Y')
        ORDER BY month_key
        '''
    )

    rows = cursor.fetchall()

    for row in rows:
        row['billed'] = float(row['billed'] or 0)
        row['collected'] = float(row['collected'] or 0)

    cursor.close()
    db.close()

    return {'revenue_trend': rows}


# ── ENDPOINT 6: Appointment Heatmap ───────────────────────────────────────────
# URL: http://127.0.0.1:8000/appointment-heatmap
# Returns: Appointment count grouped by weekday and hour

@app.get('/appointment-heatmap')
def get_appointment_heatmap():
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        '''
        SELECT
            WEEKDAY(appointment_date) AS day_number,
            DAYNAME(appointment_date) AS day,
            HOUR(appointment_time) AS hour,
            COUNT(*) AS total_appointments
        FROM appointment
        GROUP BY
            WEEKDAY(appointment_date),
            DAYNAME(appointment_date),
            HOUR(appointment_time)
        ORDER BY
            day_number,
            hour
        '''
    )

    rows = cursor.fetchall()

    cursor.close()
    db.close()

    return {'appointment_heatmap': rows}


# ── ENDPOINT 7: Blood Group Distribution ─────────────────────────────────────
# URL: http://127.0.0.1:8000/blood-group-distribution
# Returns: Number of active patients belonging to each blood group

@app.get('/blood-group-distribution')
def get_blood_group_distribution():
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        '''
        SELECT
            COALESCE(blood_group, 'Unknown') AS blood_group,
            COUNT(*) AS total_patients
        FROM patient
        WHERE is_deleted = 0
        GROUP BY blood_group
        ORDER BY total_patients DESC
        '''
    )

    rows = cursor.fetchall()

    cursor.close()
    db.close()

    return {'blood_group_distribution': rows}

@app.get('/patients/{patient_id}')
def get_patient_by_id(patient_id: int):

    db = None
    cursor = None

    try:
        db = get_db()

        cursor = db.cursor(dictionary=True)

        cursor.execute(
            '''
            SELECT
                patient_id,
                full_name,
                gender,
                blood_group,
                DATE_FORMAT(date_of_birth, '%d %b %Y') AS date_of_birth,
                DATE_FORMAT(created_at, '%d %b %Y %h:%i %p') AS registered_on
            FROM patient
            WHERE patient_id = %s
              AND is_deleted = 0
            ''',
            (patient_id,)
        )

        patient = cursor.fetchone()

        # Patient does not exist
        if patient is None:
            raise HTTPException(
                status_code=404,
                detail="Patient not found"
            )

        return {
            "patient": patient
        }

    except HTTPException:
        raise

    except mysql.connector.Error as e:
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )

    finally:

        if cursor:
            cursor.close()

        if db and db.is_connected():
            db.close()


            # ── ENDPOINT: Get Appointments by Patient ID ────────────────────────────────
# URL: http://127.0.0.1:8000/patients/{patient_id}/appointments
# Returns: All appointments linked to a specific patient

@app.get('/patients/{patient_id}/appointments')
def get_patient_appointments(patient_id: int):

    db = None
    cursor = None

    try:
        db = get_db()
        cursor = db.cursor(dictionary=True)

        # JOIN appointment table with patient table using patient_id
        cursor.execute(
            '''
            SELECT
                a.appointment_id,
                p.patient_id,
                p.full_name AS patient_name,
                a.doctor_id,
                DATE_FORMAT(
                    a.appointment_date,
                    '%d %b %Y'
                ) AS appointment_date,
                TIME_FORMAT(
                    a.appointment_time,
                    '%h:%i %p'
                ) AS appointment_time,
                a.status

            FROM appointment a

            JOIN patient p
                ON a.patient_id = p.patient_id

            WHERE p.patient_id = %s

            ORDER BY
                a.appointment_date DESC,
                a.appointment_time DESC
            ''',
            (patient_id,)
        )

        appointments = cursor.fetchall()

        # If the patient has no appointments,
        # return an empty list []
        return {
            "appointments": appointments
        }

    except mysql.connector.Error as e:

        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )

    finally:

        if cursor:
            cursor.close()

        if db and db.is_connected():
            db.close()


# ============================================================
# DOCTOR ANALYTICS
# ============================================================

@app.get("/analytics/doctors")
def get_doctor_analytics():

    connection = None
    cursor = None

    try:

        connection = get_db()

        cursor = connection.cursor(dictionary=True)

        query = """
            SELECT
                doctor_name,
                total_appointments AS appointment_count
            FROM vw_doctor_appointment_summary
            ORDER BY total_appointments DESC
        """

        cursor.execute(query)

        results = cursor.fetchall()

        return results

    except mysql.connector.Error as e:

        print("Database Error:", e)

        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )

    finally:

        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()