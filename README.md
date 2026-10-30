# CollegeConnect

CollegeConnect is a Flask application with a MySQL database and static HTML,
CSS, and JavaScript pages.

## Deploy to Render

The repository includes a Render Blueprint at `render.yaml`. It deploys one
Python web service that serves both the frontend and API from the same origin,
so browser session cookies work without a separate static-site CORS setup.

The application currently uses MySQL. Render's Blueprint in this repository
does not provision a MySQL database; create or use a MySQL database that
accepts connections from Render before deploying. Render also offers managed
PostgreSQL, but switching to it requires a database-driver and schema migration
that this project has not implemented.

1. Push this repository to GitHub and create/connect a Render Blueprint for it.
   Render reads the repository-root `render.yaml`.
2. Before the first deployment, provide these service environment variables in
   Render using the connection details from your MySQL provider:
   - `DB_HOST`
   - `DB_PORT`
   - `DB_USER`
   - `DB_PASSWORD`
   - `DB_NAME`
3. The Blueprint generates `FLASK_SECRET_KEY`, enables secure session cookies,
   binds Gunicorn to Render's `$PORT`, and uses `/api/health` as its health
   check. Leave `CORS_ALLOWED_ORIGINS` blank for the single-origin deployment.
4. Run `database/schema.sql` against the production MySQL database before or
   immediately after deployment. The health check is database-dependent.
5. Open the Render service's `onrender.com` URL. The root route serves the
   landing page; API routes remain under `/api`.

Keep database credentials and local `.env` files out of source control. Use
Render's environment-variable settings for production secrets. For a production
launch, use a managed MySQL provider with backups and encrypted connections.
The schema creates empty classroom and timetable tables; load that data
separately before relying on those features. The analytics page is not
implemented yet. The project also does not currently include request
rate-limiting, so add it before opening account endpoints to a large public
audience.

## Run locally on Windows

1. Install Python 3.13 and MySQL. Run `database/schema.sql` in MySQL Workbench.
2. Create a local environment file:

   ```powershell
   Copy-Item .env.example .env
   ```

   Set the database values in `.env`. Replace the sample Flask secret with a
   long random value.
3. Create and activate a virtual environment, then install the backend
   dependencies:

   ```powershell
   cd C:\PROJECTS\CollegeConnect\backend
   py -3.13 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install -r requirements.txt
   ```

4. In the backend terminal, start Flask:

   ```powershell
   python app.py
   ```

5. In a second terminal from the project root, serve the frontend:

   ```powershell
   cd C:\PROJECTS\CollegeConnect
   py -3.13 -m http.server 8000 --bind 127.0.0.1
   ```

6. Visit `http://127.0.0.1:8000`. The frontend sends API requests to
   `http://127.0.0.1:5000`.

## Tests

Run the backend authentication and deployment-serving tests from `backend`:

```powershell
py -3.13 -m unittest test_auth -v
```

The tests use a mock database and do not create production users.
