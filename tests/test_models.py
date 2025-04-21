import pytest
from app import db, Patient, Reading
from datetime import datetime

def test_patient_and_reading_saving(app):
    # сохраняем пациента
    p = Patient(
        patient_name="Иванов И.И.",
        age=45,
        disease="Грипп",
        frequency=7,
        health_indicators="Темп., Давление"
    )
    db.session.add(p)
    db.session.commit()

    assert Patient.query.count() == 1
    saved = Patient.query.first()
    assert saved.patient_name == "Иванов И.И."

    # сохраняем измерение с корректным datetime
    r = Reading(
        patient_id=saved.id,
        patient_name=saved.patient_name,
        age=saved.age,
        temperature=37.1,
        systolic=118,
        diastolic=78,
        cough="нет",
        sore_throat=False,
        shortness_of_breath=False,
        chest_pain=False,
        overall_condition="OK",
        timestamp=datetime.fromisoformat("2025-01-01T10:00:00")
    )
    db.session.add(r)
    db.session.commit()

    assert Reading.query.count() == 1
    saved_r = Reading.query.first()
    assert saved_r.patient_id == saved.id
    assert saved_r.temperature == 37.1
