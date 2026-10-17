import datetime

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from . import calories
from .forms import PatientForm
from .models import History, Patient


def make_patient(owner, **overrides):
    fields = {
        "name": "Alex",
        "age": 30,
        "sex": "M",
        "weight_kg": 80,
        "height_cm": 180,
        "activity_level": "moderate",
    }
    fields.update(overrides)
    return Patient.objects.create(owner=owner, **fields)


class CalorieEstimateTests(TestCase):
    def test_bmr_male(self):
        # 10*80 + 6.25*180 - 5*30 + 5 = 1780
        self.assertEqual(calories.bmr(sex="M", age=30, weight_kg=80, height_cm=180), 1780)

    def test_bmr_female(self):
        # 10*60 + 6.25*165 - 5*40 - 161 = 1270.25
        self.assertEqual(calories.bmr(sex="F", age=40, weight_kg=60, height_cm=165), 1270.25)

    def test_target_applies_activity_factor(self):
        result = calories.estimate(
            sex="M", age=30, weight_kg=80, height_cm=180, activity_level="moderate"
        )
        self.assertAlmostEqual(result.target, 1780 * 1.55)
        self.assertAlmostEqual(result.low, result.target * 0.9)
        self.assertAlmostEqual(result.high, result.target * 1.1)

    def test_unknown_inputs_raise(self):
        with self.assertRaises(ValueError):
            calories.bmr(sex="X", age=30, weight_kg=80, height_cm=180)
        with self.assertRaises(ValueError):
            calories.estimate(
                sex="M", age=30, weight_kg=80, height_cm=180, activity_level="extreme"
            )

    def test_patient_save_stores_target(self):
        owner = User.objects.create_user("owner", password="pw-123456789")
        patient = make_patient(owner)
        self.assertEqual(patient.daily_calorie_target, round(1780 * 1.55))
        patient.weight_kg = 70
        patient.save()
        self.assertEqual(patient.daily_calorie_target, round(1680 * 1.55))


class AuthRequiredTests(TestCase):
    def test_anonymous_users_are_redirected_to_login(self):
        owner = User.objects.create_user("owner", password="pw-123456789")
        patient = make_patient(owner)
        urls = [
            reverse("view_patients"),
            reverse("new_patient"),
            reverse("patient_detail", args=[patient.id]),
            reverse("edit_patient", args=[patient.id]),
            reverse("view_history", args=[patient.id]),
            reverse("track_calories"),
        ]
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertRedirects(response, f"{reverse('users:login')}?next={url}")

    def test_anonymous_post_cannot_create_patient(self):
        self.client.post(reverse("new_patient"), {"name": "Eve"})
        self.assertFalse(Patient.objects.exists())

    def test_public_pages(self):
        for name in ["home", "users:login", "users:signup"]:
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_login_honors_next(self):
        User.objects.create_user("owner", password="pw-123456789")
        target = reverse("track_calories")
        response = self.client.post(
            reverse("users:login"),
            {"username": "owner", "password": "pw-123456789", "next": target},
        )
        self.assertRedirects(response, target)

    def test_signup_creates_and_logs_in_user(self):
        response = self.client.post(reverse("users:signup"), {
            "username": "newuser",
            "password1": "a-strong-passphrase-42",
            "password2": "a-strong-passphrase-42",
        })
        self.assertRedirects(response, reverse("view_patients"))
        self.assertTrue(User.objects.filter(username="newuser").exists())
        self.assertEqual(self.client.get(reverse("view_patients")).status_code, 200)


class OwnershipTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user("alice", password="pw-123456789")
        self.bob = User.objects.create_user("bob", password="pw-123456789")
        self.bobs_patient = make_patient(self.bob, name="Bob's patient")
        self.client.force_login(self.alice)

    def test_patient_list_only_shows_own_patients(self):
        make_patient(self.alice, name="Alice's patient")
        response = self.client.get(reverse("view_patients"))
        self.assertContains(response, "Alice&#x27;s patient")
        self.assertNotContains(response, "Bob&#x27;s patient")

    def test_other_users_patient_pages_404(self):
        pid = self.bobs_patient.id
        for name in ["patient_detail", "edit_patient", "view_history"]:
            with self.subTest(name=name):
                self.assertEqual(self.client.get(reverse(name, args=[pid])).status_code, 404)
        self.assertEqual(self.client.post(reverse("delete_patient", args=[pid])).status_code, 404)
        self.assertTrue(Patient.objects.filter(id=pid).exists())

    def test_cannot_log_calories_for_other_users_patient(self):
        response = self.client.post(reverse("track_calories"), {
            "patient": self.bobs_patient.id,
            "date": "2026-01-01",
            "calories": 2000,
        })
        self.assertEqual(response.status_code, 200)
        self.assertIn("patient", response.context["form"].errors)
        self.assertFalse(History.objects.exists())


class PageRenderTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("owner", password="pw-123456789")
        self.client.force_login(self.user)

    def test_empty_states(self):
        self.assertContains(self.client.get(reverse("view_patients")), "No patients yet")
        self.assertContains(self.client.get(reverse("track_calories")), "Add a patient before")

    def test_patient_pages_render(self):
        patient = make_patient(self.user)
        detail = self.client.get(reverse("patient_detail", args=[patient.id]))
        self.assertContains(detail, f"{patient.daily_calorie_target} kcal")
        self.assertContains(detail, "not medical advice")
        self.assertContains(self.client.get(reverse("edit_patient", args=[patient.id])), "80")
        history = self.client.get(reverse("view_history", args=[patient.id]))
        self.assertContains(history, "No logged")
        self.assertContains(self.client.get(reverse("new_patient")), "Imperial")

    def test_admin_link_only_for_staff(self):
        self.assertNotContains(self.client.get(reverse("home")), "Admin</a>")
        self.user.is_staff = True
        self.user.save()
        self.assertContains(self.client.get(reverse("home")), "Admin</a>")


class PatientFormTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("owner", password="pw-123456789")
        self.client.force_login(self.user)

    def form_data(self, **overrides):
        data = {
            "name": "Alex",
            "age": 30,
            "sex": "M",
            "units": "metric",
            "weight": 80,
            "height": 180,
            "activity_level": "moderate",
        }
        data.update(overrides)
        return data

    def test_create_assigns_owner_and_target(self):
        response = self.client.post(reverse("new_patient"), self.form_data())
        patient = Patient.objects.get()
        self.assertRedirects(response, reverse("patient_detail", args=[patient.id]))
        self.assertEqual(patient.owner, self.user)
        self.assertEqual(patient.daily_calorie_target, round(1780 * 1.55))

    def test_imperial_units_are_converted(self):
        form = PatientForm(self.form_data(units="imperial", weight=176.37, height=70.87))
        self.assertTrue(form.is_valid(), form.errors)
        patient = form.save(commit=False)
        self.assertAlmostEqual(patient.weight_kg, 80.0, places=1)
        self.assertAlmostEqual(patient.height_cm, 180.0, places=1)

    def test_required_and_out_of_range_inputs_are_rejected(self):
        cases = {
            "sex": {"sex": ""},
            "activity_level": {"activity_level": ""},
            "age": {"age": 5},
            "weight": {"weight": 0},
            "height": {"height": 1000},
        }
        for field, overrides in cases.items():
            with self.subTest(field=field):
                form = PatientForm(self.form_data(**overrides))
                self.assertFalse(form.is_valid())
                self.assertIn(field, form.errors)

    def test_edit_updates_target(self):
        patient = make_patient(self.user)
        self.client.post(reverse("edit_patient", args=[patient.id]), self.form_data(weight=70))
        patient.refresh_from_db()
        self.assertEqual(patient.weight_kg, 70)
        self.assertEqual(patient.daily_calorie_target, round(1680 * 1.55))

    def test_delete(self):
        patient = make_patient(self.user)
        url = reverse("delete_patient", args=[patient.id])
        self.assertEqual(self.client.get(url).status_code, 405)
        self.client.post(reverse("delete_patient", args=[patient.id]))
        self.assertFalse(Patient.objects.exists())


class HistoryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("owner", password="pw-123456789")
        self.patient = make_patient(self.user)
        self.client.force_login(self.user)

    def test_history_is_ordered_and_chart_context_is_json_safe(self):
        History.objects.create(patient=self.patient, date=datetime.date(2026, 3, 2), calories=2200)
        History.objects.create(patient=self.patient, date=datetime.date(2026, 1, 15), calories=1900)
        response = self.client.get(reverse("view_history", args=[self.patient.id]))
        chart = response.context["chart"]
        self.assertEqual(chart["labels"], ["2026-01-15", "2026-03-02"])
        self.assertEqual(chart["values"], [1900, 2200])
        self.assertEqual(chart["target"], self.patient.daily_calorie_target)
        self.assertContains(response, 'id="chart-data"')

    def test_log_entry(self):
        response = self.client.post(reverse("track_calories"), {
            "patient": self.patient.id,
            "date": "2026-01-01",
            "calories": 2000,
        })
        self.assertRedirects(response, reverse("view_history", args=[self.patient.id]))
        self.assertEqual(self.patient.history.get().calories, 2000)

    def test_invalid_entries_are_rejected(self):
        History.objects.create(patient=self.patient, date=datetime.date(2026, 1, 1), calories=2000)
        cases = {
            "duplicate day": {"date": "2026-01-01", "calories": 1800},
            "impossible date": {"date": "2026-02-30", "calories": 1800},
            "negative calories": {"date": "2026-01-02", "calories": -5},
        }
        for label, data in cases.items():
            with self.subTest(label):
                response = self.client.post(
                    reverse("track_calories"), {"patient": self.patient.id, **data}
                )
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context["form"].errors)
        self.assertEqual(History.objects.count(), 1)
