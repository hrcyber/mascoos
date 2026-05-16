import streamlit as st
import sqlite3
import pandas as pd
from datetime import date
from fpdf import FPDF
import base64
import urllib.parse
import hashlib
import matplotlib.pyplot as plt

# --- 1. PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Maa Saraswati Coaching",
    layout="centered",  # Mobile layout optimization
    page_icon="📚"
)

# Custom CSS for smartphone viewports
st.markdown("""
    <style>
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 1.5rem;
        padding-left: 0.8rem;
        padding-right: 0.8rem;
    }
    div.stButton > button:first-child {
        width: 100% !important;
        border-radius: 8px;
    }
    .mobile-card {
        background-color: #f8f9fa;
        padding: 12px;
        border-radius: 8px;
        margin-bottom: 10px;
        border: 1px solid #dee2e6;
    }
    </style>
""", unsafe_allow_html=True)


# --- 2. DATABASE SETUP ---
def init_db():
    conn = sqlite3.connect('coaching_management_v8.db', check_same_thread=False)
    c = conn.cursor()

    # Students Table (Added father_name and ensured address field is active)
    c.execute('''CREATE TABLE IF NOT EXISTS students(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE, 
                    father_name TEXT,
                    class TEXT, 
                    address TEXT, 
                    mobile TEXT, 
                    monthly_fee REAL)''')

    # Fee Collection Table
    c.execute('''CREATE TABLE IF NOT EXISTS fee_collection(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT, class TEXT, month TEXT, paid_amount REAL, dues REAL, date TEXT)''')

    # Users/Login Table
    c.execute('''CREATE TABLE IF NOT EXISTS users(
                    username TEXT PRIMARY KEY, password TEXT)''')

    # Homework & Notices Table
    c.execute('''CREATE TABLE IF NOT EXISTS notices(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT, title TEXT, content TEXT, class_target TEXT, date TEXT)''')

    # Default Admin User
    c.execute("SELECT * FROM users WHERE username = 'admin'")
    if not c.fetchone():
        hashed_default_pass = hashlib.sha256(str.encode('admin123')).hexdigest()
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)", ('admin', hashed_default_pass))
        conn.commit()

    return conn


conn = init_db()
c = conn.cursor()


# --- 3. HELPERS ---
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()


def verify_user(username, password):
    hashed_pass = make_hashes(password)
    c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, hashed_pass))
    return c.fetchone()


def create_pdf(name, s_class, month, amount, dues, pay_date=None):
    if not pay_date:
        pay_date = str(date.today())
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 20)
    pdf.cell(200, 12, "MAA SARASWATI COACHING CENTRE", ln=True, align='C')
    pdf.set_font("Arial", size=10)
    pdf.cell(200, 7, "ENGLISHPUR | Estd:- 10 March 2014", ln=True, align='C')
    pdf.cell(200, 7, "Email: sudhirkumarsingh986@gmail.com | Contact: 7654025302", ln=True, align='C')
    pdf.ln(10)

    pdf.set_fill_color(230, 230, 230)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, f"FEE RECEIPT - {month.upper()}", ln=True, align='C', fill=True)
    pdf.ln(5)

    pdf.set_font("Arial", size=12)
    pdf.cell(100, 10, f"Student Name: {name}")
    pdf.cell(100, 10, f"Date: {pay_date}", ln=True, align='R')
    pdf.cell(100, 10, f"Class: {s_class}")
    pdf.ln(10)

    pdf.set_font("Arial", 'B', 12)
    pdf.cell(95, 12, "Description", border=1, align='C')
    pdf.cell(95, 12, "Amount (Rs.)", border=1, ln=True, align='C')

    pdf.set_font("Arial", size=12)
    pdf.cell(95, 12, f"Monthly Fee ({month})", border=1)
    pdf.cell(95, 12, f"{amount}/-", border=1, ln=True, align='C')
    pdf.cell(95, 12, "Remaining Dues", border=1)
    pdf.cell(95, 12, f"{dues}/-", border=1, ln=True, align='C')

    pdf.ln(20)
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(200, 10, "Regards: Sudhir Kumar Singh (7654025302)", align='R')
    return pdf.output(dest='S')


def get_whatsapp_link(name, month, paying, current_dues, mobile):
    wa_msg = (
        f"*MAA SARASWATI COACHING CENTRE*\n\n"
        f"Dear Parent, Fee received for *{name}* for *{month}*.\n\n"
        f"Paid Amount: Rs. {paying}\n"
        f"Remaining Dues: Rs. {current_dues}\n\n"
        f"Regards,\n*Sudhir Kumar Singh*\n"
        f"Contact: 7654025302\n"
        f"Thank You!"
    )
    encoded_msg = urllib.parse.quote(wa_msg)
    return f"https://api.whatsapp.com/send?phone=91{mobile}&text={encoded_msg}"


# --- 4. SESSION STATE MANAGEMENT ---
if 'role' not in st.session_state:
    st.session_state['role'] = None
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'student_name' not in st.session_state:
    st.session_state['student_name'] = ""
if 'student_class' not in st.session_state:
    st.session_state['student_class'] = ""

CLASSES = [f"Class {i}" for i in range(1, 13)]
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November",
          "December"]

# --- 5. MAIN GATEWAY / LOGIN SCREEN ---
if not st.session_state['logged_in']:
    st.markdown("<h2 style='text-align: center; color: #E63946; margin-bottom:0;'>MAA SARASWATI COACHING</h2>",
                unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-size:13px;'>ENGLISHPUR | Contact: 7654025302</p>",
                unsafe_allow_html=True)

    login_tab1, login_tab2 = st.tabs(["🔒 Staff Portal", "👨‍🎓 Student Portal"])

    # ADMIN LOGIN
    with login_tab1:
        with st.form("admin_login_form"):
            u_name = st.text_input("Username")
            p_word = st.text_input("Password", type="password")
            if st.form_submit_button("Verify & Login"):
                if verify_user(u_name, p_word):
                    st.session_state['logged_in'] = True
                    st.session_state['role'] = 'admin'
                    st.session_state['username'] = u_name
                    st.success("Welcome Back Admin!")
                    st.rerun()
                else:
                    st.error("Invalid Admin Credentials.")

    # STUDENT PORTAL ACCESS
    with login_tab2:
        with st.form("student_access_form"):
            input_st_name = st.text_input("Enter Student Full Name")
            selected_class = st.selectbox("Select Your Class", CLASSES)
            submit_student = st.form_submit_button("Enter Student Dashboard 🚀")

            if submit_student:
                if input_st_name.strip() != "":
                    st.session_state['logged_in'] = True
                    st.session_state['role'] = 'student'
                    st.session_state['student_name'] = input_st_name.strip()
                    st.session_state['student_class'] = selected_class
                    st.success("Access Granted!")
                    st.rerun()
                else:
                    st.error("Kripya apna naam fill karein.")

# --- 6. CORE DASHBOARDS (AFTER LOGIN) ---
else:
    if st.sidebar.button("🚪 Log Out / Change Portal", use_container_width=True):
        st.session_state['logged_in'] = False
        st.session_state['role'] = None
        st.session_state['student_name'] = ""
        st.session_state['student_class'] = ""
        st.rerun()

    # ==========================================
    # A. ADMIN / STAFF PANEL SCREEN
    # ==========================================
    if st.session_state['role'] == 'admin':
        st.markdown("<h3 style='color:#1D3557; text-align:center;'>🏛️ Admin Panel</h3>", unsafe_allow_html=True)
        menu = ["Student Registration", "Fee Collection", "View Records", "📢 Homework & Notices", "Settings"]
        choice = st.selectbox("Menu Navigation", menu)
        st.divider()

        # 1. Student Registration
        if choice == "Student Registration":
            st.markdown("#### 📝 Register New Student")
            with st.form("reg_form", clear_on_submit=True):
                name = st.text_input("Full Name (Unique Identity)")
                father_name = st.text_input("Father's Name")
                s_class = st.selectbox("Class", CLASSES)
                address = st.text_input("Address", value="Englishpur")
                mobile = st.text_input("Mobile No")
                fee = st.number_input("Monthly Fee Amount (Rs.)", min_value=0.0, value=500.0)

                if st.form_submit_button("Register Student"):
                    if name.strip() and mobile.strip():
                        try:
                            c.execute(
                                "INSERT INTO students (name, father_name, class, address, mobile, monthly_fee) VALUES (?,?,?,?,?,?)",
                                (name.strip(), father_name.strip(), s_class, address.strip(), mobile.strip(), fee))
                            conn.commit()
                            st.success(f"Success! Registered: {name}")
                            st.rerun()
                        except sqlite3.IntegrityError:
                            st.error(f"Error: '{name}' ke naam se ID pehle se bni hui hai!")
                    else:
                        st.error("Fields khali nahi chhod sakte.")

            st.divider()
            st.markdown("#### 👥 Registered Students Data")
            df_students = pd.read_sql_query(
                "SELECT id, name, father_name, class, address, mobile, monthly_fee FROM students ORDER BY id DESC",
                conn)

            if not df_students.empty:
                for idx, row in df_students.iterrows():
                    father_val = row['father_name'] if row['father_name'] else ""
                    address_val = row['address'] if row['address'] else ""
                    with st.expander(f"👤 {row['name']} ({row['class']})"):
                        with st.form(f"edit_student_form_{row['id']}"):
                            u_name = st.text_input("Name", value=row['name'])
                            u_father = st.text_input("Father's Name", value=father_val)
                            u_class = st.selectbox("Class", CLASSES, index=CLASSES.index(row['class']))
                            u_address = st.text_input("Address", value=address_val)
                            u_mobile = st.text_input("Mobile", value=row['mobile'])
                            u_fee = st.number_input("Fee (Rs.)", min_value=0.0, value=float(row['monthly_fee']))

                            if st.form_submit_button("💾 Save Updates"):
                                try:
                                    c.execute(
                                        "UPDATE students SET name=?, father_name=?, class=?, address=?, mobile=?, monthly_fee=? WHERE id=?",
                                        (u_name.strip(), u_father.strip(), u_class, u_address.strip(), u_mobile.strip(),
                                         u_fee, row['id']))
                                    conn.commit()
                                    st.success("Details Updated!")
                                    st.rerun()
                                except sqlite3.IntegrityError:
                                    st.error("Yeh naam kisi doosre student ke liye already reserved hai!")

                            if st.form_submit_button("❌ Delete Student Profile"):
                                c.execute("DELETE FROM students WHERE id=?", (row['id'],))
                                conn.commit()
                                st.warning("Profile Deleted.")
                                st.rerun()
            else:
                st.info("Database khali hai.")

        # 2. Fee Collection Section
        elif choice == "Fee Collection":
            st.markdown("#### 💰 Fee Collection Manager")
            students_data = pd.read_sql_query("SELECT name FROM students", conn)
            if not students_data.empty:
                student_list = students_data['name'].tolist()
                selected_student = st.selectbox("Select Student", ["-- Choose Student --"] + student_list)

                if selected_student != "-- Choose Student --":
                    s_info = \
                    pd.read_sql_query("SELECT * FROM students WHERE name=?", conn, params=(selected_student,)).iloc[0]
                    reg_fee = s_info['monthly_fee']

                    st.info(f"Standard Fee Amount: Rs. {reg_fee}")
                    month = st.selectbox("Select Fee Month", MONTHS)
                    paying = st.number_input("Amount Depositing (Rs.)", min_value=0.0, value=float(reg_fee))
                    current_dues = reg_fee - paying
                    st.metric("Calculated Dues", f"Rs. {current_dues}")

                    if st.button("Submit Fee Transaction"):
                        c.execute(
                            "INSERT INTO fee_collection (name, class, month, paid_amount, dues, date) VALUES (?,?,?,?,?,?)",
                            (selected_student, s_info['class'], month, paying, current_dues, str(date.today())))
                        conn.commit()
                        st.success("Transaction Logged Successfully!")
                        st.rerun()
            else:
                st.info("Kripya pehle students register karein.")

            st.divider()
            st.markdown("#### 📝 Edit/Delete Recent Fee Slips")
            df_recent_fees = pd.read_sql_query(
                "SELECT id, name, class, month, paid_amount, dues, date FROM fee_collection ORDER BY id DESC LIMIT 10",
                conn)

            if not df_recent_fees.empty:
                for idx, f_row in df_recent_fees.iterrows():
                    with st.expander(f"💸 ID {f_row['id']}: {f_row['name']} ({f_row['month']})"):
                        with st.form(f"edit_fee_form_{f_row['id']}"):
                            edit_paid = st.number_input("Paid Amount", min_value=0.0, value=float(f_row['paid_amount']))
                            edit_dues = st.number_input("Dues Amount", min_value=0.0, value=float(f_row['dues']))

                            if st.form_submit_button("Update Slip Data"):
                                c.execute("UPDATE fee_collection SET paid_amount=?, dues=? WHERE id=?",
                                          (edit_paid, edit_dues, f_row['id']))
                                conn.commit()
                                st.success("Slip Updated!")
                                st.rerun()

                            if st.form_submit_button("🗑️ Delete Fee Record"):
                                c.execute("DELETE FROM fee_collection WHERE id=?", (f_row['id'],))
                                conn.commit()
                                st.warning("Transaction Record Cleared.")
                                st.rerun()

        # 3. View Records Logs
        elif choice == "View Records":
            # --- PIE CHART INTEGRATION ---
            st.markdown("#### 📈 Students Batch Distribution (Pie Chart)")
            df_pie_data = pd.read_sql_query("SELECT class FROM students", conn)

            if not df_pie_data.empty:
                class_counts = df_pie_data['class'].value_counts()

                fig, ax = plt.subplots(figsize=(6, 4))
                ax.pie(class_counts, labels=class_counts.index, autopct='%1.1f%%', startangle=90,
                       colors=plt.cm.Paired.colors)
                ax.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
                st.pyplot(fig)
            else:
                st.info("Pie Chart dikhane ke liye koi student registered nahi hai.")

            st.divider()
            st.markdown("#### 📊 Digital Ledger History Logs")
            query = """SELECT fc.id, fc.name, fc.class, fc.month, fc.paid_amount, fc.dues, fc.date, s.mobile, s.father_name, s.address 
                       FROM fee_collection fc LEFT JOIN students s ON fc.name = s.name ORDER BY fc.id DESC"""
            history_df = pd.read_sql_query(query, conn)

            if not history_df.empty:
                for idx, row in history_df.iterrows():
                    f_name_display = row['father_name'] if row['father_name'] else "N/A"
                    address_display = row['address'] if row['address'] else "Englishpur"
                    st.markdown(f"""
                    <div class="mobile-card">
                        <b>👤 Name:</b> {row['name']}<br>
                        <b>👨‍👦 Father's Name:</b> {f_name_display}<br>
                        <b>📍 Address:</b> {address_display}<br>
                        <b>🏫 Class:</b> {row['class']} | 📅 <b>Month:</b> {row['month']}<br>
                        <b>✅ Paid:</b> Rs. {row['paid_amount']}/- | ⚠️ <b>Dues:</b> Rs. {row['dues']}/-<br>
                        <small>Date: {row['date']}</small>
                    </div>
                    """, unsafe_allow_html=True)

                    mob = row['mobile'] if row['mobile'] else "7654025302"
                    wa_link_record = get_whatsapp_link(row['name'], row['month'], row['paid_amount'], row['dues'], mob)
                    pdf_bytes_record = create_pdf(row['name'], row['class'], row['month'], row['paid_amount'],
                                                  row['dues'], row['date'])
                    b64_record = base64.b64encode(pdf_bytes_record).decode()

                    m_btn1, m_btn2 = st.columns(2)
                    with m_btn1:
                        st.markdown(
                            f'<a href="data:application/pdf;base64,{b64_record}" download="Receipt_{row["name"]}.pdf" style="text-decoration:none;"><div style="background-color:#1D3557;color:white;padding:6px;text-align:center;border-radius:5px;font-size:12px;font-weight:bold;margin-bottom:15px;">Download PDF</div></a>',
                            unsafe_allow_html=True)
                    with m_btn2:
                        st.markdown(
                            f'<a href="{wa_link_record}" target="_blank" style="text-decoration:none;"><div style="background-color:#25D366;color:white;padding:6px;text-align:center;border-radius:5px;font-size:12px;font-weight:bold;margin-bottom:15px;">WhatsApp Notification</div></a>',
                            unsafe_allow_html=True)
            else:
                st.info("No logs available yet.")

        # 4. Homework & Notices
        elif choice == "📢 Homework & Notices":
            st.markdown("#### ✍️ Publish Homework / Notice Updates")
            with st.form("notice_form", clear_on_submit=True):
                n_type = st.radio("Type", ["📚 Homework", "📢 Official Notice"])
                n_title = st.text_input("Topic / Title")
                n_target = st.selectbox("Target Class", ["All Classes"] + CLASSES)
                n_content = st.text_area("Detailed Description Message")

                if st.form_submit_button("Publish Notification"):
                    if n_title and n_content:
                        c.execute("INSERT INTO notices (type, title, content, class_target, date) VALUES (?,?,?,?,?)",
                                  (n_type, n_title, n_content, n_target, str(date.today())))
                        conn.commit()
                        st.success("Published Successfully!")
                        st.rerun()
                    else:
                        st.error("Mandatory fields missing.")

            st.divider()
            st.markdown("#### 📋 Existing Active Notices Panel")
            df_notices = pd.read_sql_query(
                "SELECT id, type, title, content, class_target, date FROM notices ORDER BY id DESC", conn)

            if not df_notices.empty:
                for idx, n_row in df_notices.iterrows():
                    with st.expander(f"📌 [{n_row['class_target']}] {n_row['type']} - {n_row['title']}"):
                        with st.form(f"edit_notice_form_{n_row['id']}"):
                            en_title = st.text_input("Edit Title", value=n_row['title'])
                            en_target = st.selectbox("Edit Target Class", ["All Classes"] + CLASSES,
                                                     index=(["All Classes"] + CLASSES).index(n_row['class_target']))
                            en_content = st.text_area("Edit Details", value=n_row['content'])

                            if st.form_submit_button("Modify Notice"):
                                c.execute("UPDATE notices SET title=?, class_target=?, content=? WHERE id=?",
                                          (en_title, en_target, en_content, n_row['id']))
                                conn.commit()
                                st.success("Announcement updated!")
                                st.rerun()

                            if st.form_submit_button("🗑️ Permanent Remove Notice"):
                                c.execute("DELETE FROM notices WHERE id=?", (n_row['id'],))
                                conn.commit()
                                st.warning("Notice Deleted.")
                                st.rerun()

        # 5. Settings Panel
        elif choice == "Settings":
            st.markdown("#### ⚙️ Security Management")
            with st.form("pass_form"):
                old_p = st.text_input("Current Password", type="password")
                new_p = st.text_input("New Password", type="password")
                if st.form_submit_button("Update Password Credentials"):
                    if verify_user(st.session_state['username'], old_p):
                        c.execute("UPDATE users SET password=? WHERE username=?",
                                  (make_hashes(new_p), st.session_state['username']))
                        conn.commit()
                        st.success("Admin Credentials Updated!")
                    else:
                        st.error("Old password verification failed.")

    # ==========================================
    # B. STUDENT PORTAL DASHBOARD SCREEN
    # ==========================================
    elif st.session_state['role'] == 'student':
        st.balloons()
        st.snow()

        s_name = st.session_state['student_name']
        s_class = st.session_state['student_class']

        st.markdown(f"<h3 style='margin-bottom:0;'>👋 Welcome, {s_name.upper()}</h3>", unsafe_allow_html=True)
        st.markdown(f"<p style='font-size:14px; color:#555;'>Class: <b>{s_class}</b> | Center: <b>Englishpur</b></p>",
                    unsafe_allow_html=True)
        st.divider()

        st_tab1, st_tab2 = st.tabs(["📢 Notices & Homework", "💸 My Fee logs"])

        with st_tab1:
            st.markdown("#### 📌 Homework & Notifications from Sudhir Sir")
            notice_query = """SELECT * FROM notices WHERE class_target = 'All Classes' OR class_target = ? ORDER BY id DESC"""
            student_notices = pd.read_sql_query(notice_query, conn, params=(s_class,))

            if not student_notices.empty:
                for idx, row in student_notices.iterrows():
                    box_color = "#E8F8F5" if "Homework" in row['type'] else "#FEF9E7"
                    border_color = "#2ECC71" if "Homework" in row['type'] else "#F1C40F"

                    st.markdown(f"""
                        <div style="background-color:{box_color}; padding:12px; border-left:5px solid {border_color}; border-radius:5px; margin-bottom:12px;">
                            <span style="float:right; font-size:11px; color:#666;">📅 {row['date']}</span>
                            <b style="font-size:15px; color:#111;">{row['type']} - {row['title']}</b>
                            <p style="margin-top:8px; font-size:13px; white-space: pre-wrap; color:#222;">{row['content']}</p>
                        </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("✨ No active assignments found for your class batch.")

        with st_tab2:
            st.markdown("#### 💸 Personal Deposit Records")
            fee_query = "SELECT month, paid_amount, dues, date FROM fee_collection WHERE name LIKE ? ORDER BY id DESC"
            my_fees_df = pd.read_sql_query(fee_query, conn, params=(f"%{s_name}%",))

            if not my_fees_df.empty:
                total_paid = my_fees_df['paid_amount'].sum()
                pending_dues = my_fees_df['dues'].iloc[0]

                st.metric("Total Fees Paid Till Date", f"Rs. {total_paid}/-")
                st.metric("Latest Outstandings/Dues", f"Rs. {pending_dues}/-")
                st.divider()

                st.markdown("<b>Receipt History List:</b>", unsafe_allow_html=True)
                for idx, r in my_fees_df.iterrows():
                    st.markdown(f"""
                    <div class="mobile-card">
                        <b>📅 Month:</b> {r['month']}<br>
                        <b>💰 Amount Paid:</b> Rs. {r['paid_amount']}/-<br>
                        <b>⚠️ Dues Left:</b> Rs. {r['dues']}/-<br>
                        <small>Txn Date: {r['date']}</small>
                    </div>
                    """, unsafe_allow_html=True)

                    st_pdf_bytes = create_pdf(s_name, s_class, r['month'], r['paid_amount'], r['dues'], r['date'])
                    st_b64 = base64.b64encode(st_pdf_bytes).decode()
                    st.markdown(
                        f'<a href="data:application/pdf;base64,{st_b64}" download="Receipt_{r["month"]}.pdf" style="text-decoration:none;"><div style="background-color:#1D3557;color:white;padding:5px;text-align:center;border-radius:5px;font-size:12px;font-weight:bold;margin-bottom:15px;">📥 Download PDF Receipt</div></a>',
                        unsafe_allow_html=True)
            else:
                st.info("No payment history receipts logged under this student profile identity.")