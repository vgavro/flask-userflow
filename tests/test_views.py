def test_status(client):
    resp = client.get('/user/status')
    assert resp.status_code == 200
    assert not resp.json['user']
    assert resp.json['locale'] == 'en'
    assert resp.json['timezone'] == 'UTC'


def test_set_i18n_success(client):
    # set locale
    resp = client.post('/user/set_i18n', json={'locale': 'ru'})
    assert resp.status_code == 200

    resp = client.get('/user/status')
    assert resp.status_code == 200
    assert resp.json['locale'] == 'ru'
    assert resp.json['timezone'] == 'UTC'

    # set timezone
    resp = client.post('/user/set_i18n', json={'timezone': 'Europe/Kiev'})
    assert resp.status_code == 200

    resp = client.get('/user/status')
    assert resp.status_code == 200
    assert resp.json['locale'] == 'ru'
    assert resp.json['timezone'] == 'Europe/Kiev'

    # set locale and timezone same time
    resp = client.post('/user/set_i18n', json={'timezone': 'Asia/Kuala_Lumpur',
                                               'locale': 'en'})
    assert resp.status_code == 200

    resp = client.get('/user/status')
    assert resp.status_code == 200
    assert resp.json['locale'] == 'en'
    assert resp.json['timezone'] == 'Asia/Kuala_Lumpur'


def test_set_i18n_fail(client):
    # unknown locale
    resp = client.post('/user/set_i18n', json={'locale': 'es'})
    assert resp.status_code == 422
    assert resp.json['errors']['locale']
    assert 'timezone' not in resp.json['errors']

    # unknown timezone
    resp = client.post('/user/set_i18n', json={'timezone': 'unknown'})
    assert resp.status_code == 422
    assert resp.json['errors']['timezone']
    assert 'locale' not in resp.json['errors']


def test_timezones(client):
    resp = client.get('/user/timezones')
    assert resp.status_code == 200
    assert resp.json['timezones']


def test_login_success(client):
    resp = client.post('/user/status', json={'email': 'vgavro@gmail.com', 'password': 'password'})
    assert resp.status_code == 200
    assert resp.json.get('auth_token')
    email = resp.json['user']['email']
    assert email == 'vgavro@gmail.com'

    resp = client.get('/user/status')
    assert resp.status_code == 200
    assert resp.json['user']['email'] == email


def test_login_fail(client):
    # no email
    resp = client.post('/user/status', json={'email': 'matt@lp.com', 'password': 'password'})
    assert resp.status_code == 422
    assert 'email' in resp.json['errors']

    resp = client.get('/user/status')
    assert resp.status_code == 200
    assert not resp.json['user']

    # bad password
    resp = client.post('/user/status', json={'email': 'vgavro@gmail.com',
                                             'password': 'badpassword'})
    assert resp.status_code == 422
    assert 'password' in resp.json['errors']
    assert 'email' not in resp.json['errors']

    resp = client.get('/user/status')
    assert resp.status_code == 200
    assert not resp.json['user']


def test_logout_success(client):
    test_login_success(client)
    resp = client.delete('/user/status')
    assert resp.status_code == 200
    assert not resp.json['user']

    resp = client.get('/user/status')
    assert resp.status_code == 200
    assert not resp.json['user']


def test_register_start_success(client):
    resp = client.post('/user/register', json={'email': 'matt@lp.com'})
    assert resp.status_code == 200


def test_register_start_fail(client):
    resp = client.post('/user/register', json={'email': 'vgavro@gmail.com'})
    assert resp.status_code == 422
    assert 'email' in resp.json['errors']


def test_register_confirm_success(client):
    email = 'py@test.com'
    token = client.application.userflow.register_confirm_serializer.dumps(email)
    resp = client.post('/user/register_confirm', json={'token': token})
    assert resp.status_code == 200
    assert resp.json['email'] == email


def test_register_confirm_fail(client):
    resp = client.post('/user/register_confirm', json={})
    assert resp.status_code == 422
    assert 'token' in resp.json['errors']

    token = client.application.userflow.register_confirm_serializer.dumps('py@test.com')
    resp = client.post('/user/register_confirm', json={'token': ''.join(reversed(token))})
    assert resp.status_code == 422
    assert 'token' in resp.json['errors']


def test_register_finish_success(client):
    email = 'py@test.com'
    token = client.application.userflow.register_confirm_serializer.dumps(email)
    resp = client.put('/user/register', json={
        'name': 'Vasya Pupkin',
        'email': 'wrong@email.com',
        'token': token,
        'password': 'Some password',
        'confirm_password': 'Some password',
        'timezone': 'Europe/Kiev',
        'locale': 'ru',
    })
    assert resp.status_code == 200

    resp = client.get('/user/status')
    assert resp.status_code == 200
    assert resp.json['user']['email'] == email


def test_register_finish_fail(client):
    token = client.application.userflow.register_confirm_serializer.dumps('py@test.com')

    resp = client.put('/user/register', json={
        'name': 'Vasya Pupkin',
        'token': token,
        'password': '',
        'confirm_password': '',
        'timezone': 'Europe/Kiev',
        'locale': 'ru',
    })
    assert resp.status_code == 422
    assert 'password' in resp.json['errors']

    resp = client.put('/user/register', json={
        'name': 'Vasya Pupkin',
        'token': token,
        'password': 'Some password',
        'confirm_password': 'Wrong password',
        'timezone': 'Europe/Kiev',
        'locale': 'ru',
    })
    assert resp.status_code == 422
    assert 'confirm_password' in resp.json['errors']


def test_restore_success(client):
    resp = client.post('/user/restore', json={'email': 'vgavro@gmail.com'})
    assert resp.status_code == 200


def test_restore_start_fail(client):
    resp = client.post('/user/restore', json={'email': 'matt@lp.com'})
    assert resp.status_code == 422
    assert 'email' in resp.json['errors']


def test_restore_confirm_success(client):
    email = 'vgavro@gmail.com'
    token = client.application.userflow.restore_confirm_serializer.dumps(email)
    resp = client.post('/user/restore_confirm', json={'token': token})
    assert resp.status_code == 200
    assert resp.json['email'] == email


def test_restore_confirm_fail(client):
    resp = client.post('/user/restore_confirm', json={})
    assert resp.status_code == 422
    assert 'token' in resp.json['errors']

    token = client.application.userflow.restore_confirm_serializer.dumps('py@test.com')
    resp = client.post('/user/restore_confirm', json={'token': ''.join(reversed(token))})
    assert resp.status_code == 422
    assert 'token' in resp.json['errors']


def test_restore_finish_success(client):
    email = 'vgavro@gmail.com'
    new_password = 'newpassword'
    token = client.application.userflow.restore_confirm_serializer.dumps(email)
    resp = client.put('/user/restore', json={'token': token, 'password': new_password,
                                             'confirm_password': new_password})
    assert resp.status_code == 200
    with client.application.app_context():
        user = client.application.userflow.datastore.find_user(email=email)
        assert user.verify_password(new_password)


def test_restore_finish_fail(client):
    email = 'matt@lp.com'
    token = client.application.userflow.restore_confirm_serializer.dumps(email)
    resp = client.put('/user/restore', json={'token': token, 'password': 'password',
                                             'confirm_password': 'password'})
    assert resp.status_code == 422
    assert 'token' in resp.json['errors']

    email = 'vgavro@gmail.com'
    token = client.application.userflow.restore_confirm_serializer.dumps(email)
    resp = client.put('/user/restore', json={'token': token, 'password': 'password',
                                             'confirm_password': 'wrong_password'})
    assert resp.status_code == 422
    assert 'confirm_password' in resp.json['errors']
