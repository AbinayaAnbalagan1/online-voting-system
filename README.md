# Online Voting System

A web-based voting system built with Flask and SQLite. Voters register, verify their email with a one-time password (OTP), and cast one vote. Results update automatically, and an admin panel manages candidates, voters, and an audit log.

## Features

- User registration and login
- Email OTP verification using Gmail SMTP
- Passwords stored as SHA-256 hashes
- One vote per user, enforced by the database
- Live results page that refreshes every 10 seconds
- Admin panel to add or edit candidates and view voters
- Audit log of key actions (last 50 entries shown in the admin panel)
- Admin option to reset votes

## Tech stack

- **Backend:** Python, Flask
- **Database:** SQLite (`voting.db`)
- **Frontend:** HTML, CSS, JavaScript (Jinja2 templates)
- **Email:** Gmail SMTP

## Project structure

```
online-voting-system/
├── app.py              # Routes, database setup, and OTP logic
├── voting.db           # SQLite database (created on first run)
└── templates/
    ├── base.html
    ├── login.html
    ├── register.html
    ├── verify_otp.html
    ├── vote.html
    ├── results.html
    └── admin.html
```

## Getting started

### Prerequisites

- Python 3.10 or newer
- A Gmail account with a 16-digit **App Password** (Google Account → Security → 2-Step Verification → App passwords)

### Setup

1. Clone the repository and open the folder:
   ```bash
   git clone https://github.com/your-username/online-voting-system.git
   cd online-voting-system
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   venv\Scripts\activate        # Windows
   source venv/bin/activate     # macOS/Linux
   ```
3. Install Flask and Flask-SQLAlchemy:
   ```bash
   pip install flask flask-sqlalchemy
   ```
4. In `app.py`, set your email details:
   ```python
   EMAIL_ADDRESS  = "your_email@gmail.com"
   EMAIL_PASSWORD = "your_16_digit_app_password"
   ```
   Do not commit your real password to GitHub. See the security notes below.
5. Run the app:
   ```bash
   python app.py
   ```
6. Open `http://127.0.0.1:5000` in your browser.

### Default admin login

- Username: `admin`
- Password: `admin123`

Change this password before using the system outside a test environment.

## How it works

1. A user registers with a username, email, and password. The password is hashed with SHA-256 before it is saved.
2. The system emails a one-time password to the user.
3. The user enters the OTP to verify their email.
4. A verified user can cast one vote for a candidate.
5. The results page shows the current counts and refreshes every 10 seconds.
6. The admin panel lets the admin manage candidates, view voters, read the audit log, and reset votes.

## Security notes

- Passwords are hashed with SHA-256. This is a basic approach for a student project. A production system should use a salted, slow hashing method such as bcrypt or Argon2.
- Email credentials are currently stored in `app.py`. Move them to environment variables (a `.env` file kept out of GitHub) before publishing.
- The default admin password should be changed.

## Future improvements

- Salted password hashing (bcrypt or Argon2)
- Move credentials to environment variables
- Time-limited voting periods
- Export results as a CSV or PDF report

## Author

**Abinaya Anbalagan**
B.E. Computer Science and Engineering, Paavai Engineering College
