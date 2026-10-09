import streamlit as st
import pandas as pd
import io
import zipfile
from datetime import datetime

# ------------------------------------------------------------------------------
# 1. PAGE SETUP
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="Catalog Team Performance Appraisal Tool",
    page_icon="📋",
    layout="wide"
)

st.title("📋 Catalog Team Performance Appraisal Portal")
st.markdown("Evaluate employee performance, edit ratings, track scores (out of 100), and export detailed appraisal records.")

# ------------------------------------------------------------------------------
# 2. EVALUATION CRITERIA & REMARKS MATRIX
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

# Complete Matrix from Remarks.xlsx
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

def get_default_remark(criteria_name: str, rating: int) -> str:
    """Returns corresponding remark from matrix based on rating."""
    return REMARKS_MATRIX.get(criteria_name, {}).get(int(rating), "")

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
    """Calculates weighted total score out of 100 based on 1-5 rating scale."""
    total = 0.0
    for crit in CRITERIA_CONFIG:
        rating = float(row.get(f"Rating: {crit['name']}", 3))
        score = (crit['weight'] * rating) / 5.0
        total += score
    return round(total, 2)

# Initialize Session State Keys for Form Dropdowns & Remarks
for crit in CRITERIA_CONFIG:
    sr = crit['sr']
    c_name = crit['name']
    if f"form_r_{sr}" not in st.session_state:
        st.session_state[f"form_r_{sr}"] = 5 if sr in [2, 3, 4, 7, 9] else 4
    if f"form_rem_{sr}" not in st.session_state:
        st.session_state[f"form_rem_{sr}"] = get_default_remark(c_name, st.session_state[f"form_r_{sr}"])

def update_remark_callback(sr: int, c_name: str):
    """Callback triggered whenever rating dropdown changes."""
    selected_rating = st.session_state[f"form_r_{sr}"]
    st.session_state[f"form_rem_{sr}"] = get_default_remark(c_name, selected_rating)

# ------------------------------------------------------------------------------
# 3. INITIALIZE DATABASE
# ------------------------------------------------------------------------------
if 'appraisal_db' not in st.session_state:
    sample_data = [{
        "Employee Name": "Mitesh Makwana",
        "Employee ID": "EMP202401",
        "Designation": "Team Leader",
        "Department": "IT (Catalog)",
        "Team Leader": "Mitesh Makwana",
        "Review Period": "FY 2024-25",
        "Date of Evaluation": "11-Jun-2026",
        "Rating: Quality of Work": 4,
        "Remarks: Quality of Work": REMARKS_MATRIX["Quality of Work"][4],
        "Rating: Productivity / Target Achievement": 5,
        "Remarks: Productivity / Target Achievement": REMARKS_MATRIX["Productivity / Target Achievement"][5],
        "Rating: Attendance & Punctuality": 5,
        "Remarks: Attendance & Punctuality": REMARKS_MATRIX["Attendance & Punctuality"][5],
        "Rating: Teamwork & Collaboration": 5,
        "Remarks: Teamwork & Collaboration": REMARKS_MATRIX["Teamwork & Collaboration"][5],
        "Rating: Communication Skills": 4,
        "Remarks: Communication Skills": REMARKS_MATRIX["Communication Skills"][4],
        "Rating: Problem Solving Ability": 4,
        "Remarks: Problem Solving Ability": REMARKS_MATRIX["Problem Solving Ability"][4],
        "Rating: Initiative & Ownership": 5,
        "Remarks: Initiative & Ownership": REMARKS_MATRIX["Initiative & Ownership"][5],
        "Rating: Learning & Development": 4,
        "Remarks: Learning & Development": REMARKS_MATRIX["Learning & Development"][4],
        "Rating: Client Satisfaction": 5,
        "Remarks: Client Satisfaction": REMARKS_MATRIX["Client Satisfaction"][5]
    }]
    st.session_state['appraisal_db'] = pd.DataFrame(sample_data)

# ------------------------------------------------------------------------------
# 4. FORM GENERATOR HELPER
# ------------------------------------------------------------------------------
def generate_text_form(row) -> str:
    total_score = calculate_employee_scores(row)
    overall_rating = get_overall_rating(total_score)
    
    header = f"""================================================================================
                    Catalog Team Performance Appraisal Form
================================================================================
Employee Name      : {row['Employee Name']}
Employee ID        : {row['Employee ID']}
Designation        : {row['Designation']}
Department         : {row['Department']}
Team Leader        : {row['Team Leader']}
Review Period      : {row['Review Period']}
Date of Evaluation : {row['Date of Evaluation']}

--------------------------------------------------------------------------------
RATING SCALE REFERENCE
--------------------------------------------------------------------------------
5 - Outstanding  |  4 - Exceeds Expectations  |  3 - Meets Expectations
2 - Growth Opportunity  |  1 - Unsatisfactory

--------------------------------------------------------------------------------
EVALUATION BREAKDOWN
--------------------------------------------------------------------------------
Sr.  Criteria                              Weight(%)  Rating(1-5)  Score  Remarks
"""
    body = ""
    for crit in CRITERIA_CONFIG:
        c_name = crit['name']
        w = crit['weight']
        r = int(float(row.get(f"Rating: {c_name}", 0)))
        s = (w * r) / 5.0
        rem = row.get(f"Remarks: {c_name}", get_default_remark(c_name, r))
        body += f"{crit['sr']:<4} {c_name:<36} {w:<10} {r:<11} {s:<6.1f} {rem}\n"

    footer = f"""--------------------------------------------------------------------------------
TOTAL SCORE    : {total_score:.0f} / 100
OVERALL RATING : {overall_rating}
================================================================================
"""
    return header + body + footer

# ------------------------------------------------------------------------------
# 5. SIDEBAR CONTROLS
# ------------------------------------------------------------------------------
st.sidebar.header("📂 Bulk Data Controls")

uploaded_file = st.sidebar.file_uploader("Upload Appraisal File (CSV / Excel)", type=["csv", "xlsx"])
if uploaded_file is not None:
    try:
        if uploaded_file.name.endswith('.csv'):
            new_df = pd.read_csv(uploaded_file)
        else:
            new_df = pd.read_excel(uploaded_file)
        st.session_state['appraisal_db'] = new_df
        st.sidebar.success(f"Successfully loaded {len(new_df)} record(s)!")
    except Exception as e:
        st.sidebar.error(f"Error loading file: {str(e)}")

st.sidebar.markdown("---")

@st.cache_data
def get_csv_template():
    return st.session_state['appraisal_db'].to_csv(index=False).encode('utf-8')

st.sidebar.download_button(
    label="📄 Download Input CSV Template",
    data=get_csv_template(),
    file_name="catalog_appraisal_template.csv",
    mime="text/csv"
)

if st.sidebar.button("⚠️ Reset / Clear Records"):
    st.session_state['appraisal_db'] = pd.DataFrame()
    st.rerun()

# ------------------------------------------------------------------------------
# 6. WORKSPACE TABS
# ------------------------------------------------------------------------------
tab_add, tab_view, tab_preview, tab_export = st.tabs([
    "➕ 1. Manual Form Entry",
    "📊 2. Score Dashboard",
    "📄 3. View Individual Appraisal Form",
    "📦 4. Export & Download Reports"
])

# ------------------------------------------------------------------------------
# TAB 1: MANUAL ENTRY FORM WITH LIVE AUTO-REMARKS
# ------------------------------------------------------------------------------
with tab_add:
    st.subheader("Add Employee Appraisal Record")
    
    st.markdown("##### Header Information")
    c1, c2, c3 = st.columns(3)
    with c1:
        emp_name = st.text_input("Employee Name*", value="Mitesh Makwana", key="form_emp_name")
        emp_id = st.text_input("Employee ID*", value="EMP202601", key="form_emp_id")
    with c2:
        designation = st.text_input("Designation*", value="Team Leader", key="form_designation")
        department = st.text_input("Department*", value="IT (Catalog)", key="form_dept")
    with c3:
        team_leader = st.text_input("Team Leader*", value="Mitesh Makwana", key="form_tl")
        review_period = st.text_input("Review Period*", value="FY 2024-25", key="form_rp")
        eval_date = st.date_input("Date of Evaluation", datetime.now(), key="form_date").strftime("%d-%b-%Y")

    st.markdown("---")
    st.markdown("##### Criteria Performance Ratings (Scale 1-5) & Auto Remarks")
    
    for crit in CRITERIA_CONFIG:
        sr = crit['sr']
        c_name = crit['name']
        
        st.markdown(f"**{sr}. {c_name}** *(Weight: {crit['weight']}%)*")
        col_r, col_m = st.columns([1, 3])
        
        with col_r:
            st.selectbox(
                "Rating (1-5)", 
                [5, 4, 3, 2, 1], 
                key=f"form_r_{sr}", 
                on_change=update_remark_callback, 
                args=(sr, c_name)
            )
        
        with col_m:
            st.text_input(
                "Remarks (Auto-filled from matrix, editable)", 
                key=f"form_rem_{sr}"
            )

    if st.button("➕ Save Employee Appraisal", type="primary"):
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
            sr = crit['sr']
            c_name = crit['name']
            new_record[f"Rating: {c_name}"] = st.session_state[f"form_r_{sr}"]
            new_record[f"Remarks: {c_name}"] = st.session_state[f"form_rem_{sr}"]

        st.session_state['appraisal_db'] = pd.concat(
            [st.session_state['appraisal_db'], pd.DataFrame([new_record])], 
            ignore_index=True
        )
        st.success(f"Appraisal form for {emp_name} saved successfully!")

# ------------------------------------------------------------------------------
# TAB 2: SCORE DASHBOARD (CALCULATED METRICS ONLY)
# ------------------------------------------------------------------------------
with tab_view:
    st.subheader("📊 Calculated Performance Metrics")
    
    if not st.session_state['appraisal_db'].empty:
        df_current = st.session_state['appraisal_db'].copy()
        
        calc_summary = []
        for idx, row in df_current.iterrows():
            total = calculate_employee_scores(row)
            rating_label = get_overall_rating(total)
            calc_summary.append({
                "Employee ID": row.get("Employee ID", ""),
                "Employee Name": row.get("Employee Name", ""),
                "Department": row.get("Department", ""),
                "Designation": row.get("Designation", ""),
                "Total Score (Max 100)": int(total),
                "Overall Rating": rating_label
            })
        
        st.dataframe(pd.DataFrame(calc_summary), use_container_width=True)
    else:
        st.info("No records present. Add an employee in Tab 1 or upload a CSV file from the sidebar.")

# ------------------------------------------------------------------------------
# TAB 3: INDIVIDUAL PREVIEW
# ------------------------------------------------------------------------------
with tab_preview:
    st.subheader("Form Inspector & Individual Document Download")
    
    if not st.session_state['appraisal_db'].empty:
        df = st.session_state['appraisal_db']
        names = df['Employee Name'].tolist()
        
        selected_name = st.selectbox("Select Employee to View Form:", names)
        selected_row = df[df['Employee Name'] == selected_name].iloc[0]
        
        form_text = generate_text_form(selected_row)
        
        st.text_area("Form Preview", form_text, height=480)
        
        st.download_button(
            label=f"💾 Download {selected_name}'s Appraisal Form (.txt)",
            data=form_text,
            file_name=f"{selected_row['Employee ID']}_{selected_name.replace(' ', '_')}_Appraisal_Form.txt",
            mime="text/plain"
        )
    else:
        st.info("No appraisal data available to preview.")

# ------------------------------------------------------------------------------
# TAB 4: BULK EXPORT
# ------------------------------------------------------------------------------
with tab_export:
    st.subheader("Export Summary Reports & Zip Packages")
    
    if not st.session_state['appraisal_db'].empty:
        df_export = st.session_state['appraisal_db'].copy()
        
        df_export['Total Score'] = df_export.apply(calculate_employee_scores, axis=1)
        df_export['Overall Rating'] = df_export['Total Score'].apply(get_overall_rating)
        
        col_ex1, col_ex2 = st.columns(2)
        
        csv_bytes = df_export.to_csv(index=False).encode('utf-8')
        col_ex1.download_button(
            label="📊 Download Full Appraisal Summary (CSV)",
            data=csv_bytes,
            file_name="catalog_appraisal_summary_2026.csv",
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