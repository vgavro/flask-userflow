def test_status(client):
    resp = client.get('/user/status')
    assert resp.status_code == 200
    assert not resp.json['user']
    assert resp.json['locale'] == 'en'
    assert resp.json['timezone'] == 'UTC'


def test_set_i18n(client):
    resp = client.post('/user/set_i18n', json={'locale': 'ru'})
    assert resp.status_code == 200
    print resp.json
    resp = client.get('/user/status')
    assert resp.status_code == 200
    assert resp.json['locale'] == 'ru'
