import pdfplumber
import pandas as pd
import re

# 1. THE RULE BOOK
grade_points = {
    'O': 10, 'S': 10, 'A+': 10, 'A': 9, 'B': 8, 'C': 7,
    'D': 6, 'E': 5, 'F': 0, 'AB': 0, 'M': 0, 
    'COMPLETED': 0, 'Y': 0
}

def get_semester_from_code(code):
    # Decodes JNTU Subject Codes (e.g., R201101 -> 1-1)
    code = str(code).upper()
    clean_code = code.replace('R13', '').replace('R16', '').replace('R19', '').replace('R20', '').replace('R23', '')
    if len(clean_code) >= 2 and clean_code[0].isdigit() and clean_code[1].isdigit():
        return f"{clean_code[0]}-{clean_code[1]}"
    return "Others"

def calculate_sgpa(df):
    academic_courses = df[~df['Grade'].isin(['COMPLETED', 'Y'])]
    total_credits = academic_courses['Credits'].sum()
    total_points = (academic_courses['Credits'] * academic_courses['Points']).sum()
    if total_credits == 0: return 0.0
    return round(total_points / total_credits, 2)

def parse_pdf(file_obj):
    data = []
    student_name = "Unknown"
    roll_no = "Unknown"
    
    with pdfplumber.open(file_obj) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text: continue
            
            lines = text.split('\n')
            for line in lines:
                clean_line = line.replace('"', '').replace(',', '').strip()
                
                # --- HUNT FOR ROLL NUMBER ---
                # Pattern: 2 digits, 2 letters, 1 alphanumeric, 4 digits (e.g., 22HJ1A4311)
                # We assume the roll number is essentially the only 10-char string with this pattern
                if roll_no == "Unknown":
                    roll_match = re.search(r'\b\d{2}[A-Z]{2}[0-9A-Z]\d{4}\b', clean_line)
                    if roll_match:
                        roll_no = roll_match.group(0)

                # --- HUNT FOR NAME ---
                if "Name" in clean_line and (":" in clean_line or " " in clean_line):
                    # Try to grab text after 'Name' or ':'
                    parts = re.split(r'Name\s*[:\-\.]?\s*', clean_line, flags=re.IGNORECASE)
                    if len(parts) > 1:
                        candidate = parts[1].strip()
                        # Clean up if it grabbed extra junk
                        if len(candidate) > 3 and not candidate.startswith("Subject"):
                            student_name = candidate

                # --- EXTRACT MARKS ---
                parts = clean_line.split()
                if len(parts) >= 4:
                    code = parts[0]
                    # Check for Subject Code (Starts with R or Number)
                    if len(code) > 3 and (code.startswith('R') or code[0].isdigit()):
                        try:
                            grade = None
                            credits = 0.0
                            subject_end_index = -1
                            
                            for i in range(1, 4):
                                item = parts[-i].upper()
                                if item in grade_points:
                                    grade = item
                                    # Find credits near the grade
                                    if parts[-i-1].replace('.', '', 1).isdigit():
                                        credits = float(parts[-i-1])
                                    elif parts[-i+1].replace('.', '', 1).isdigit():
                                        credits = float(parts[-i+1])
                                    subject_end_index = -i-1
                                    break
                            
                            if grade:
                                if credits == 15: credits = 1.5
                                if grade == 'F' and credits == 0: credits = 3.0
                                subject_name = " ".join(parts[1:subject_end_index])
                                semester = get_semester_from_code(code)

                                data.append({
                                    'RollNo': roll_no,       # <--- Now uses found Roll No
                                    'StudentName': student_name, # <--- Now uses found Name
                                    'Semester': semester,
                                    'Subject': subject_name,
                                    'Grade': grade,
                                    'Credits': credits,
                                    'Points': grade_points[grade]
                                })
                        except Exception: continue

    if not data: return None
    
    # Backfill Name/RollNo to all rows if found late
    df = pd.DataFrame(data)
    if roll_no != "Unknown": df['RollNo'] = roll_no
    if student_name != "Unknown": df['StudentName'] = student_name
    
    return df

def calculate_results(df):
    # Group by found RollNo
    results = df.groupby('RollNo').apply(lambda x: pd.Series({
        'Backlogs': (x['Grade'].isin(['F', 'AB', 'M'])).sum(),
        'SGPA': calculate_sgpa(x),
        'Failed_Subjects': ", ".join(x[x['Grade'].isin(['F', 'AB', 'M'])]['Subject'].values)
    }))
    return results