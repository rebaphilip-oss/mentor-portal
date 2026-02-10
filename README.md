# Mentor Portal

A Streamlit-based portal for mentors to view their assigned and confirmed students.

## Features

- **View A: Assigned Students** - See all students assigned to you with onboarding status
  - Match confirmation status
  - Background shared status
  - Meeting progress

- **View B: Confirmed Students** - View confirmed students with:
  - Background info (city, graduation year, research area)
  - Program deadlines with status
  - Access to submission files

- **Preview Mode** - Team members can view the portal as any mentor

## Local Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the app:
   ```bash
   streamlit run app.py
   ```

3. Open http://localhost:8501 in your browser

## Deploy to Streamlit Cloud

1. Push this code to a GitHub repository

2. Go to [share.streamlit.io](https://share.streamlit.io)

3. Click "New app" and select your repository

4. Set the main file path to `app.py`

5. Add secrets in the Streamlit Cloud dashboard:
   - Go to App Settings > Secrets
   - Paste the contents of `.streamlit/secrets.toml`

## Configuration

Edit `.streamlit/secrets.toml` to configure:

- `AIRTABLE_API_KEY` - Your Airtable Personal Access Token
- `AIRTABLE_BASE_ID` - Your Airtable Base ID
- `STUDENT_TABLE` - Name of your student table
- `DEADLINES_TABLE` - Name of your deadlines table
- `MENTOR_TABLE` - Name of your mentor table
- `ADMIN_KEY` - Key for preview mode access

## Field Mapping

If your Airtable field names differ, update the field mappings in `app.py`:

- `STUDENT_FIELDS` - Maps student table fields
- `DEADLINE_FIELDS` - Maps deadline table fields
- `SUBMISSION_FIELDS` - List of submission attachment fields
