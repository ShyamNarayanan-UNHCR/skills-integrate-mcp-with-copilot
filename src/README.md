# Mergington High School Activities API

A super simple FastAPI application that allows students to view and sign up for extracurricular activities.

## Features

- View all available extracurricular activities
- Teacher sign-in to register and unregister students
- Public viewing of activity rosters

## Getting Started

1. Install the dependencies:

   ```
   pip install fastapi uvicorn
   ```

2. Create a teacher account. The password is stored as a salted PBKDF2 hash in the
   local `src/teachers.json` file; the file is ignored by Git.

   ```
   python src/create_teacher.py
   ```

3. Run the application from the repository root:

   ```
   uvicorn app:app --app-dir src --reload
   ```

4. Open your browser and go to:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

Set `SESSION_SECRET` to a stable, randomly generated value when deploying the
application. For HTTPS deployments, also set `SESSION_COOKIE_SECURE=true`.

## API Endpoints

| Method | Endpoint                                                          | Description                                                           |
| ------ | ----------------------------------------------------------------- | --------------------------------------------------------------------- |
| GET    | `/activities`                                                     | Public list of activities and participant rosters                     |
| GET    | `/auth/session`                                                   | Check whether the current browser session is signed in                 |
| POST   | `/auth/login`                                                     | Sign in with a teacher username and password                           |
| POST   | `/auth/logout`                                                    | Sign out                                                               |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Register a student (teacher sign-in required)                          |
| DELETE | `/activities/{activity_name}/unregister?email=student@mergington.edu` | Unregister a student (teacher sign-in required)                     |

## Data Model

The application uses a simple data model with meaningful identifiers:

1. **Activities** - Uses activity name as identifier:

   - Description
   - Schedule
   - Maximum number of participants allowed
   - List of student emails who are signed up

2. **Students** - Uses email as identifier.

All data is stored in memory, which means data will be reset when the server restarts.
