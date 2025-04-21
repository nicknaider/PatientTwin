import pytest
from app import analyze_reading, Reading
from datetime import datetime

def make_reading(**kwargs):
    # создаём «голое» Reading без записи в БД
    defaults = {
        'patient_id': 1,
        'patient_name': 'X',
        'age': 0,
        'temperature': None,
        'systolic': None,
        'diastolic': None,
        'overall_condition': '',
        'cough': '',
        'sore_throat': False,
        'shortness_of_breath': False,
        'chest_pain': False,
        'timestamp': datetime.fromisoformat('2025-01-01T00:00:00')
    }
    defaults.update(kwargs)
    return Reading(**defaults)

def test_no_alerts_when_all_normal():
    r = make_reading(
        temperature=36.5,
        systolic=120,
        diastolic=80,
        chest_pain=False,
        sore_throat=False,
        shortness_of_breath=False
    )
    assert analyze_reading(r) == []

def test_temperature_alert():
    r = make_reading(temperature=38.2)
    alerts = analyze_reading(r)
    # проверяем, что в списке есть хоть один алерт с текстом "Температура"
    assert any("Температура" in a for a in alerts)

def test_pressure_alerts():
    r = make_reading(systolic=150, diastolic=95)
    alerts = analyze_reading(r)
    # проверяем наличие текста про систолическое и диастолическое
    assert any("Систолическое давление" in a for a in alerts)
    assert any("Диастолическое давление" in a for a in alerts)

def test_symptom_alerts():
    r = make_reading(chest_pain=True, sore_throat=True, shortness_of_breath=True)
    alerts = analyze_reading(r)
    assert "Боль в груди" in alerts
    assert "Боль в горле" in alerts
    assert "Одышка" in alerts
