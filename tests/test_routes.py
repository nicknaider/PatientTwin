from flask import url_for
from app import db, Patient, Reading

def test_schedule_route_posts_and_redirects(client):
    data = {
        'patient_name': 'Пупкин П.П.',
        'age': '30',
        'disease': 'ОРВИ',
        'frequency': '3',
        'health_indicators': 'Темп.'
    }
    resp = client.post('/schedule', data=data, follow_redirects=False)
    # после POST редирект на /schedule
    assert resp.status_code == 302
    assert resp.headers['Location'].endswith('/schedule')
    # пациент оказался в БД
    assert Patient.query.filter_by(patient_name='Пупкин П.П.').one()

def test_readings_route_posts_and_redirects(client):
    # сначала создаём пациента
    client.post('/schedule', data={
        'patient_name': 'Тест Т.Т.',
        'age': '40',
        'disease': 'Тест',
        'frequency': '1',
        'health_indicators': 'T'
    })
    p = Patient.query.first()
    data = {
        'patient_id': str(p.id),
        'temperature': '36.6',
        'systolic': '110',
        'diastolic': '70',
        'cough': 'нет',
        'chest_pain': 'no',
        'sore_throat': 'no',
        'shortness_of_breath': 'no',
        'overall_condition': 'OK'
    }
    resp = client.post('/readings', data=data, follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers['Location'].endswith('/readings')
    # измерение появилось
    assert Reading.query.count() == 1

def test_reports_route_shows_data(client):
    # создаём пациента + одно измерение
    client.post('/schedule', data={
        'patient_name': 'AAA',
        'age': '50',
        'disease': 'X',
        'frequency': '2',
        'health_indicators': 'T'
    })
    p = Patient.query.first()
    client.post('/readings', data={
        'patient_id': str(p.id),
        'temperature': '37.5',
        'systolic': '130',
        'diastolic': '85',
        'cough': 'нет',
        'chest_pain': 'no',
        'sore_throat': 'no',
        'shortness_of_breath': 'no',
        'overall_condition': 'OK'
    })
    # получаем страницу отчётов
    resp = client.get('/reports')
    assert resp.status_code == 200
    assert b'AAA' in resp.data
    assert b'37.5' in resp.data
