import streamlit as st
from pyairtable import Api
import pandas as pd
from datetime import datetime, timedelta, timezone
import resend
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature

# Page config
st.set_page_config(
    page_title="Mentor Portal",
    page_icon="👨‍🏫",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Airtable connection
@st.cache_resource
def get_airtable_api():
    api = Api(st.secrets["AIRTABLE_API_KEY"])
    return api

@st.cache_resource
def get_tables():
    api = get_airtable_api()
    base = api.base(st.secrets["AIRTABLE_BASE_ID"])
    return {
        "students": base.table(st.secrets["STUDENT_TABLE"]),
        "deadlines": base.table(st.secrets["DEADLINES_TABLE"]),
        "mentors": base.table(st.secrets["MENTOR_TABLE"])
    }

# Magic Link Authentication
def get_serializer():
    return URLSafeTimedSerializer(st.secrets["MAGIC_LINK_SECRET"])

def generate_magic_token(email):
    """Generate a signed token containing the email"""
    serializer = get_serializer()
    return serializer.dumps(email, salt="magic-link")

def verify_magic_token(token, max_age=3600):
    """Verify token and return email if valid (default 1 hour expiry)"""
    serializer = get_serializer()
    try:
        email = serializer.loads(token, salt="magic-link", max_age=max_age)
        return email
    except (SignatureExpired, BadSignature):
        return None

def send_magic_link(email, mentor_name):
    """Send magic link email to mentor"""
    resend.api_key = st.secrets["RESEND_API_KEY"]

    token = generate_magic_token(email)
    # Get the base URL from secrets or construct from request
    base_url = st.secrets.get("APP_URL", "http://localhost:8501")
    magic_link = f"{base_url}?token={token}"

    try:
        r = resend.Emails.send({
            "from": st.secrets.get("FROM_EMAIL", "Mentor Portal <onboarding@resend.dev>"),
            "to": [email],
            "subject": "Your Mentor Portal Login Link",
            "html": f"""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h2 style="color: #1E3A5F;">Welcome to the Mentor Portal</h2>
                <p>Hi {mentor_name},</p>
                <p>Click the button below to access your mentor dashboard:</p>
                <p style="margin: 30px 0;">
                    <a href="{magic_link}"
                       style="background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%);
                              color: white;
                              padding: 12px 30px;
                              text-decoration: none;
                              border-radius: 6px;
                              display: inline-block;">
                        Access Portal
                    </a>
                </p>
                <p style="color: #64748B; font-size: 14px;">
                    This link will expire in 1 hour for security reasons.<br>
                    If you didn't request this link, you can safely ignore this email.
                </p>
            </div>
            """
        })
        return True
    except Exception as e:
        st.error(f"Failed to send email: {e}")
        return False

# Field mappings (adjust these to match your exact Airtable field names)
STUDENT_FIELDS = {
    "name": "Student Cohort Application Tracker",
    "mentor": "Mentor Name",
    "research_area": "Research Area - First Preference",
    "city": "City of Residence",
    "graduation_year": "Graduation Year",
    "mentor_confirmation": "Mentor Confirmation",
    "background_shared": "OB: Mentor Background Shared",
    "expected_meetings": "Number of Expected Meetings - Student/Mentor",
    "completed_meetings": "[Current + Archived] No. of Meetings Completed",
    "notes_summary": "Mentor-Student Notes Summary",
    "hours_recorded": "[Current + Archived] No. of Hours Recorded"
}

DEADLINE_FIELDS = {
    "name": "Deadline Name",
    "type": "Deadline Type",
    "due_date": "Due Date (in use, updated to reflect student's timeline)",
    "status": "Deadline Status",
    "date_submitted": "Date Submitted",
    "student_link": "Student Application & Cohort Tracker"
}

# Submission file fields (these may be attachments or lookups)
SUBMISSION_FIELDS = [
    "Syllabus Submission (From Mentor)",
    "Research Question",
    "Research Proposal",
    "Research Outline",
    "Milestone",
    "Final Paper",
    "Revised Final Paper",
    "Target Publication Submission"
]

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1E3A5F;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.1rem;
        color: #64748B;
        margin-bottom: 2rem;
    }
    .student-card {
        background: white;
        border-radius: 12px;
        padding: 1.5rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        margin-bottom: 1rem;
        border-left: 4px solid #4F46E5;
    }
    .status-confirmed {
        background-color: #DEF7EC;
        color: #03543F;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 500;
    }
    .status-pending {
        background-color: #FEF3C7;
        color: #92400E;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 500;
    }
    .status-not-sent {
        background-color: #FEE2E2;
        color: #991B1B;
        padding: 0.25rem 0.75rem;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 500;
    }
    .metric-card {
        background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%);
        border-radius: 12px;
        padding: 1.5rem;
        color: white;
    }
    .deadline-submitted {
        background-color: #DEF7EC;
        border-left: 4px solid #10B981;
    }
    .deadline-pending {
        background-color: #FEF3C7;
        border-left: 4px solid #F59E0B;
    }
    .deadline-overdue {
        background-color: #FEE2E2;
        border-left: 4px solid #EF4444;
    }
    .preview-banner {
        background-color: #FEF3C7;
        border: 1px solid #F59E0B;
        border-radius: 8px;
        padding: 0.75rem 1rem;
        margin-bottom: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# Session state initialization
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "mentor_name" not in st.session_state:
    st.session_state.mentor_name = None
if "mentor_email" not in st.session_state:
    st.session_state.mentor_email = None
if "is_preview" not in st.session_state:
    st.session_state.is_preview = False
if "magic_link_sent" not in st.session_state:
    st.session_state.magic_link_sent = False

# Helper functions
@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_mentor_by_email(email):
    """Find mentor by email in Mentor Table"""
    tables = get_tables()
    try:
        records = tables["mentors"].all(formula=f"LOWER({{Email}}) = LOWER('{email}')")
        if records:
            record = records[0]
            return {
                "id": record["id"],
                "name": record["fields"].get("Name") or record["fields"].get("Mentor Name", ""),
                "email": record["fields"].get("Email", "")
            }
    except Exception as e:
        st.error(f"Error fetching mentor: {e}")
    return None

@st.cache_data(ttl=300)
def get_students_for_mentor(mentor_name):
    """Get all students assigned to a mentor"""
    tables = get_tables()
    try:
        # Use FIND to search for mentor name in the linked field
        formula = f"FIND('{mentor_name}', ARRAYJOIN({{Mentor Name}}))"
        records = tables["students"].all(formula=formula)

        students = []
        for record in records:
            fields = record["fields"]
            students.append({
                "id": record["id"],
                "name": fields.get(STUDENT_FIELDS["name"], "Unknown"),
                "research_area": fields.get(STUDENT_FIELDS["research_area"], ""),
                "city": fields.get(STUDENT_FIELDS["city"], ""),
                "graduation_year": fields.get(STUDENT_FIELDS["graduation_year"], ""),
                "mentor_confirmation": fields.get(STUDENT_FIELDS["mentor_confirmation"], ""),
                "background_shared": fields.get(STUDENT_FIELDS["background_shared"], ""),
                "expected_meetings": fields.get(STUDENT_FIELDS["expected_meetings"], 0),
                "completed_meetings": fields.get(STUDENT_FIELDS["completed_meetings"], 0),
                "notes_summary": fields.get(STUDENT_FIELDS["notes_summary"], ""),
                "hours_recorded": fields.get(STUDENT_FIELDS["hours_recorded"], "")
            })
        return students
    except Exception as e:
        st.error(f"Error fetching students: {e}")
        return []

@st.cache_data(ttl=300)
def get_deadlines_for_student(student_name):
    """Get all deadlines for a specific student"""
    tables = get_tables()
    try:
        # Search for student name in Deadline Name field
        formula = f"FIND('{student_name.split('|')[0].strip()}', {{Deadline Name}})"
        records = tables["deadlines"].all(formula=formula)

        deadlines = []
        for record in records:
            fields = record["fields"]

            # Collect submission files
            submissions = {}
            for field in SUBMISSION_FIELDS:
                value = fields.get(field)
                if value:
                    submissions[field] = value

            deadlines.append({
                "id": record["id"],
                "name": fields.get(DEADLINE_FIELDS["name"], ""),
                "type": fields.get(DEADLINE_FIELDS["type"], ""),
                "due_date": fields.get(DEADLINE_FIELDS["due_date"], ""),
                "status": fields.get(DEADLINE_FIELDS["status"], ""),
                "date_submitted": fields.get(DEADLINE_FIELDS["date_submitted"], ""),
                "submissions": submissions
            })

        # Sort by due date
        deadlines.sort(key=lambda x: x["due_date"] or "9999-99-99")
        return deadlines
    except Exception as e:
        st.error(f"Error fetching deadlines: {e}")
        return []

def format_duration(value):
    """Format a duration value (seconds from Airtable API) as h:mm"""
    if not value and value != 0:
        return "N/A"
    # If already a formatted string like "1:40", return as-is
    if isinstance(value, str):
        return value if value else "N/A"
    # Airtable returns duration fields as seconds
    try:
        total_seconds = int(value)
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        return f"{hours}:{minutes:02d}"
    except (ValueError, TypeError):
        return str(value)

def format_date(date_str):
    """Format date string for display"""
    if not date_str:
        return "Not set"
    # Handle list values (e.g. from Airtable lookup fields)
    if isinstance(date_str, list):
        date_str = date_str[0] if date_str else ""
    if not date_str:
        return "Not set"
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        return date_obj.strftime("%b %#d, %Y")
    except:
        return date_str

def format_datetime_ist(date_str):
    """Format an ISO datetime string to a friendly format in IST (UTC+5:30)"""
    if not date_str:
        return "Not set"
    # Handle list values (e.g. from Airtable lookup fields)
    if isinstance(date_str, list):
        date_str = date_str[0] if date_str else ""
    if not date_str:
        return "Not set"
    try:
        # Parse ISO format (e.g. '2026-01-31T18:49:57.000Z')
        date_str = date_str.strip("'\"")
        date_obj = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%fZ")
        # Convert from UTC to IST (UTC+5:30)
        ist = timezone(timedelta(hours=5, minutes=30))
        date_obj = date_obj.replace(tzinfo=timezone.utc).astimezone(ist)
        return date_obj.strftime("%b %#d, %Y %#I:%M %p IST")
    except:
        # Fallback: try plain date format
        return format_date(date_str)

def format_notes_summary(text):
    """Parse and format notes summary text for better display"""
    if not text:
        return ""

    import re

    lines = text.strip().split('\n')
    formatted_lines = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Detect headers (ALL CAPS lines or lines ending with colon)
        if line.isupper() and len(line) > 2:
            # Convert ALL CAPS to Title Case for headers
            formatted_lines.append(f"**{line.title()}**")
        elif line.endswith(':') and len(line) < 50:
            # Lines ending with colon are likely section headers
            formatted_lines.append(f"**{line}**")
        elif line.startswith(('-', '•', '*', '–')):
            # Already a bullet point
            formatted_lines.append(line)
        elif re.match(r'^\d+[\.\)]\s', line):
            # Numbered list item
            formatted_lines.append(line)
        else:
            formatted_lines.append(line)

    return '\n\n'.join(formatted_lines)

def is_overdue(due_date_str, status):
    """Check if deadline is overdue"""
    if status == "Submitted":
        return False
    if not due_date_str:
        return False
    try:
        due_date = datetime.strptime(due_date_str, "%Y-%m-%d")
        return due_date < datetime.now()
    except:
        return False

# Check for magic link token in URL
def check_magic_link_token():
    query_params = st.query_params
    if "token" in query_params and not st.session_state.authenticated:
        token = query_params["token"]
        email = verify_magic_token(token)
        if email:
            mentor = get_mentor_by_email(email)
            if mentor:
                st.session_state.authenticated = True
                st.session_state.mentor_name = mentor["name"]
                st.session_state.mentor_email = mentor["email"]
                st.session_state.is_preview = False
                # Clear the token from URL
                st.query_params.clear()
                st.rerun()
        else:
            st.error("This login link has expired or is invalid. Please request a new one.")
            st.query_params.clear()

# LOGIN PAGE
def show_login_page():
    st.markdown('<p class="main-header">Mentor Portal</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Access your student dashboard</p>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("### Sign In")

        # Check if magic link was just sent
        if st.session_state.magic_link_sent:
            st.success("Check your email! We've sent you a magic link to access the portal.")
            st.info("The link will expire in 1 hour.")
            if st.button("Send another link"):
                st.session_state.magic_link_sent = False
                st.rerun()
        else:
            # Regular mentor login with magic link
            with st.form("login_form"):
                email = st.text_input("Email Address", placeholder="Enter your mentor email")
                submitted = st.form_submit_button("Send Magic Link", use_container_width=True)

                if submitted and email:
                    mentor = get_mentor_by_email(email)
                    if mentor:
                        if send_magic_link(mentor["email"], mentor["name"]):
                            st.session_state.magic_link_sent = True
                            st.rerun()
                    else:
                        st.error("Email not found. Please check your email address.")

        st.markdown("---")

        # Preview mode for team members
        with st.expander("🔍 Team Preview Mode"):
            st.caption("For team members to preview any mentor's view")
            with st.form("preview_form"):
                preview_email = st.text_input("Mentor's Email", placeholder="Enter mentor email to preview")
                admin_key = st.text_input("Admin Key", type="password", placeholder="Enter admin key")
                preview_submitted = st.form_submit_button("Preview as Mentor", use_container_width=True)

                if preview_submitted:
                    if admin_key == st.secrets["ADMIN_KEY"]:
                        mentor = get_mentor_by_email(preview_email)
                        if mentor:
                            st.session_state.authenticated = True
                            st.session_state.mentor_name = mentor["name"]
                            st.session_state.mentor_email = mentor["email"]
                            st.session_state.is_preview = True
                            st.rerun()
                        else:
                            st.error("Mentor email not found.")
                    else:
                        st.error("Invalid admin key.")

# MAIN DASHBOARD
def show_dashboard():
    # Sidebar
    with st.sidebar:
        st.markdown(f"### Welcome, {st.session_state.mentor_name}")
        st.caption(st.session_state.mentor_email)

        if st.session_state.is_preview:
            st.warning("👁️ Preview Mode")

        st.markdown("---")

        view = st.radio(
            "Select View",
            ["📋 Assigned Students", "✅ Confirmed Students"],
            label_visibility="collapsed"
        )

        st.markdown("---")

        if st.button("🔄 Refresh Data"):
            st.cache_data.clear()
            st.rerun()

        if st.button("🚪 Logout"):
            st.session_state.authenticated = False
            st.session_state.mentor_name = None
            st.session_state.mentor_email = None
            st.session_state.is_preview = False
            st.rerun()

    # Preview mode banner
    if st.session_state.is_preview:
        st.markdown(
            '<div class="preview-banner">👁️ <strong>Preview Mode:</strong> You are viewing this portal as ' +
            st.session_state.mentor_name + '</div>',
            unsafe_allow_html=True
        )

    # Get students
    students = get_students_for_mentor(st.session_state.mentor_name)

    if view == "📋 Assigned Students":
        show_assigned_students(students)
    else:
        show_confirmed_students(students)

# VIEW A: ASSIGNED STUDENTS
def show_assigned_students(students):
    st.markdown('<p class="main-header">Assigned Students</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Track onboarding progress for all assigned students</p>', unsafe_allow_html=True)

    if not students:
        st.info("No students assigned to you yet.")
        return

    # Summary metrics
    total = len(students)
    confirmed = sum(1 for s in students if s["mentor_confirmation"] == "Yes")
    pending = total - confirmed

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Assigned", total)
    with col2:
        st.metric("Confirmed", confirmed)
    with col3:
        st.metric("Pending Confirmation", pending)

    # Debug: Show field mappings
    with st.expander("🔧 Debug: Field Mappings"):
        st.markdown("**Summary Metrics:**")
        st.markdown(f"- **Total Assigned**: Count of students linked via `{STUDENT_FIELDS['mentor']}`")
        st.markdown(f"- **Confirmed**: Count where `{STUDENT_FIELDS['mentor_confirmation']}` = 'Yes'")
        st.markdown(f"- **Pending Confirmation**: Total - Confirmed")
        st.markdown("---")
        st.markdown("**Student Card Fields:**")
        st.markdown(f"- **Student Name**: `{STUDENT_FIELDS['name']}`")
        st.markdown(f"- **Research Area**: `{STUDENT_FIELDS['research_area']}`")
        st.markdown(f"- **Match Confirmation**: `{STUDENT_FIELDS['mentor_confirmation']}`")
        st.markdown(f"- **Background Shared**: `{STUDENT_FIELDS['background_shared']}`")
        st.markdown(f"- **Meetings Completed**: `{STUDENT_FIELDS['completed_meetings']}`")
        st.markdown(f"- **Expected Meetings**: `{STUDENT_FIELDS['expected_meetings']}`")

    st.markdown("---")

    # Student list
    for student in students:
        with st.container():
            col1, col2 = st.columns([3, 1])

            with col1:
                st.markdown(f"#### {student['name']}")
                st.caption(f"🎯 {student['research_area']}" if student['research_area'] else "Research area not set")

            with col2:
                # Confirmation status
                if student["mentor_confirmation"] == "Yes":
                    st.success("✅ Confirmed")
                else:
                    st.warning("⏳ Pending")

            # Onboarding status details
            col1, col2, col3 = st.columns(3)

            with col1:
                st.markdown("**Match Confirmation**")
                if student["mentor_confirmation"] == "Yes":
                    st.markdown('<span class="status-confirmed">Confirmed</span>', unsafe_allow_html=True)
                else:
                    st.markdown('<span class="status-pending">Pending</span>', unsafe_allow_html=True)

            with col2:
                st.markdown("**Background Shared**")
                if student["background_shared"] == "Yes":
                    st.markdown('<span class="status-confirmed">Yes</span>', unsafe_allow_html=True)
                else:
                    st.markdown('<span class="status-not-sent">Not Yet</span>', unsafe_allow_html=True)

            with col3:
                st.markdown("**Meetings**")
                completed = student.get("completed_meetings", 0) or 0
                expected = student.get("expected_meetings", 0) or 0
                st.markdown(f"{completed} / {expected} completed")

            st.markdown("---")

# VIEW B: CONFIRMED STUDENTS
def show_confirmed_students(students):
    st.markdown('<p class="main-header">Confirmed Students</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">View backgrounds, deadlines, and submissions</p>', unsafe_allow_html=True)

    # Filter to confirmed students only
    confirmed_students = [s for s in students if s["mentor_confirmation"] == "Yes"]

    if not confirmed_students:
        st.info("No confirmed students yet. Students will appear here once they confirm the mentor match.")
        return

    # Student selector
    student_names = [s["name"] for s in confirmed_students]
    selected_student_name = st.selectbox("Select Student", student_names)

    selected_student = next((s for s in confirmed_students if s["name"] == selected_student_name), None)

    if not selected_student:
        return

    st.markdown("---")

    # Tabs for different sections
    tab1, tab2, tab3 = st.tabs(["📝 Background", "📅 Deadlines", "📁 Submissions"])

    with tab1:
        show_student_background(selected_student)

    with tab2:
        show_student_deadlines(selected_student)

    with tab3:
        show_student_submissions(selected_student)

def show_student_background(student):
    st.markdown("### Student Background")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**📍 City of Residence**")
        st.markdown(student["city"] or "Not specified")

        st.markdown("**🎓 Graduation Year**")
        st.markdown(str(student["graduation_year"]) if student["graduation_year"] else "Not specified")

    with col2:
        st.markdown("**🔬 Research Area**")
        st.markdown(student["research_area"] or "Not specified")

        st.markdown("**📊 Meetings Progress**")
        completed = student.get("completed_meetings", 0) or 0
        expected = student.get("expected_meetings", 0) or 0
        if expected > 0:
            progress = completed / expected
            st.progress(progress)
            st.caption(f"{completed} of {expected} meetings completed")
        else:
            st.markdown("No meetings scheduled")

        st.markdown("**⏱️ Hours Recorded**")
        st.markdown(format_duration(student.get("hours_recorded", "")))

    if student.get("notes_summary"):
        st.markdown("---")
        st.markdown("**📝 Notes Summary**")
        formatted_notes = format_notes_summary(student["notes_summary"])
        st.markdown(formatted_notes)

def show_student_deadlines(student):
    st.markdown("### Program Deadlines")

    deadlines = get_deadlines_for_student(student["name"])

    if not deadlines:
        st.info("No deadlines found for this student.")
        return

    for deadline in deadlines:
        status = deadline["status"]
        due_date = deadline["due_date"]
        overdue = is_overdue(due_date, status)

        # Determine styling
        if status == "Submitted":
            container_class = "deadline-submitted"
            icon = "✅"
        elif overdue:
            container_class = "deadline-overdue"
            icon = "⚠️"
        else:
            container_class = "deadline-pending"
            icon = "📅"

        with st.container():
            col1, col2, col3 = st.columns([2, 1, 1])

            with col1:
                st.markdown(f"{icon} **{deadline['type']}**")

            with col2:
                st.markdown(f"**Due:** {format_date(due_date)}")

            with col3:
                if status == "Submitted":
                    st.success(f"Submitted {format_datetime_ist(deadline['date_submitted'])}")
                elif overdue:
                    st.error("Overdue")
                else:
                    st.warning("Not Submitted")

            st.markdown("---")

def show_student_submissions(student):
    st.markdown("### Submission Files")

    deadlines = get_deadlines_for_student(student["name"])

    has_submissions = False

    for deadline in deadlines:
        if deadline.get("submissions"):
            for field_name, value in deadline["submissions"].items():
                has_submissions = True

                st.markdown(f"**{deadline['type']}**")

                # Handle different types of submission values
                if isinstance(value, list):
                    # Attachments are usually a list of dicts with url, filename
                    for attachment in value:
                        if isinstance(attachment, dict):
                            url = attachment.get("url", "")
                            filename = attachment.get("filename", "Download")
                            if url:
                                st.markdown(f"📎 [{filename}]({url})")
                        else:
                            st.markdown(f"📎 {attachment}")
                elif isinstance(value, str) and value.startswith("http"):
                    st.markdown(f"📎 [View Submission]({value})")
                else:
                    st.markdown(f"📄 {value}")

                st.markdown("---")

    if not has_submissions:
        st.info("No submissions available yet.")

# Main app logic
def main():
    # Check for magic link token first
    check_magic_link_token()

    if not st.session_state.authenticated:
        show_login_page()
    else:
        show_dashboard()

if __name__ == "__main__":
    main()
