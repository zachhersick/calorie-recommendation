# Calorie Recommendation

Modern Django app that collects basic patient info, runs a local ML model, and suggests daily caloric intake with a polished UI/UX.

## Features
- Quick calorie prediction with animated progress overlay
- Clean dark theme with card-based layout and responsive nav/footer
- Login/logout screens styled to match the app (nav hidden when signed out)
- Patient snapshots and clear result presentation

## Stack
- Python 3.x, Django
- Local ML model artifacts (`calorie_model.h5`, `scaler.pkl`, `feature_columns.json`)

## Quick start
```bash
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

## Usage
- Visit `/predict` to enter patient info and run the model.
- Watch the loader and step-by-step progress text; the result appears after processing.
- Authentication:
  - `/users/login/` to sign in (nav hidden on auth pages).
  - `/users/logout/` to sign out.

## Project structure (selected)
- `main/templates/` — pages and shared layout (`index_base.html`) with nav/footer partials
- `main/static/css/` — global, nav, footer styling and loading animation
- `main/views.py` — request handlers, including prediction workflow
- `model.py` / `ml_predict.py` — model integration helpers

## Notes
- Model files are local; no external API calls are required.
- Adjust the artificial processing delay in `main/views.py` if you want faster/slower visible progress.
