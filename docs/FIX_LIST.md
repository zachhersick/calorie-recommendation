# Fix List

Audit of the repository as of commit `2d9803e`.

> **Status:** Every item below is addressed in code by the follow-up pull request that replaced the Keras model with the Mifflin-St Jeor equation. Two parts of P1-1 can't be done in a pull request and still need doing by hand: change the passwords for `su` and `zach` (and anywhere they were reused), and, if the repository is or was public, purge `db.sqlite3` from git history with `git filter-repo --path db.sqlite3 --invert-paths` followed by a force-push. Items are ordered by priority inside each tier. Every item says what is wrong, where, why it matters, and what to do instead. Line numbers refer to that commit.

Tiers:

- **P0**: invalidates the project or prevents it from running. Fix before anything else.
- **P1**: security, data integrity, or correctness bugs a user will hit.
- **P2**: wrong engineering choices that make the code fragile or misleading.
- **P3**: cleanup, polish, and hygiene.

---

## Summary

The core problem is not Keras vs. RandomForest. The dataset has no signal for the target. `Daily_Caloric_Intake` in `diet_recommendations_dataset.csv` is statistically indistinguishable from uniform random integers between 1500 and 3500, and it is independent of every feature. No model of any kind can learn it. The app therefore shows a number that is effectively the dataset mean (about 2475 kcal) dressed up as a personalized clinical recommendation. Everything else on this list is secondary to that.

After that, the app does not start from a fresh clone, has no access control on any view, and ships the developer's SQLite database (with password hashes and a live session) in git.

---

## P0: Project-invalidating

### P0-1. The target variable is random noise. No model can predict it.

- **Where:** `diet_recommendations_dataset.csv`, used by `model.py:13-25`.
- **What is wrong:** I ran this check against the committed CSV (1000 rows):
  - Pearson correlation of `Daily_Caloric_Intake` with every numeric column is between -0.071 and +0.026 (Age -0.009, Weight_kg -0.071, Height_cm 0.026, Weekly_Exercise_Hours 0.018).
  - The target's histogram over 1500 to 3500 in 10 bins is flat (93, 107, 112, 94, 110, 109, 106, 96, 84, 89). A Kolmogorov-Smirnov test against Uniform(1500, 3500) gives p = 0.21, so uniform noise cannot be rejected. Std is 565; a uniform distribution on that range has std 577.
  - Group means go the wrong way physiologically: Sedentary 2535 kcal, Moderate 2468, Active 2423. Men 2457, women 2495.
  - The Mifflin-St Jeor TDEE computed from the same rows correlates with the target at **-0.097**.
  - 5-fold cross-validated results on the exact 7 features `model.py` uses:

    | Model | MAE (kcal) | R² |
    |---|---|---|
    | Predict the mean (DummyRegressor) | 486.0 | -0.001 |
    | LinearRegression | 485.1 | -0.001 |
    | RandomForestRegressor (300 trees) | 499.8 | -0.077 |
    | HistGradientBoostingRegressor | 519.7 | -0.212 |
    | RandomForest on **all 19** columns | n/a | -0.038 |

  Every model is at or worse than "always predict 2475". This is a synthetic Kaggle-style dataset generated with independent random columns.
- **Why it matters:** The product's single feature is fake. Whatever the Keras net outputs is either close to the mean or overfit noise. Calling that a "personalized" or "data-backed" recommendation for "clinicians" (`main/templates/index.html:9-10`) is false and, for a health app, potentially harmful.
- **What to do instead:** Pick one:
  1. **Recommended:** Drop ML for the recommendation. Compute BMR with Mifflin-St Jeor (`10*kg + 6.25*cm - 5*age + 5` for men, `-161` for women) and multiply by a standard activity factor (1.2 / 1.375 / 1.55 / 1.725 / 1.9). This is the method dietitians actually use, is deterministic, explainable, and needs no TensorFlow. Optionally add a goal adjustment (for example -500 kcal/day for loss).
  2. If ML is a hard requirement (for a class, for example), find a dataset where the label is real and causally linked to the features, and prove the model beats both the mean baseline and Mifflin-St Jeor on a held-out set before shipping it.
  3. If you keep this dataset for a class demo, say plainly in the README and UI that the model has no predictive power and why.

### P0-2. The label means the wrong thing even if it were real.

- **Where:** `model.py:24-25` (`y = df['Daily_Caloric_Intake']`).
- **What is wrong:** `Daily_Caloric_Intake` is how much a person eats, not how much they should eat. The dataset's own `Disease_Type` column includes Obesity and Diabetes. A model trained on observed intake learns to reproduce current eating habits, including the habits that caused the condition.
- **Why it matters:** "Predict intake" and "recommend intake" are different problems. Even with a perfect model, the app would recommend that an overeating patient keep overeating.
- **What to do instead:** Frame the output as an energy requirement estimate (see P0-1 option 1), or train on a target that represents a recommendation (for example a clinician-prescribed target or measured energy expenditure), not self-reported consumption.

### P0-3. The app cannot start from a fresh clone.

- **Where:** `main/ml_predict.py:10-16`, `.gitignore:72-74`, `README.md:15-22`.
- **What is wrong:** `ml_predict.py` loads `calorie_model.h5` and `scaler.pkl` at import time. Both are gitignored (`*.h5`, `*.pkl`) and not in the repo. `main/urls.py` imports `views`, which imports `ml_predict`, and Django's system checks import the URLconf, so **every** `manage.py` command (including `migrate`, `check`, and `test`) imports TensorFlow and tries to load the missing files. I confirmed `manage.py migrate --plan` reaches `ml_predict.py` and fails there. The README never tells you to run `model.py` first.
- **Why it matters:** Nobody else can run the project. `migrate` failing because a model file is missing is also a sign the model loading is in the wrong place.
- **What to do instead:** If you keep a model: load it lazily on first prediction (a cached function), not at import. Either commit the small artifacts (or publish them as a release asset) or document `python model.py` as a required step. If you follow P0-1 option 1, this whole module goes away.

### P0-4. `SECRET_KEY` is required but undocumented.

- **Where:** `calorieRecommendation/settings.py:24`, `README.md:15-22`.
- **What is wrong:** `os.environ["SECRET_KEY"]` raises `KeyError` if unset. I confirmed `manage.py check` fails with `KeyError: 'SECRET_KEY'`. The README quick start does not mention it.
- **Why it matters:** Second hard failure on first run. Reading the key from the environment is the right idea; the missing piece is documentation and a dev path.
- **What to do instead:** Document it in the README, add a `.env.example`, and either load `.env` (for example with `django-environ` or `python-dotenv`) or fall back to an insecure dev key only when `DEBUG` is on.

---

## P1: Security, data integrity, correctness

### P1-1. The development database is committed, with password hashes and a live session.

- **Where:** `db.sqlite3` (tracked despite `.gitignore:53-54`).
- **What is wrong:** The committed DB contains `auth_user` rows for `su` (superuser) and `zach` with their PBKDF2 hashes, one row in `django_session`, and patient records including the name "Zach" with age, weight, and height.
- **Why it matters:** Anyone who can read the repo can run an offline dictionary attack against the superuser hash. If the same password is used elsewhere, that is exposed too. Health data for a real person is in version control.
- **What to do instead:** `git rm --cached db.sqlite3`. Change the passwords for both accounts and anywhere they were reused. If the repo is or was public, rewrite history (`git filter-repo --path db.sqlite3 --invert-paths`) and force-push. Use fixtures or a seed management command for demo data.

### P1-2. No view requires login.

- **Where:** `main/views.py:8-75` (every view), `main/templates/new_patient.html:9`, `main/templates/track_calories.html:8`.
- **What is wrong:** Access control is done in templates with `{% if user.is_authenticated %}`, which only hides the form. The views still accept POSTs from anonymous users, and `view_patients`, `predict_result`, and `view_history` render patient data to anyone. An anonymous GET to `/patients/new/` gets a blank card.
- **Why it matters:** Any visitor can read every patient's data and create records. Template checks are not authorization.
- **What to do instead:** Decorate every view with `@login_required` (or use `LoginRequiredMixin` / Django 5.1+ `LoginRequiredMiddleware`). Set `LOGIN_URL = "users:login"` in settings, because the default `/accounts/login/` does not exist in this project.

### P1-3. Patients are not owned by users. Every user sees every patient.

- **Where:** `main/models.py:5-33`, `main/views.py:23,34,38,60,71`.
- **What is wrong:** `Patient` has no foreign key to `User` (`User` is imported on line 2 and never used). `Patient.objects.all()` and `get_object_or_404(Patient, id=...)` are unscoped, so any ID in the URL works (IDOR).
- **Why it matters:** Once login exists, user A can still read and log calories for user B's patients by changing a number in the URL.
- **What to do instead:** Add `owner = models.ForeignKey(User, on_delete=models.CASCADE)`, set it in `new_patient`, and filter every query by `owner=request.user` (`get_object_or_404(Patient, id=..., owner=request.user)`).

### P1-4. A patient with no activity level crashes the prediction page; missing values are silently misencoded.

- **Where:** `main/models.py:19-32` (`null=True, blank=True` on `gender` and `physical_activity_level`), `main/ml_predict.py:36,47`.
- **What is wrong:** The form lets you leave both fields empty. Then `patient.physical_activity_level.strip()` raises `AttributeError` on `None` (500 error). A missing gender becomes `Gender_Male = 0`, so the model silently treats the patient as female. An empty-string activity level would fall through to the all-zero baseline, which means "Active".
- **Why it matters:** Required model inputs are optional in the schema, and the encoder hides the problem instead of rejecting it.
- **What to do instead:** Make both fields required (`null=False, blank=False`, with a migration). In the feature encoder, raise on unknown values instead of defaulting.

### P1-5. No input validation or range checks.

- **Where:** `main/models.py:18,25,26,33`, `main/models.py:39-42`, `main/forms.py`.
- **What is wrong:** Age, weight, height, and exercise hours accept zero, negatives, and absurd values. The training data covers age 18 to 79, weight 50 to 119.7 kg, height 150 to 199 cm, exercise 0 to 10 h. History accepts month 13, day 31 in February, year 0, and negative calories.
- **Why it matters:** A neural net extrapolates without bound outside its training range, so out-of-range input produces arbitrary numbers. Invalid dates break chronological sorting and charts.
- **What to do instead:** Add `MinValueValidator` / `MaxValueValidator` to the model fields that match the range the calculator is valid for. Use `PositiveIntegerField` where appropriate. Replace the date triple with a `DateField` (P2-6).

### P1-6. `DEBUG = True` and `ALLOWED_HOSTS = []` are hardcoded.

- **Where:** `calorieRecommendation/settings.py:27,29`.
- **Why it matters:** Any deploy exposes stack traces and settings on errors. Hardcoding means you will forget to flip it.
- **What to do instead:** Read `DEBUG` and `ALLOWED_HOSTS` from the environment, default `DEBUG` to `False`. Run `python manage.py check --deploy` before any deployment and fix what it reports (secure cookies, HSTS, `STATIC_ROOT`).

### P1-7. Admin link is gated on a hardcoded username.

- **Where:** `main/templates/partials/_nav_main.html:18`.
- **What is wrong:** `{% if user.username == "su" %}`.
- **Why it matters:** It hides the link from real staff and is the wrong concept. It is not a security hole on its own (admin checks `is_staff`), but it is the wrong check.
- **What to do instead:** `{% if user.is_staff %}` and `{% url 'admin:index' %}` instead of a hardcoded `/admin/`.

### P1-8. Chart data is injected with `|safe`.

- **Where:** `main/templates/view_calorie_history.html:51-52`.
- **What is wrong:** A Python list's `repr` is pasted into a `<script>` with escaping disabled. It works today only because the values are integers and the labels are built from integers.
- **Why it matters:** The first time a string field (patient name, a note) goes into that context, it is an XSS hole. Python `repr` is also not JSON (for example `None`, `True`).
- **What to do instead:** Use `{{ labels|json_script:"labels" }}` and `JSON.parse(document.getElementById('labels').textContent)`.

### P1-9. Chart.js is loaded from a CDN with no version pin or integrity hash.

- **Where:** `main/templates/view_calorie_history.html:48`.
- **What is wrong:** `https://cdn.jsdelivr.net/npm/chart.js` resolves to whatever "latest" is that day.
- **Why it matters:** A major release can break the chart overnight, and an unpinned third-party script on a page with health data is a supply-chain risk.
- **What to do instead:** Pin an exact version and add `integrity` and `crossorigin` attributes, or vendor the file into `main/static/`.

### P1-10. Login hardcodes `next`, which breaks redirects.

- **Where:** `users/templates/registration/login.html:21`.
- **What is wrong:** `<input type="hidden" name="next" value="{% url 'home' %}" />` overrides the `?next=` that `login_required` will add.
- **Why it matters:** After P1-2, users will always land on home instead of the page they tried to open.
- **What to do instead:** Use `value="{{ next }}"` and set `LOGIN_REDIRECT_URL = "home"` in settings for the default.

### P1-11. No user registration.

- **Where:** `users/views.py`, `users/urls.py`.
- **What is wrong:** Only Django's built-in login/logout URLs exist. Accounts can only be made through `createsuperuser` or the admin.
- **Why it matters:** Combined with P1-2/P1-3, the multi-user story is incomplete.
- **What to do instead:** Add a signup view using `UserCreationForm`, or state in the README that accounts are admin-created.

---

## P2: Wrong or fragile engineering choices

### P2-1. Keras is the wrong tool here, and RandomForest is not the fix either.

- **Where:** `model.py:6-8,37-54`, `requirements.txt:8`, `main/ml_predict.py:4,15`.
- **What is wrong:** A 4x64 dense network with dropout (about 13k parameters) trained on 640 rows and 7 features. For small tabular regression, the standard defaults are linear models and tree ensembles (RandomForest, gradient boosting), which need no scaling, train in milliseconds, and usually beat MLPs at this size. The table in P0-1 shows that on this data none of them work, because there is nothing to learn.
- **Why it matters:** TensorFlow adds hundreds of megabytes to the install, slows Django startup and every management command (P0-3), and makes training non-deterministic. It brings all the cost of deep learning and none of the benefit.
- **What to do instead:** Remove TensorFlow. Use the Mifflin-St Jeor calculator (P0-1). If you later find a real dataset, start with a scikit-learn `Pipeline` of `OneHotEncoder` + `HistGradientBoostingRegressor` or `RidgeCV`, compare it against the mean baseline and the formula, and only move to anything heavier if it measurably wins.

### P2-2. Training-serving skew: categorical encoding is reimplemented by hand.

- **Where:** `model.py:21` (`pd.get_dummies(..., drop_first=True)`), `main/ml_predict.py:34-58`.
- **What is wrong:** Training uses `get_dummies` with `drop_first`, which silently drops the alphabetically first category ("Active", "Female"). Serving reimplements this with hardcoded strings, and the comment on line 42 says the baseline is "likely Active or something". It happens to be correct, but only by luck. Gender is encoded as `"M"` in the DB versus `"Male"` in the CSV, which is another hand-maintained mapping.
- **Why it matters:** Any change to categories, column order, or spelling silently produces wrong inputs with no error.
- **What to do instead:** Fit a single scikit-learn `Pipeline` (`ColumnTransformer` with `OneHotEncoder(handle_unknown="error")` and the model) and serialize the whole pipeline. At serving time, build a one-row DataFrame with the original column names and call `pipeline.predict`. One artifact replaces `calorie_model.h5`, `scaler.pkl`, and `feature_columns.json`.

### P2-3. Evaluation methodology is not sufficient to know whether the model works.

- **Where:** `model.py:28-33,54,76-79`.
- **What is wrong:**
  - The scaler is fit on all rows before the train/test split (line 29 before line 33). That is test-set leakage. Small here, but wrong.
  - No baseline. Test MAE is printed without comparing it to "predict the mean" (about 486 kcal), so a useless model looks fine.
  - One random 80/20 split with no cross-validation on 1000 rows gives a noisy estimate.
  - No early stopping; a fixed 100 epochs.
  - No seed for TensorFlow, so results change on every run.
  - The target is unscaled (values around 2500) with MSE loss and Adam at the default learning rate. That makes training slow to converge and the loss curves hard to read.
- **Why it matters:** These are exactly the steps that would have shown P0-1 immediately.
- **What to do instead:** Split first, then fit preprocessing on train only (a `Pipeline` does this). Use `cross_validate` with k-fold. Always report a `DummyRegressor` baseline and, for this problem, the Mifflin-St Jeor formula as a second baseline. Set seeds. Report MAE and R².

### P2-4. `model.py` is a notebook pasted into a script.

- **Where:** `model.py:14-15,35,51,64,74,84`.
- **What is wrong:** `df.head()` and `X_train.shape` are no-op expressions. `plt.show()` blocks twice. `import json` is at the bottom. Everything runs at module level with no `if __name__ == "__main__":`. It writes artifacts into the repo root using relative paths, so it breaks if run from another directory. It sits at the repo root next to `manage.py` rather than in a training package.
- **Why it matters:** It is not reproducible or importable, and it cannot run in CI or headless.
- **What to do instead:** Move to `ml/train.py` (or a `manage.py train_model` command) with a `main()`, argparse for paths and seed, `plt.savefig` instead of `show`, and artifacts written to a dedicated `artifacts/` directory. If P0-1 option 1 is chosen, delete it.

### P2-5. Model artifact format is legacy.

- **Where:** `model.py:82`, `main/ml_predict.py:10`.
- **What is wrong:** `.h5` is the legacy HDF5 format. Keras 3 (bundled with TF 2.20) treats it as legacy and recommends `.keras`.
- **What to do instead:** Moot if TensorFlow is removed (P2-1). Otherwise save as `.keras`.

### P2-6. Dates are stored as three integers.

- **Where:** `main/models.py:38-43`, `main/forms.py:37-59`, `main/views.py:40-42`.
- **What is wrong:** `month`, `day`, `year` as separate `IntegerField`s.
- **Why it matters:** No validation (Feb 31 is accepted), awkward ordering, no date queries ("last 7 days"), manual label formatting, US-only display.
- **What to do instead:** One `date = models.DateField()` with a `DateInput(attrs={"type": "date"})` widget, `ordering = ["date"]` in `Meta`, and a `UniqueConstraint(fields=["patient", "date"])` if one entry per day is intended (otherwise sum per day in the view).

### P2-7. Predictions are not stored or compared against tracked intake.

- **Where:** `main/views.py:22-31`, `main/views.py:37-50`.
- **What is wrong:** The recommendation is recomputed on every page load and thrown away. The history page charts intake with no target line.
- **Why it matters:** The two features (recommendation and tracking) never connect, which is the obvious value of the app. If the inputs change, there is no record of what was recommended.
- **What to do instead:** Compute the target when a patient is saved or updated (store it on `Patient` or in a `Recommendation` model with a timestamp). Draw it as a horizontal line on the history chart.

### P2-8. Patients cannot be edited or deleted.

- **Where:** `main/urls.py`, `main/views.py`.
- **Why it matters:** Weight changes over time and drives the recommendation. Right now the only path is to create a duplicate patient.
- **What to do instead:** Add update and delete views (scoped to the owner, P1-3). Consider storing weight over time if tracking progress is a goal.

### P2-9. "Patient" vs. "your information" framing is inconsistent.

- **Where:** `main/templates/new_patient.html:5,10`, `main/templates/track_calories.html:9`, `main/templates/index.html:10`.
- **What is wrong:** The model and nav say "Patient"; the forms say "Enter your information"; the home page says it is "built for clinicians".
- **Why it matters:** It is unclear whether this is a personal tracker or a clinician tool, and that decides the data model (P1-3), the privacy obligations, and the wording.
- **What to do instead:** Decide. For a personal tracker, link one profile to the logged-in user and drop the patient list. For a clinician tool, keep patients owned by a clinician user and add a medical disclaimer.

### P2-10. Dependencies are wrong or bloated.

- **Where:** `requirements.txt`, `pyproject.toml`.
- **What is wrong:**
  - `requirements.txt:5` contains `:contentReference[oaicite:0]{index=0}`, a pasted ChatGPT citation artifact.
  - `tensorflow` and `matplotlib` are runtime requirements but are only needed for training (and TF is not needed at all after P2-1).
  - `joblib` is imported directly (`model.py:10`, `ml_predict.py:3`) but only installed transitively through scikit-learn.
  - `pyproject.toml` contains a bare `requires-python = "==3.12.*"` with no `[project]` table, so no tool reads it. `==3.12.*` is also needlessly strict.
  - No dev dependencies (linting, tests).
- **What to do instead:** Split runtime (`Django`) from training/dev dependencies. Either drop `pyproject.toml` or make it a valid `[project]` table with `requires-python = ">=3.12"` and dependency groups. Remove the artifact line.

### P2-11. Missing settings for login and static files.

- **Where:** `calorieRecommendation/settings.py`.
- **What is wrong:** No `LOGIN_URL`, `LOGIN_REDIRECT_URL`, `LOGOUT_REDIRECT_URL`, or `STATIC_ROOT`. `TEMPLATES['DIRS']` is empty while a shared base template lives inside the `main` app and is extended from the `users` app.
- **What to do instead:** Add the auth URL settings (P1-2, P1-10). Add `STATIC_ROOT` for `collectstatic`. Move shared templates (`index_base.html`, partials) to a project-level `templates/` directory listed in `DIRS`.

---

## P3: Cleanup and hygiene

### P3-1. Files committed despite `.gitignore`.

- **Where:** `.DS_Store`, `db.sqlite3` (see P1-1), `diet_recommendations_dataset.csv` (`.gitignore:68` ignores `*.csv`).
- **What to do instead:** `git rm --cached .DS_Store`. Decide whether the CSV belongs in git. If it stays, add an explicit `!diet_recommendations_dataset.csv` exception or move it to `data/` with a README on where it came from and its license. If P0-1 option 1 is chosen, remove it.

### P3-2. Stray duplicate templates from another project.

- **Where:** `users/templates/registration/login 2.html`, `users/templates/registration/logged_out 2.html`.
- **What is wrong:** macOS Finder duplicates. `logged_out 2.html:6,10` says "Football Game".
- **What to do instead:** Delete both.

### P3-3. Dead templates, scripts, and imports.

- **Where:**
  - `main/templates/predict.html`: no view renders it. Its fake progress steps ("Scaling features…") are theater around a millisecond computation.
  - `main/templates/conf.html`: no view renders it.
  - `main/static/scripts/script.js`: never included by any template.
  - `main/views.py:2`: `import time` unused.
  - `main/views.py:15`: `patient = form.save()` assigns an unused variable.
  - `main/urls.py:1,4`: `admin` and `predict_result` imported and unused.
  - `main/models.py:2`: `User` imported and unused (use it for P1-3).
  - `users/models.py`, `users/admin.py`, `users/views.py`, `users/tests.py`: empty stubs.
- **What to do instead:** Delete the unused files and imports. Add `ruff` to catch these automatically.

### P3-4. README is inaccurate.

- **Where:** `README.md`.
- **What is wrong:**
  - Line 25: "Visit `/predict`". There is no such route. The route is `/predict/<id>/`.
  - Line 39: "Adjust the artificial processing delay in `main/views.py`". No delay exists (only an unused `import time`).
  - Line 35: refers to `ml_predict.py` at the root; it is `main/ml_predict.py`.
  - Line 13 lists `calorie_model.h5` and `scaler.pkl` as if present; they are not (P0-3).
  - No mention of `SECRET_KEY` (P0-4), training, creating a user, calorie tracking, or the dataset's source and limits (P0-1).
- **What to do instead:** Rewrite after the P0 fixes so the quick start works verbatim on a fresh clone.

### P3-5. No tests and no CI.

- **Where:** `main/tests.py`, `users/tests.py`.
- **What to do instead:** Add tests for, at minimum:
  - The calorie calculation for known inputs (hand-checked Mifflin-St Jeor values).
  - Anonymous access redirects to login on every view (P1-2).
  - User A cannot see or modify user B's patients (P1-3).
  - Invalid inputs are rejected (P1-4, P1-5).
  - History ordering and chart context.

  Add a GitHub Actions workflow that runs `ruff check`, `python manage.py check`, `makemigrations --check`, and the tests.

### P3-6. Migration history noise.

- **Where:** `main/migrations/0004_history.py:18-21`, `main/migrations/0001_initial.py`, `main/migrations/0002_patient_name.py:16`.
- **What is wrong:** `max_length` on `IntegerField` (undone in 0005). `bmi` and `daily_caloric_intake` added then removed. `name` defaulted to the literal `'user'`.
- **What to do instead:** Since the only database is a local dev DB (and it should leave git, P1-1), squash or reset the migrations into one clean `0001_initial` after the model changes in P1-3, P1-4, P1-5, and P2-6.

### P3-7. Model field details.

- **Where:** `main/models.py`.
- **What is wrong:**
  - `name = models.CharField(default='user')` has no `max_length` (allowed on SQLite and Postgres in Django 4.2+, but not portable) and a meaningless default.
  - `height_cm` is an `IntegerField` while `weight_kg` is a `FloatField`, which is inconsistent.
  - `History` has no `Meta.ordering`, no `created_at`, and is not registered in admin (`main/admin.py` only registers `Patient`).
  - Gender is binary-only with no explanation. If the formula needs a sex input, label it "Sex (used for BMR formula)" so the reason is clear.
  - Imperial units are not supported at all.
- **What to do instead:** `max_length=100` and no default on `name`. Pick one numeric type for body measurements. Register `History`. Add an optional unit toggle in the form that converts to metric before saving.

### P3-8. No medical disclaimer or uncertainty.

- **Where:** `main/templates/prediction_result.html:11-13`, `main/templates/index.html:9-10`.
- **What is wrong:** A single number is presented as "Recommended daily calories" with marketing copy about clinicians and data-backed guidance.
- **What to do instead:** Show the method used, a range (validation studies put Mifflin-St Jeor within 10% of measured resting energy expenditure for most, not all, adults), and a short "not medical advice" note. Remove claims the model cannot support.

### P3-9. Frontend details.

- **Where:** templates.
- **What is wrong:**
  - Nav links to pages that render empty for anonymous users (`_nav_main.html:9-11`).
  - The track-calories `<select>` has no `id` for its `<label>` (`track_calories.html:13-14`), which breaks accessibility, and renders empty with no message when there are no patients.
  - Inline `style=` attributes scattered across templates (`view_patients.html:15-16`, `prediction_result.html:26`, `view_calorie_history.html:14`).
  - No `<meta name="viewport">` in `index_base.html`, so the "responsive" layout claimed in the README does not scale on phones.
  - Footer hardcodes `© 2025` (`_footer.html:2`).
- **What to do instead:** Hide nav items for anonymous users, label the select properly, move inline styles to CSS, add the viewport meta tag, and use `{% now "Y" %}` in the footer.

---

## Suggested order of work

1. P1-1 (rotate passwords, remove `db.sqlite3` from git). Do this today; it is the only item with ongoing exposure.
2. P0-1 and P0-2: decide on the formula approach. This decision removes P0-3, P2-1 through P2-5, and most of P2-10.
3. P0-4, P1-6, P2-11: settings and README so the app runs from a fresh clone.
4. P1-2, P1-3, P1-10, P1-11: authentication and ownership.
5. P1-4, P1-5, P2-6: data model and validation, then P3-6 to squash migrations.
6. P3-5: tests and CI, written alongside steps 4 and 5.
7. P2-7, P2-8, P2-9: product features that connect recommendation and tracking.
8. Remaining P3 cleanup.
