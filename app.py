import streamlit as st
import pandas as pd
from analyzer import calculate_results, parse_pdf

st.set_page_config(page_title="JNTUK Result Manager", layout="wide")

# --- MAIN TITLE (RESTORED) ---
st.title("🎓 JNTUK Percentage Calculator")
st.write("Upload your semester memos to calculate your CGPA.")

# --- SIDEBAR: UPLOAD ONLY ---
with st.sidebar:
    st.header("Upload Center")
    uploaded_files = st.file_uploader("Upload Memos (PDF/CSV)", type=["csv", "pdf"], accept_multiple_files=True)
    use_demo = st.checkbox("Use Demo Data")
    st.info("💡 Supports JNTUK R16/R19/R20/R23 formats")

all_semesters_data = []

# --- DATA LOADING ---
if use_demo:
    # DEMO DATA
    data = {
        'RollNo': ['22HJ1A4311']*6,
        'StudentName': ['LEKKALA DIVAKAR REDDY']*6,
        'Semester': ['1-1', '1-1', '1-1', '1-2', '1-2', '2-1'],
        'Subject': ['Python', 'Maths-I', 'Physics', 'Data Structures', 'Maths-II', 'Java'],
        'Grade': ['B', 'A', 'F', 'S', 'B', 'F'],
        'Credits': [3, 3, 3, 3, 3, 3],
        'Points': [8, 9, 0, 10, 8, 0]
    }
    all_semesters_data.append(pd.DataFrame(data))

elif uploaded_files:
    for file in uploaded_files:
        try:
            file.seek(0)
            if file.name.endswith('.csv'): df = pd.read_csv(file)
            elif file.name.endswith('.pdf'): df = parse_pdf(file)
            
            if df is not None:
                all_semesters_data.append(df)
        except Exception: pass

# --- DASHBOARD ---
if all_semesters_data:
    full_history = pd.concat(all_semesters_data, ignore_index=True)
    
    # CLEANUP
    if 'Points' in full_history.columns:
        full_history.sort_values(by='Points', ascending=False, inplace=True)
    full_history.drop_duplicates(subset=['Subject'], keep='first', inplace=True)
    full_history.sort_values(by=['Semester', 'Subject'], inplace=True)

    # --- STUDENT DETAILS (SHOWN BELOW TITLE) ---
  
    st.divider()

    # --- SECTION A: FAILURES ---
    failed_df = full_history[full_history['Grade'].isin(['F', 'AB', 'M'])]
    if not failed_df.empty:
        st.error(f"⚠️ Active Backlogs: {len(failed_df)}")
        st.dataframe(
            failed_df[['Semester', 'Subject', 'Grade']], 
            use_container_width=True, 
            hide_index=True
        )
    else:
        st.success("✨ All Clear! No Backlogs.")

    # --- SECTION B: SEMESTER TABS ---
    semesters = sorted(full_history['Semester'].unique())
    if semesters:
        tabs = st.tabs(semesters)
        for i, sem in enumerate(semesters):
            with tabs[i]:
                sem_data = full_history[full_history['Semester'] == sem]
                
                # SGPA
                sgpa = calculate_results(pd.DataFrame(sem_data)).iloc[0]['SGPA'] if not sem_data.empty else 0
                st.metric(f"SGPA ({sem})", sgpa)
                
                # Table
                display_df = sem_data.copy()
                display_df['Status'] = display_df['Grade'].apply(lambda x: '❌' if x in ['F', 'AB', 'M'] else '✅')
                st.dataframe(
                    display_df[['Subject', 'Grade', 'Status', 'Credits']], 
                    use_container_width=True, 
                    hide_index=True
                )

    # --- SECTION C: FINAL CGPA ---
    st.divider()
    
    academic = full_history[~full_history['Grade'].isin(['COMPLETED', 'Y'])]
    total_creds = academic['Credits'].sum()
    total_pts = (academic['Credits'] * academic['Points']).sum()
    cgpa = round(total_pts / total_creds, 2) if total_creds > 0 else 0.0
    
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Credits", total_creds)
    c2.metric("Total Semesters", len(semesters))
    c3.metric("🏆 FINAL CGPA", cgpa)

elif not use_demo:
    st.info("Upload files to begin.")