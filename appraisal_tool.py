import streamlit as st
import pandas as pd
import sqlite3
import re
import io
import os
import zipfile
import hashlib
import base64
from datetime import datetime

# ------------------------------------------------------------------------------
# 1. PAGE SETUP & CORPORATE BRAND STYLING
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="Goodday Enterprise Performance Appraisal Portal",
    page_icon="📋",
    layout="wide"
)

# Custom Corporate CSS matching Goodday Information Systems Palette
st.markdown("""
<style>
    /* Primary Goodday Theme Colors: Royal Blue (#1C509F) & Vibrant Orange (#F48220) */
    .header-container {
        display: flex;
        align-items: center;
        gap: 18px;
        margin-bottom: 10px;
    }
    .brand-header {
        color: #1C509F;
        font-weight: 800;
        font-size: 2.0rem;
        margin: 0px;
        line-height: 1.1;
    }
    .brand-subtext {
        color: #F48220;
        font-weight: 600;
        font-size: 1.05rem;
        margin-top: 4px;
    }
    .stButton>button {
        background-color: #1C509F !important;
        color: #ffffff !important;
        border-radius: 8px !important;
        border: none !important;
        font-weight: 600 !important;
    }
    .stButton>button:hover {
        background-color: #F48220 !important;
        color: #ffffff !important;
    }
    div[data-baseweb="tab-list"] {
        gap: 8px;
    }
    div[data-baseweb="tab"] {
        background-color: #f1f5f9;
        border-radius: 8px 8px 0px 0px;
        padding: 10px 20px;
        font-weight: 600;
        color: #334155;
    }
    div[aria-selected="true"] {
        background-color: #1C509F !important;
        color: #ffffff !important;
    }
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# 2. TRANSPARENT LOGO & ALIGNED HEADER HELPER FUNCTION
# ------------------------------------------------------------------------------
def get_image_base64(filepath):
    if os.path.exists(filepath):
        with open(filepath, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    return None

def render_brand_header():
    """Renders small, transparent logo perfectly aligned with text headers."""
    logo_filename = None
    for name in ["transparent_emblem.png", "transparent_logo.png", "gis logo_3.png", "gis logo_2.png", "gis_logo.png", "gis logo.png"]:
        if os.path.exists(name):
            logo_filename = name
            break

    b64_logo = get_image_base64(logo_filename) if logo_filename else None

    if b64_logo:
        # Mix-blend-mode ensures clean transparency blending across dark/light themes
        st.markdown(f"""
        <div class="header-container">
            <img src="data:image/png;base64,{b64_logo}" style="height: 60px; width: auto; background: transparent; mix-blend-mode: screen; border-radius: 4px;">
            <div>
                <div class="brand-header">Goodday Information Systems Pvt. Ltd.</div>
                <div class="brand-subtext">Enterprise Performance Appraisal Portal</div>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        col_logo, col_title = st.columns([1, 6])
        with col_logo:
            st.markdown("""
            <div style="background-color: #1C509F; padding: 8px; border-radius: 6px; text-align: center;">
                <span style="color: #F48220; font-size: 1.2rem; font-weight: bold;">Goodday</span>
            </div>
            """, unsafe_allow_html=True)
        with col_title:
            st.markdown('<div class="brand-header">Goodday Information Systems Pvt. Ltd.</div>', unsafe_allow_html=True)
            st.markdown('<div class="brand-subtext">Enterprise Performance Appraisal Portal</div>', unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# 3. EVALUATION CRITERIA & REMARKS MATRIX
# ------------------------------------------------------------------------------
CRITERIA_CONFIG = [
    {"sr": 1, "name": "Quality of Work", "weight": 20},
    {"sr": 2, "name": "Productivity / Target Achievement", "weight": 20},
    {"sr": 3, "name": "Attendance & Punctuality", "weight": 10},
    {"sr": 4, "name": "Teamwork & Collaboration", "weight": 10},
    {"sr": 5, "name": "Communication Skills", "weight": 10},
    {"sr": 6, "name": "Problem Solving Ability", "weight": 10},
    {"sr": 7, "name": "Initiative & Ownership", "weight": 10},
    {"sr": 8, "name": "Learning & Development", "weight": 5},
    {"sr": 9, "name": "Client Satisfaction", "weight": 5},
]

REMARKS_MATRIX = {
    "Quality of Work": {
        1: "Frequently produces inaccurate work requiring significant rework.",
        2: "Work quality is inconsistent and requires regular supervision.",
        3: "Delivers accurate work with occasional errors.",
        4: "Consistently delivers high-quality work with minimal errors.",
        5: "Produces exceptional work that exceeds quality standards and serves as a benchmark for others."
    },
    "Productivity / Target Achievement": {
        1: "Rarely meets assigned targets or deadlines.",
        2: "Meets some targets but requires improvement in consistency.",
        3: "Achieves most assigned targets within deadlines.",
        4: "Regularly exceeds targets and manages workload effectively.",
        5: "Consistently surpasses targets while maintaining excellent quality."
    },
    "Attendance & Punctuality": {
        1: "Frequent absenteeism and lateness affect performance.",
        2: "Attendance and punctuality need improvement.",
        3: "Maintains satisfactory attendance and punctuality.",
        4: "Reliable attendance with very few exceptions.",
        5: "Exemplary attendance and punctuality, setting a positive example."
    },
    "Teamwork & Collaboration": {
        1: "Has difficulty working effectively with team members.",
        2: "Participates in team activities but collaboration can improve.",
        3: "Works cooperatively with colleagues and contributes positively.",
        4: "Actively supports team success and promotes collaboration.",
        5: "Exceptional team player who inspires and unites others toward common goals."
    },
    "Communication Skills": {
        1: "Communication is unclear and often causes misunderstandings.",
        2: "Communication needs improvement in clarity and effectiveness.",
        3: "Communicates effectively in most situations.",
        4: "Expresses ideas clearly and professionally.",
        5: "Outstanding communicator who effectively influences and engages stakeholders."
    },
    "Problem Solving Ability": {
        1: "Struggles to identify and resolve issues independently.",
        2: "Requires guidance to solve routine problems.",
        3: "Resolves routine issues effectively.",
        4: "Proactively identifies problems and develops practical solutions.",
        5: "Demonstrates exceptional analytical thinking and resolves complex challenges efficiently."
    },
    "Initiative & Ownership": {
        1: "Rarely takes responsibility beyond assigned tasks.",
        2: "Occasionally shows initiative but needs encouragement.",
        3: "Takes ownership of assigned responsibilities.",
        4: "Frequently demonstrates initiative and accountability.",
        5: "Consistently takes proactive ownership and drives positive outcomes."
    },
    "Learning & Development": {
        1: "Shows limited interest in learning new skills.",
        2: "Participates in learning activities when required.",
        3: "Demonstrates willingness to learn and improve.",
        4: "Actively seeks opportunities for skill enhancement.",
        5: "Continuously develops new competencies and shares knowledge with others."
    },
    "Client Satisfaction": {
        1: "Receives frequent complaints or negative feedback.",
        2: "Customer/stakeholder expectations are not consistently met.",
        3: "Maintains satisfactory relationships and service levels.",
        4: "Regularly receives positive feedback from customers/stakeholders.",
        5: "Consistently exceeds expectations and builds strong stakeholder trust."
    }
}

FY_OPTIONS = [
    "-- Select Review Period --",
    "FY 2026-27",
    "FY 2027-28",
    "FY 2028-29",
    "FY 2029-30"
]

def clean_col_name(name: str) -> str:
    return re.sub(r'[^a-zA-Z0-9_]', '_', name).strip('_')

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

# ------------------------------------------------------------------------------
# 4. DATABASE SETUP & PERSISTENCE
# ------------------------------------------------------------------------------
DB_FILE = "appraisals.db"

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL,
            full_name TEXT NOT NULL
        );
    """)
    
    cursor.execute("SELECT COUNT(*) FROM users;")
    if cursor.fetchone()[0] == 0:
        cursor.execute(
            "INSERT INTO users (username, password_hash, role, full_name) VALUES (?, ?, ?, ?);",
            ("admin", hash_password("admin123"), "Super Admin", "Super Administrator")
        )
        cursor.execute(
            "INSERT INTO users (username, password_hash, role, full_name) VALUES (?, ?, ?, ?);",
            ("hr_user", hash_password("hr123"), "HR", "HR Manager")
        )
        cursor.execute(
            "INSERT INTO users (username, password_hash, role, full_name) VALUES (?, ?, ?, ?);",
            ("tl_mitesh", hash_password("tl123"), "Team Leader", "Alexander Wright")
        )

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS deleted_notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            emp_id TEXT NOT NULL,
            emp_name TEXT NOT NULL,
            team_leader TEXT,
            deleted_by TEXT,
            deleted_at TEXT
        );
    """)

    cols = [
        "id INTEGER PRIMARY KEY AUTOINCREMENT",
        "emp_name TEXT",
        "emp_id TEXT UNIQUE",
        "designation TEXT",
        "department TEXT",
        "team_leader TEXT",
        "review_period TEXT",
        "eval_date TEXT",
        "total_score REAL",
        "overall_rating TEXT",
        "is_locked INTEGER DEFAULT 1",
        "edit_requested INTEGER DEFAULT 0",
        "reeval_requested INTEGER DEFAULT 0",
        "last_updated_date TEXT",
        "last_updated_by TEXT"
    ]
    
    for crit in CRITERIA_CONFIG:
        safe_name = clean_col_name(crit['name'])
        cols.append(f"rating_{safe_name} INTEGER")
        cols.append(f"remarks_{safe_name} TEXT")
        
    query = f"CREATE TABLE IF NOT EXISTS appraisal_reviews ({', '.join(cols)});"
    cursor.execute(query)
    conn.commit()
    
    cursor.execute("PRAGMA table_info(appraisal_reviews);")
    existing_cols = [col['name'] for col in cursor.fetchall()]
    
    migrations = {
        "is_locked": "INTEGER DEFAULT 1",
        "edit_requested": "INTEGER DEFAULT 0",
        "reeval_requested": "INTEGER DEFAULT 0",
        "last_updated_date": "TEXT",
        "last_updated_by": "TEXT"
    }
    
    for col_name, col_type in migrations.items():
        if col_name not in existing_cols:
            cursor.execute(f"ALTER TABLE appraisal_reviews ADD COLUMN {col_name} {col_type};")
            
    conn.commit()
    conn.close()

init_db()

# ------------------------------------------------------------------------------
# 5. AUTHENTICATION & SESSION STATE
# ------------------------------------------------------------------------------
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
    st.session_state['username'] = None
    st.session_state['user_role'] = None
    st.session_state['full_name'] = None

def login_user(username, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ? AND password_hash = ?;", (username, hash_password(password)))
    user = cursor.fetchone()
    conn.close()
    
    if user:
        st.session_state['logged_in'] = True
        st.session_state['username'] = user['username']
        st.session_state['user_role'] = user['role']
        st.session_state['full_name'] = user['full_name']
        return True
    return False

def logout_user():
    st.session_state['logged_in'] = False
    st.session_state['username'] = None
    st.session_state['user_role'] = None
    st.session_state['full_name'] = None
    st.rerun()

# ------------------------------------------------------------------------------
# LOGIN SCREEN
# ------------------------------------------------------------------------------
if not st.session_state['logged_in']:
    render_brand_header()
    st.markdown("---")
    col_l1, col_l2, col_l3 = st.columns([1, 2, 1])
    with col_l2:
        with st.form("login_form"):
            st.subheader("🔐 Sign In")
            u_input = st.text_input("Username")
            p_input = st.text_input("Password", type="password")
            submit_login = st.form_submit_button("Login")
            
            if submit_login:
                if login_user(u_input, p_input):
                    st.success("Login successful!")
                    st.rerun()
                else:
                    st.error("Invalid username or password.")
    st.stop()

# ------------------------------------------------------------------------------
# 6. LOGGED-IN PORTAL HEADER & USER BAR
# ------------------------------------------------------------------------------
render_brand_header()

col_user, col_out = st.columns([3, 1])
with col_user:
    st.markdown(f"Logged in as: **{st.session_state['full_name']}** | Role: **`{st.session_state['user_role']}`**")
with col_out:
    if st.button("🚪 Logout"):
        logout_user()

st.markdown("---")

def get_default_remark(criteria_name: str, rating) -> str:
    if rating in [None, "-- Select Rating --", ""]:
        return ""
    try:
        return REMARKS_MATRIX.get(criteria_name, {}).get(int(rating), "")
    except (ValueError, TypeError):
        return ""

def get_overall_rating(total_score: float) -> str:
    if total_score >= 90:
        return "Outstanding"
    elif total_score >= 70:
        return "Exceeds Expectations"
    elif total_score >= 50:
        return "Meets Expectations"
    elif total_score >= 30:
        return "Growth Opportunity"
    else:
        return "Unsatisfactory"

def calculate_employee_scores(row) -> float:
    total = 0.0
    for crit in CRITERIA_CONFIG:
        c_name = crit['name']
        col_key = f"Rating: {c_name}" if f"Rating: {c_name}" in row else f"rating_{clean_col_name(c_name)}"
        val = row.get(col_key, None)
        try:
            rating = float(val) if val not in [None, "", "-- Select Rating --"] else 0.0
        except (ValueError, TypeError):
            rating = 0.0
        score = (crit['weight'] * rating) / 5.0
        total += score
    return round(total, 2)

def save_appraisal_to_db(record_dict, updated_by_user):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    total_score = calculate_employee_scores(record_dict)
    overall_rating = get_overall_rating(total_score)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    cursor.execute("DELETE FROM deleted_notifications WHERE emp_id = ?;", (record_dict.get("Employee ID"),))
    
    cols = [
        "emp_name", "emp_id", "designation", "department", "team_leader", 
        "review_period", "eval_date", "total_score", "overall_rating", 
        "is_locked", "edit_requested", "reeval_requested", "last_updated_date", "last_updated_by"
    ]
    vals = [
        record_dict.get("Employee Name"),
        record_dict.get("Employee ID"),
        record_dict.get("Designation"),
        record_dict.get("Department"),
        record_dict.get("Team Leader"),
        record_dict.get("Review Period"),
        record_dict.get("Date of Evaluation"),
        total_score,
        overall_rating,
        1,
        0,
        0,
        now_str,
        updated_by_user
    ]
    
    for crit in CRITERIA_CONFIG:
        c_name = crit['name']
        safe_name = clean_col_name(c_name)
        cols.append(f"rating_{safe_name}")
        cols.append(f"remarks_{safe_name}")
        vals.append(record_dict.get(f"Rating: {c_name}"))
        vals.append(record_dict.get(f"Remarks: {c_name}"))

    placeholders = ", ".join(["?"] * len(vals))
    col_names = ", ".join(cols)
    
    query = f"""
        INSERT INTO appraisal_reviews ({col_names})
        VALUES ({placeholders})
        ON CONFLICT(emp_id) DO UPDATE SET
            emp_name=excluded.emp_name,
            designation=excluded.designation,
            department=excluded.department,
            team_leader=excluded.team_leader,
            review_period=excluded.review_period,
            eval_date=excluded.eval_date,
            total_score=excluded.total_score,
            overall_rating=excluded.overall_rating,
            is_locked=1,
            edit_requested=0,
            reeval_requested=0,
            last_updated_date=excluded.last_updated_date,
            last_updated_by=excluded.last_updated_by;
    """
    cursor.execute(query, vals)
    conn.commit()
    conn.close()

def load_all_records_from_db():
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM appraisal_reviews ORDER BY id DESC;", conn)
    conn.close()
    
    if not df.empty:
        rename_map = {
            "emp_name": "Employee Name",
            "emp_id": "Employee ID",
            "designation": "Designation",
            "department": "Department",
            "team_leader": "Team Leader",
            "review_period": "Review Period",
            "eval_date": "Date of Evaluation",
            "total_score": "Total Score",
            "overall_rating": "Overall Rating",
            "is_locked": "Is Locked",
            "edit_requested": "Edit Requested",
            "reeval_requested": "Reevaluation Requested",
            "last_updated_date": "Last Updated Date",
            "last_updated_by": "Last Updated By"
        }
        for crit in CRITERIA_CONFIG:
            c_name = crit['name']
            safe_name = clean_col_name(c_name)
            rename_map[f"rating_{safe_name}"] = f"Rating: {c_name}"
            rename_map[f"remarks_{safe_name}"] = f"Remarks: {c_name}"
        
        df.rename(columns=rename_map, inplace=True)
    return df

def generate_text_form(row) -> str:
    total_score = calculate_employee_scores(row)
    overall_rating = get_overall_rating(total_score)
    last_updated = row.get("Last Updated Date", "N/A")
    updated_by = row.get("Last Updated By", "N/A")
    
    header = f"""Goodday Information Systems Pvt. Ltd. - Performance Appraisal Form
---------------------------------------------------------------------------------------------------
Employee Name      : {row['Employee Name']}
Employee ID        : {row['Employee ID']}
Designation        : {row['Designation']}
Department         : {row['Department']}
Team Leader        : {row['Team Leader']}
Review Period      : {row['Review Period']}
Date of Evaluation : {row['Date of Evaluation']}
Last Updated Date  : {last_updated} (By: {updated_by})

RATING SCALE REFERENCE
---------------------------------------------------------------------------------------------------
5 - Outstanding  |  4 - Exceeds Expectations  |  3 - Meets Expectations
2 - Growth Opportunity  |  1 - Unsatisfactory

EVALUATION BREAKDOWN
---------------------------------------------------------------------------------------------------
{ 'Sr.':<4} {'Criteria':<38} {'Weight(%)':<10} {'Rating(1-5)':<12} {'Score':<8} {'Remarks'}
"""
    body = ""
    for crit in CRITERIA_CONFIG:
        c_name = crit['name']
        w = crit['weight']
        val = row.get(f"Rating: {c_name}", 0)
        try:
            r = int(float(val)) if val not in [None, "", "-- Select Rating --"] else 0
        except (ValueError, TypeError):
            r = 0
        s = (w * r) / 5.0
        rem = row.get(f"Remarks: {c_name}", get_default_remark(c_name, r))
        body += f"{crit['sr']:<4} {c_name:<38} {w:<10} {r:<12} {s:<8.1f} {rem}\n"

    footer = f"""---------------------------------------------------------------------------------------------------
TOTAL SCORE    : {total_score:.0f} / 100
OVERALL RATING : {overall_rating}
---------------------------------------------------------------------------------------------------
"""
    return header + body + footer

# ------------------------------------------------------------------------------
# 7. MAIN NAVIGATION TAB ROUTING
# ------------------------------------------------------------------------------
user_role = st.session_state['user_role']

t1, t2, t3, t4, t5 = None, None, None, None, None

if user_role == "Super Admin":
    t2, t3, t4, t5 = st.tabs([
        "📊 Executive Dashboard (Submitted Forms)",
        "📄 View Appraisal Form",
        "📦 Export Reports",
        "🛠️ Admin Console & Permissions"
    ])
elif user_role == "HR":
    t2, t3, t4 = st.tabs([
        "📊 Executive Dashboard (Submitted Forms)",
        "📄 View Appraisal Form",
        "📦 Export Reports"
    ])
else:
    t1, t4 = st.tabs([
        "➕ Manual Form Entry",
        "📦 Export Reports"
    ])

# ------------------------------------------------------------------------------
# TAB 1: FORM ENTRY (TEAM LEADERS ONLY)
# ------------------------------------------------------------------------------
if t1 is not None:
    with t1:
        st.subheader("Add / Edit Employee Appraisal Record")
        
        df_db = load_all_records_from_db()
        
        # Alert for Deleted Forms requiring Resubmission
        conn = get_db_connection()
        del_notifs = pd.read_sql_query("SELECT * FROM deleted_notifications;", conn)
        conn.close()
        
        if not del_notifs.empty:
            for idx, d_row in del_notifs.iterrows():
                st.error(f"🚨 **Form Deleted / Resubmission Required**: The appraisal form for **{d_row['emp_name']} ({d_row['emp_id']})** was deleted by Super Admin. Please re-evaluate and resubmit this employee's form.")

        # Alert for Re-evaluation Requests
        if not df_db.empty and "Reevaluation Requested" in df_db.columns:
            reeval_records = df_db[df_db["Reevaluation Requested"] == 1]
            for idx, r_row in reeval_records.iterrows():
                st.warning(f"⚠️ **Re-evaluation Requested by Super Admin**: Appraisal for **{r_row['Employee Name']} ({r_row['Employee ID']})** was rejected for review. Please inspect and re-evaluate this employee.")

        existing_emp_ids = ["-- New Blank Appraisal Form --"] + (df_db["Employee ID"].tolist() if not df_db.empty else [])
        selected_edit_id = st.selectbox("Select Existing Employee to Edit/Update (or Create New):", existing_emp_ids)
        
        is_editing_existing = selected_edit_id != "-- New Blank Appraisal Form --"
        current_record = df_db[df_db["Employee ID"] == selected_edit_id].iloc[0] if is_editing_existing else None
        
        is_locked = bool(current_record["Is Locked"]) if is_editing_existing and "Is Locked" in current_record else False
        edit_requested = bool(current_record["Edit Requested"]) if is_editing_existing and "Edit Requested" in current_record else False
        
        can_edit = not is_locked
        
        if is_editing_existing and not can_edit:
            st.warning("🔒 This submitted form is locked against further edits.")
            if edit_requested:
                st.info("⌛ An edit permission request has been submitted to the Super Admin. Pending approval.")
            else:
                if st.button("🙋 Request Permission from Super Admin to Edit"):
                    conn = get_db_connection()
                    conn.execute("UPDATE appraisal_reviews SET edit_requested = 1 WHERE emp_id = ?;", (selected_edit_id,))
                    conn.commit()
                    conn.close()
                    st.success("Edit permission request sent to Super Admin!")
                    st.rerun()

        st.markdown("##### Header Information")
        c1, c2, c3 = st.columns(3)
        with c1:
            default_name = current_record["Employee Name"] if is_editing_existing else ""
            default_id = current_record["Employee ID"] if is_editing_existing else ""
            emp_name = st.text_input("Employee Name*", value=default_name, placeholder="e.g. John Smith", disabled=not can_edit)
            emp_id = st.text_input("Employee ID*", value=default_id, placeholder="e.g. EMP202601", disabled=is_editing_existing or not can_edit)
        with c2:
            default_desig = current_record["Designation"] if is_editing_existing else ""
            default_dept = current_record["Department"] if is_editing_existing else ""
            designation = st.text_input("Designation*", value=default_desig, placeholder="e.g. Senior Executive", disabled=not can_edit)
            department = st.text_input("Department*", value=default_dept, placeholder="e.g. IT (Catalog)", disabled=not can_edit)
        with c3:
            default_tl = current_record["Team Leader"] if is_editing_existing else ""
            existing_rp = current_record["Review Period"] if is_editing_existing else ""
            
            team_leader = st.text_input("Team Leader*", value=default_tl, placeholder="e.g. Alexander Wright", disabled=not can_edit)
            
            fy_index = FY_OPTIONS.index(existing_rp) if existing_rp in FY_OPTIONS else 0
            review_period = st.selectbox("Review Period*", FY_OPTIONS, index=fy_index, disabled=not can_edit)
            eval_date = st.date_input("Date of Evaluation", datetime.now(), disabled=not can_edit).strftime("%d-%b-%Y")

        st.markdown("---")
        st.markdown("##### Criteria Performance Ratings (Scale 1-5) & Auto Remarks")
        
        rating_options = ["-- Select Rating --", 5, 4, 3, 2, 1]
        ratings_input = {}
        remarks_input = {}
        
        def on_rating_change(sr, c_name, record_key):
            selected_rating = st.session_state[f"r_sel_{sr}_{record_key}"]
            if selected_rating != "-- Select Rating --":
                st.session_state[f"rem_input_{sr}_{record_key}"] = REMARKS_MATRIX[c_name][int(selected_rating)]
            else:
                st.session_state[f"rem_input_{sr}_{record_key}"] = ""

        rec_key = selected_edit_id.replace(" ", "_")

        for crit in CRITERIA_CONFIG:
            sr = crit['sr']
            c_name = crit['name']
            
            st.markdown(f"**{sr}. {c_name}** *(Weight: {crit['weight']}%)*")
            col_r, col_m = st.columns([1, 3])
            
            if is_editing_existing and f"Rating: {c_name}" in current_record:
                existing_r = int(current_record[f"Rating: {c_name}"])
                existing_rem = current_record[f"Remarks: {c_name}"]
                sel_index = rating_options.index(existing_r) if existing_r in rating_options else 0
            else:
                existing_r = "-- Select Rating --"
                existing_rem = ""
                sel_index = 0

            r_key = f"r_sel_{sr}_{rec_key}"
            rem_key = f"rem_input_{sr}_{rec_key}"

            if r_key not in st.session_state:
                st.session_state[r_key] = existing_r
            if rem_key not in st.session_state:
                st.session_state[rem_key] = existing_rem

            with col_r:
                r_val = st.selectbox(
                    "Rating (1-5)", 
                    rating_options, 
                    key=r_key,
                    on_change=on_rating_change,
                    args=(sr, c_name, rec_key),
                    disabled=not can_edit
                )
                ratings_input[c_name] = r_val
            
            with col_m:
                rem_val = st.text_input(
                    "Remarks", 
                    key=rem_key, 
                    placeholder="Remarks auto-populate upon selecting rating...",
                    disabled=not can_edit
                )
                remarks_input[c_name] = rem_val

        # --- DYNAMIC PREVIEW EXPANDER ---
        st.markdown("---")
        expander_title = "📄 Review Submitted Form" if (is_editing_existing and is_locked) else "🔍 Preview Form & Score Summary Before Final Submission"
        
        with st.expander(expander_title, expanded=False):
            preview_record = {
                "Employee Name": emp_name if emp_name else "[Not Provided]",
                "Employee ID": emp_id if emp_id else "[Not Provided]",
                "Designation": designation if designation else "[Not Provided]",
                "Department": department if department else "[Not Provided]",
                "Team Leader": team_leader if team_leader else "[Not Provided]",
                "Review Period": review_period if review_period != "-- Select Review Period --" else "[Not Selected]",
                "Date of Evaluation": str(eval_date),
            }
            for crit in CRITERIA_CONFIG:
                c_name = crit['name']
                preview_record[f"Rating: {c_name}"] = ratings_input[c_name]
                preview_record[f"Remarks: {c_name}"] = remarks_input[c_name]

            preview_score = calculate_employee_scores(preview_record)
            preview_rating = get_overall_rating(preview_score)

            p_col1, p_col2 = st.columns(2)
            p_col1.metric("Overall Score", f"{preview_score:.0f} / 100")
            p_col2.metric("Performance Level", preview_rating)

            st.markdown("#### 📋 Goodday Performance Appraisal Form")
            st.markdown(f"**Employee:** {preview_record['Employee Name']} ({preview_record['Employee ID']}) | **Role:** {preview_record['Designation']} | **Department:** {preview_record['Department']}")
            st.markdown(f"**Evaluator:** {preview_record['Team Leader']} | **Period:** {preview_record['Review Period']} | **Date:** {eval_date}")
            st.markdown("---")

            preview_table_data = []
            for crit in CRITERIA_CONFIG:
                c_name = crit['name']
                w = crit['weight']
                r_raw = ratings_input[c_name]
                r_disp = r_raw if r_raw != "-- Select Rating --" else 0
                s = (w * float(r_disp)) / 5.0 if r_raw != "-- Select Rating --" else 0.0
                rem = remarks_input[c_name]
                preview_table_data.append({
                    "Sr.": crit['sr'],
                    "Evaluation Criteria": c_name,
                    "Weight (%)": f"{w}%",
                    "Rating (1-5)": r_disp,
                    "Score": f"{s:.1f}",
                    "Remarks": rem
                })

            st.table(pd.DataFrame(preview_table_data))

        st.markdown("<br>", unsafe_allow_html=True)
        if can_edit:
            if st.button("💾 Save & Submit Appraisal Form", type="primary"):
                missing_fields = []
                if not emp_name: missing_fields.append("Employee Name")
                if not emp_id: missing_fields.append("Employee ID")
                if not designation: missing_fields.append("Designation")
                if not department: missing_fields.append("Department")
                if not team_leader: missing_fields.append("Team Leader")
                if review_period == "-- Select Review Period --": missing_fields.append("Review Period")
                
                unselected_ratings = [c['name'] for c in CRITERIA_CONFIG if ratings_input[c['name']] == "-- Select Rating --"]
                
                if missing_fields or unselected_ratings:
                    st.error(f"Please complete all required fields before submitting! "
                             f"{'Missing Headers: ' + ', '.join(missing_fields) + '. ' if missing_fields else ''}"
                             f"{'Unselected Ratings for: ' + ', '.join(unselected_ratings) if unselected_ratings else ''}")
                else:
                    new_record = {
                        "Employee Name": emp_name,
                        "Employee ID": emp_id,
                        "Designation": designation,
                        "Department": department,
                        "Team Leader": team_leader,
                        "Review Period": review_period,
                        "Date of Evaluation": str(eval_date),
                    }
                    for crit in CRITERIA_CONFIG:
                        c_name = crit['name']
                        new_record[f"Rating: {c_name}"] = ratings_input[c_name]
                        new_record[f"Remarks: {c_name}"] = remarks_input[c_name]

                    save_appraisal_to_db(new_record, st.session_state['username'])
                    st.toast("Appraisal form saved successfully!")
                    st.rerun()

# ------------------------------------------------------------------------------
# TAB 2: EXECUTIVE DASHBOARD (SUPER ADMIN & HR ONLY)
# ------------------------------------------------------------------------------
if t2 is not None:
    with t2:
        st.subheader("📊 Executive Review Portal")
        st.caption("Central executive dashboard to inspect performance reviews submitted by Team Leaders.")
        
        df_db = load_all_records_from_db()
        
        if not df_db.empty:
            col_f1, col_f2 = st.columns([2, 2])
            with col_f1:
                search_query = st.text_input("🔍 Search Employee Name or ID:", "")
            with col_f2:
                depts = ["All Departments"] + list(df_db["Department"].dropna().unique())
                selected_dept = st.selectbox("Filter by Department:", depts)

            filtered_df = df_db.copy()
            if search_query:
                filtered_df = filtered_df[
                    filtered_df["Employee Name"].str.contains(search_query, case=False, na=False) |
                    filtered_df["Employee ID"].str.contains(search_query, case=False, na=False)
                ]
            if selected_dept != "All Departments":
                filtered_df = filtered_df[filtered_df["Department"] == selected_dept]

            st.markdown("---")
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("Total Submitted Reviews", len(filtered_df))
            avg_s = filtered_df["Total Score"].mean() if "Total Score" in filtered_df else 0
            k2.metric("Company Average Score", f"{avg_s:.1f} / 100")
            out_p = len(filtered_df[filtered_df["Total Score"] >= 90]) if "Total Score" in filtered_df else 0
            k3.metric("Outstanding Performers", out_p)
            need_imp = len(filtered_df[filtered_df["Total Score"] < 50]) if "Total Score" in filtered_df else 0
            k4.metric("Growth Plans Required", need_imp)
            st.markdown("---")

            summary_cols = ["Employee ID", "Employee Name", "Department", "Designation", "Team Leader", "Total Score", "Overall Rating", "Last Updated Date", "Last Updated By"]
            display_cols = [c for c in summary_cols if c in filtered_df.columns]
            
            st.dataframe(filtered_df[display_cols], use_container_width=True)
            
            st.markdown("### 📋 Detailed Employee Review Cards")
            for idx, row in filtered_df.iterrows():
                score = row["Total Score"]
                rating_label = row["Overall Rating"]
                emp_id_val = row['Employee ID']
                is_reeval = bool(row.get("Reevaluation Requested", 0))
                
                with st.expander(f"👤 {row['Employee Name']} ({emp_id_val}) — Score: {score:.0f}/100 [{rating_label}]"):
                    st.write(f"**Department:** {row['Department']} | **Role:** {row['Designation']} | **Team Leader:** {row['Team Leader']}")
                    st.write(f"**Last Updated:** {row.get('Last Updated Date', 'N/A')} by `{row.get('Last Updated By', 'N/A')}`")
                    
                    breakdown_data = []
                    for crit in CRITERIA_CONFIG:
                        c_name = crit['name']
                        w = crit['weight']
                        val = row.get(f"Rating: {c_name}", 0)
                        try:
                            r = int(float(val)) if val not in [None, "", "-- Select Rating --"] else 0
                        except (ValueError, TypeError):
                            r = 0
                        s = (w * r) / 5.0
                        rem = row.get(f"Remarks: {c_name}", "")
                        breakdown_data.append({
                            "Sr.": crit['sr'],
                            "Criteria": c_name,
                            "Weight (%)": f"{w}%",
                            "Rating (1-5)": r,
                            "Score": f"{s:.1f}",
                            "Remarks": rem
                        })
                    
                    st.table(pd.DataFrame(breakdown_data))
                    
                    # Super Admin Actions
                    if user_role == "Super Admin":
                        col_a1, col_a2, col_a3 = st.columns([1, 1.2, 1.8])
                        
                        with col_a1:
                            if st.button(f"🗑️ Delete Record", key=f"del_{emp_id_val}"):
                                conn = get_db_connection()
                                conn.execute("INSERT INTO deleted_notifications (emp_id, emp_name, team_leader, deleted_by, deleted_at) VALUES (?, ?, ?, ?, ?);",
                                             (emp_id_val, row['Employee Name'], row['Team Leader'], st.session_state['username'], datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                                conn.execute("DELETE FROM appraisal_reviews WHERE emp_id = ?;", (emp_id_val,))
                                conn.commit()
                                conn.close()
                                st.toast("Form deleted successfully!")
                                st.rerun()
                                
                        with col_a2:
                            reeval_btn_label = "⌛ Re-evaluation Requested" if is_reeval else "🔄 Request Re-evaluation"
                            if st.button(reeval_btn_label, key=f"reeval_{emp_id_val}", disabled=is_reeval):
                                conn = get_db_connection()
                                conn.execute("UPDATE appraisal_reviews SET is_locked = 0, reeval_requested = 1 WHERE emp_id = ?;", (emp_id_val,))
                                conn.commit()
                                conn.close()
                                st.toast("Re-evaluation requested successfully!")
                                st.rerun()

                        with col_a3:
                            st.download_button(
                                label=f"💾 Download Form (.txt)",
                                data=generate_text_form(row),
                                file_name=f"{emp_id_val}_{row['Employee Name'].replace(' ', '_')}_Appraisal.txt",
                                mime="text/plain",
                                key=f"dl_card_{emp_id_val}"
                            )
                    else:
                        st.download_button(
                            label=f"💾 Download {row['Employee Name']}'s Form (.txt)",
                            data=generate_text_form(row),
                            file_name=f"{emp_id_val}_{row['Employee Name'].replace(' ', '_')}_Appraisal.txt",
                            mime="text/plain",
                            key=f"dl_card_{emp_id_val}"
                        )
        else:
            st.info("No appraisal forms have been submitted yet.")

# ------------------------------------------------------------------------------
# TAB 3: FORM INSPECTOR (SUPER ADMIN & HR ONLY)
# ------------------------------------------------------------------------------
if t3 is not None:
    with t3:
        st.subheader("📄 Individual Form Inspector & Download Portal")
        st.caption("Inspect individual employee evaluation breakdowns and export detailed reports.")
        
        df_preview = load_all_records_from_db()
        if not df_preview.empty:
            names = df_preview['Employee Name'].tolist()
            selected_name = st.selectbox("Select Employee Appraisal Record to Inspect:", names)
            selected_row = df_preview[df_preview['Employee Name'] == selected_name].iloc[0]
            
            st.markdown("---")
            row_score = selected_row["Total Score"]
            row_rating = selected_row["Overall Rating"]
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Employee Name", selected_row["Employee Name"], delta=selected_row["Employee ID"])
            m2.metric("Total Score", f"{row_score:.0f} / 100")
            m3.metric("Performance Rating", row_rating)
            m4.metric("Review Period", selected_row["Review Period"])
            st.markdown("---")

            st.markdown("##### Header Information")
            h1, h2, h3 = st.columns(3)
            h1.write(f"**Designation:** {selected_row['Designation']}")
            h1.write(f"**Department:** {selected_row['Department']}")
            h2.write(f"**Team Leader:** {selected_row['Team Leader']}")
            h2.write(f"**Date of Evaluation:** {selected_row['Date of Evaluation']}")
            h3.write(f"**Last Updated Date:** {selected_row.get('Last Updated Date', 'N/A')}")
            h3.write(f"**Last Updated By:** `{selected_row.get('Last Updated By', 'N/A')}`")
            
            st.markdown("---")
            st.markdown("##### Performance Breakdown & Criteria Scores")
            
            insp_table_data = []
            for crit in CRITERIA_CONFIG:
                c_name = crit['name']
                w = crit['weight']
                val = selected_row.get(f"Rating: {c_name}", 0)
                try:
                    r = int(float(val)) if val not in [None, "", "-- Select Rating --"] else 0
                except (ValueError, TypeError):
                    r = 0
                s = (w * r) / 5.0
                rem = selected_row.get(f"Remarks: {c_name}", get_default_remark(c_name, r))
                insp_table_data.append({
                    "Sr.": crit['sr'],
                    "Evaluation Criteria": c_name,
                    "Weight (%)": f"{w}%",
                    "Rating (1-5)": r,
                    "Score": f"{s:.1f}",
                    "Remarks": rem
                })

            st.table(pd.DataFrame(insp_table_data))
            
            form_text = generate_text_form(selected_row)
            
            st.markdown("---")
            st.download_button(
                label=f"💾 Download Official {selected_name}'s Appraisal Form (.txt)",
                data=form_text,
                file_name=f"{selected_row['Employee ID']}_{selected_name.replace(' ', '_')}_Appraisal_Form.txt",
                mime="text/plain"
            )
        else:
            st.info("No appraisal data available to inspect.")

# ------------------------------------------------------------------------------
# TAB 4: EXPORT REPORTS
# ------------------------------------------------------------------------------
if t4 is not None:
    with t4:
        st.subheader("Export Summary Reports & Zip Packages")
        
        df_export = load_all_records_from_db()
        if not df_export.empty:
            col_ex1, col_ex2 = st.columns(2)
            
            csv_bytes = df_export.to_csv(index=False).encode('utf-8')
            col_ex1.download_button(
                label="📊 Download Full Appraisal Summary (CSV)",
                data=csv_bytes,
                file_name="goodday_appraisal_summary.csv",
                mime="text/csv"
            )
            
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                for idx, row in df_export.iterrows():
                    form_content = generate_text_form(row)
                    file_name = f"{row['Employee ID']}_{str(row['Employee Name']).replace(' ', '_')}_Appraisal.txt"
                    zip_file.writestr(file_name, form_content)

            col_ex2.download_button(
                label="📦 Download All Employee Appraisal Forms (ZIP)",
                data=zip_buffer.getvalue(),
                file_name="all_employee_appraisal_forms.zip",
                mime="application/zip"
            )
        else:
            st.info("No data available to export.")

# ------------------------------------------------------------------------------
# TAB 5: SUPER ADMIN CONSOLE
# ------------------------------------------------------------------------------
if t5 is not None:
    with t5:
        st.subheader("🛠️ Super Admin Administration Console")
        
        admin_tab1, admin_tab2, admin_tab3, admin_tab4 = st.tabs([
            "🔓 Unlock Edit Requests", 
            "➕ Create New User", 
            "✏️ Edit / Delete Existing Users", 
            "🗑️ Manage & Delete Records"
        ])
        
        # SUB-TAB 1: UNLOCK REQUESTS
        with admin_tab1:
            st.markdown("##### Pending Edit Requests from Team Leaders")
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT emp_id, emp_name, team_leader, department FROM appraisal_reviews WHERE edit_requested = 1;")
            requests = cursor.fetchall()
            
            if requests:
                for req in requests:
                    col_r1, col_r2 = st.columns([3, 1])
                    with col_r1:
                        st.write(f"📌 **{req['emp_name']}** ({req['emp_id']}) - TL: {req['team_leader']} ({req['department']})")
                    with col_r2:
                        if st.button(f"Unlock {req['emp_id']}", key=f"btn_unlock_{req['emp_id']}"):
                            cursor.execute("UPDATE appraisal_reviews SET is_locked = 0, edit_requested = 0 WHERE emp_id = ?;", (req['emp_id'],))
                            conn.commit()
                            st.toast(f"Form unlocked for {req['emp_name']}!")
                            conn.close()
                            st.rerun()
            else:
                st.info("No pending edit requests.")
            conn.close()

        # SUB-TAB 2: CREATE NEW USER
        with admin_tab2:
            st.markdown("##### Create New Portal User Account")
            with st.form("create_user_form"):
                new_u = st.text_input("Username*")
                new_p = st.text_input("Password*", type="password")
                new_fn = st.text_input("Full Name*")
                new_role = st.selectbox("Assign Role*", ["Team Leader", "HR", "Super Admin"])
                
                btn_create = st.form_submit_button("➕ Create User")
                
                if btn_create:
                    if new_u and new_p and new_fn:
                        try:
                            conn = get_db_connection()
                            conn.execute(
                                "INSERT INTO users (username, password_hash, role, full_name) VALUES (?, ?, ?, ?);",
                                (new_u, hash_password(new_p), new_role, new_fn)
                            )
                            conn.commit()
                            conn.close()
                            st.toast(f"User '{new_u}' created successfully as {new_role}!")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error("Username already exists. Please pick a different username.")
                    else:
                        st.error("Please fill in all required fields.")

        # SUB-TAB 3: EDIT USERNAME & DETAILS
        with admin_tab3:
            st.markdown("##### Edit or Remove Existing User Credentials")
            conn = get_db_connection()
            users_df = pd.read_sql_query("SELECT id, username, role, full_name FROM users;", conn)
            conn.close()
            
            if not users_df.empty:
                st.dataframe(users_df, use_container_width=True)
                st.markdown("---")
                
                col_u_edit, col_u_del = st.columns(2)
                
                with col_u_edit:
                    st.markdown("###### ✏️ Edit User Details / Change Username")
                    selected_u_edit = st.selectbox("Select User to Edit:", users_df["username"].tolist(), key="select_user_edit")
                    u_row = users_df[users_df["username"] == selected_u_edit].iloc[0]
                    
                    with st.form("edit_user_form"):
                        edit_username = st.text_input("Username", value=u_row["username"])
                        edit_fn = st.text_input("Full Name", value=u_row["full_name"])
                        
                        roles_list = ["Team Leader", "HR", "Super Admin"]
                        r_idx = roles_list.index(u_row["role"]) if u_row["role"] in roles_list else 0
                        edit_role = st.selectbox("Role", roles_list, index=r_idx)
                        
                        reset_pw = st.text_input("New Password (Leave blank to keep unchanged)", type="password")
                        
                        btn_save_u = st.form_submit_button("💾 Save User Changes")
                        
                        if btn_save_u:
                            if not edit_username.strip():
                                st.error("Username cannot be empty.")
                            else:
                                try:
                                    conn = get_db_connection()
                                    if reset_pw:
                                        conn.execute("UPDATE users SET username = ?, full_name = ?, role = ?, password_hash = ? WHERE username = ?;",
                                                     (edit_username.strip(), edit_fn, edit_role, hash_password(reset_pw), selected_u_edit))
                                    else:
                                        conn.execute("UPDATE users SET username = ?, full_name = ?, role = ? WHERE username = ?;",
                                                     (edit_username.strip(), edit_fn, edit_role, selected_u_edit))
                                    conn.commit()
                                    conn.close()
                                    
                                    if selected_u_edit == st.session_state['username']:
                                        st.session_state['username'] = edit_username.strip()
                                        st.session_state['full_name'] = edit_fn
                                        st.session_state['user_role'] = edit_role

                                    st.toast(f"User details for '{edit_username.strip()}' updated successfully!")
                                    st.rerun()
                                except sqlite3.IntegrityError:
                                    st.error("Username already exists. Please choose a unique username.")

                with col_u_del:
                    st.markdown("###### 🗑️ Delete User Account")
                    selected_u_del = st.selectbox("Select User to Delete:", users_df["username"].tolist(), key="select_user_del")
                    
                    if selected_u_del == st.session_state['username']:
                        st.warning("⚠️ You cannot delete your own currently logged-in Super Admin account.")
                    else:
                        if st.button(f"🗑️ Confirm Deletion of '{selected_u_del}'", type="primary"):
                            conn = get_db_connection()
                            conn.execute("DELETE FROM users WHERE username = ?;", (selected_u_del,))
                            conn.commit()
                            conn.close()
                            st.toast(f"User '{selected_u_del}' deleted successfully!")
                            st.rerun()
            else:
                st.info("No users found.")

        # SUB-TAB 4: MANAGE AND DELETE APPRAISAL RECORDS
        with admin_tab4:
            st.markdown("##### Permanently Delete Submitted Appraisal Records")
            df_manage = load_all_records_from_db()
            if not df_manage.empty:
                del_emp_id = st.selectbox("Select Record to Delete:", df_manage["Employee ID"].tolist(), key="del_select")
                
                if st.button(f"⚠️ Confirm Permanent Deletion for {del_emp_id}", type="primary"):
                    conn = get_db_connection()
                    conn.execute("INSERT INTO deleted_notifications (emp_id, emp_name, team_leader, deleted_by, deleted_at) VALUES (?, ?, ?, ?, ?);",
                                 (del_emp_id, df_manage[df_manage["Employee ID"]==del_emp_id]["Employee Name"].values[0], df_manage[df_manage["Employee ID"]==del_emp_id]["Team Leader"].values[0], st.session_state['username'], datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
                    conn.execute("DELETE FROM appraisal_reviews WHERE emp_id = ?;", (del_emp_id,))
                    conn.commit()
                    conn.close()
                    st.toast("Form deleted successfully!")
                    st.rerun()
            else:
                st.info("No records in database to delete.")