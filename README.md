# Calorie Recommendation

Django app that estimates a person's daily calorie needs and tracks their logged intake against that estimate.

## How the estimate works

The app uses the [Mifflin-St Jeor equation](https://pubmed.ncbi.nlm.nih.gov/2305711/) for basal metabolic rate (BMR):

- Men: `10 * weight_kg + 6.25 * height_cm - 5 * age + 5`
- Women: `10 * weight_kg + 6.25 * height_cm - 5 * age - 161`

BMR is multiplied by a standard activity factor (1.2 sedentary, 1.375 light, 1.55 moderate, 1.725 active, 1.9 very active) to estimate total daily energy expenditure. The app shows a range of plus or minus 10% because individual needs vary. The code is in `main/calories.py`.

The estimate is for healthy adults (age 18 to 100) and is not medical advice.

Earlier versions used a Keras model trained on `diet_recommendations_dataset.csv`. That dataset's calorie column is statistically random, so no model trained on it could beat predicting the average. See `docs/FIX_LIST.md` (P0-1) for the analysis.

## Features

- Accounts with sign up, log in and log out. Every page except home, log in and sign up requires login.
- Each user manages their own patients, and other users can't see them.
- Add, edit and delete patients, with metric or imperial input.
- Daily calorie log with one entry per patient per day, charted against the estimated target.

## Quick start

Requires Python 3.12+.

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
export DJANGO_DEBUG=1              # Windows: set DJANGO_DEBUG=1
python manage.py migrate
python manage.py createsuperuser   # optional, for /admin/
python manage.py runserver
```

Open http://127.0.0.1:8000/ and sign up.

`DJANGO_DEBUG=1` enables a throwaway secret key and allows localhost. With debug off, `DJANGO_SECRET_KEY` and `DJANGO_ALLOWED_HOSTS` are required. See `.env.example` for every setting.

## Development

```bash
ruff check .
python manage.py test
python manage.py makemigrations --check --dry-run
```

CI (`.github/workflows/ci.yml`) runs the same checks on every push to `main` and on every pull request.

## Deploying

Set `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS` and, if served over HTTPS, `DJANGO_CSRF_TRUSTED_ORIGINS`, `DJANGO_SECURE_SSL_REDIRECT=1` and `DJANGO_SECURE_HSTS_SECONDS`. Run `python manage.py check --deploy` and `python manage.py collectstatic`. SQLite is fine for a single-user demo; use Postgres for anything shared.

## Project structure

- `main/calories.py`: the Mifflin-St Jeor calculation
- `main/models.py`: `Patient` (owned by a user, stores its calorie target) and `History` (daily intake)
- `main/views.py`, `main/forms.py`, `main/urls.py`: patient and calorie log pages
- `users/`: sign up, plus Django's login and logout views
- `templates/`: shared layout and nav/footer partials
- `main/static/`: CSS and a vendored, pinned Chart.js 4.4.6
