import pytest
from app import app as flask_app, db, User
from werkzeug.security import generate_password_hash

@pytest.fixture
def app():
    # тестовая конфигурация
    flask_app.config.update({
        'TESTING': True,
        'DEBUG': False,
    })
    with flask_app.app_context():
        db.create_all()
        yield flask_app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    # создаём клиент и логиним его
    client = app.test_client()
    with app.app_context():
        u = User(username='test', password=generate_password_hash('test'))
        db.session.add(u)
        db.session.commit()
    client.post('/login', data={'username': 'test', 'password': 'test'}, follow_redirects=True)
    return client

@pytest.fixture(autouse=True)
def reset_tables(app):
    # сброс БД перед каждым тестом
    with app.app_context():
        db.drop_all()
        db.create_all()
    yield
