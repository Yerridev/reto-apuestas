from django.urls import reverse
from rest_framework import status

from apps.users.choices import AccountStatus
from apps.users.models import User

class TestRegisterView:
    url = '/api/auth/register/'
    valid_payload = {
        'email': 'newuser@example.com',
        'dni': '876543252',
        'first_name': 'New',
        'last_name': 'User',
        'birth_date': '1995-06-15',
        'password': 'SecurePass123!',
    }

    def test_register_success(self, api_client, db):
        resp = api_client.post(self.url, self.valid_payload, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data['email'] == 'newuser@example.com'
        assert resp.data['first_name'] == 'New'
        assert 'password' not in resp.data
        created = User.objects.get(email='newuser@example.com')
        assert created.account_status == AccountStatus.PENDIENTE_VERIFICACION

    def test_register_invalid_dni(self, api_client, db):
        payload = {**self.valid_payload, 'dni': '123456780'}
        resp = api_client.post(self.url, payload, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert 'dni' in resp.data

    def test_register_underage(self, api_client, db):
        payload = {**self.valid_payload, 'birth_date': '2010-01-01'}
        resp = api_client.post(self.url, payload, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert 'birth_date' in resp.data

    def test_register_duplicate_email(self, api_client, user, db):
        payload = {
            **self.valid_payload,
            'email': 'test@example.com',
            'dni': '876543252',
        }
        resp = api_client.post(self.url, payload, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert 'email' in resp.data

    def test_register_duplicate_dni(self, api_client, user, db):
        payload = {
            **self.valid_payload,
            'email': 'another@example.com',
            'dni': '123456781',
        }
        resp = api_client.post(self.url, payload, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert 'dni' in resp.data

    def test_register_weak_password(self, api_client, db):
        payload = {**self.valid_payload, 'password': '123'}
        resp = api_client.post(self.url, payload, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert 'password' in resp.data


class TestTokenView:
    url = '/api/token/'

    def test_token_obtain_success(self, api_client, user, db):
        resp = api_client.post(self.url, {
            'email': 'test@example.com',
            'password': 'SecurePass123!',
        }, format='json')
        assert resp.status_code == status.HTTP_200_OK
        assert 'access' in resp.data
        assert 'refresh' in resp.data

    def test_token_obtain_invalid_password(self, api_client, user, db):
        resp = api_client.post(self.url, {
            'email': 'test@example.com',
            'password': 'wrongpass',
        }, format='json')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_token_obtain_nonexistent_user(self, api_client, db):
        resp = api_client.post(self.url, {
            'email': 'nobody@example.com',
            'password': 'somepass',
        }, format='json')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


class TestMeView:
    url = '/api/auth/me/'

    def test_me_authenticated(self, auth_client):
        resp = auth_client.get(self.url)
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['email'] == 'test@example.com'
        assert resp.data['account_status'] == 'pendiente_verificacion'

    def test_me_unauthenticated(self, api_client):
        resp = api_client.get(self.url)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


class TestUpdateLimitsView:
    url = '/api/auth/limits/'

    def test_set_limit_success(self, auth_client):
        resp = auth_client.post(self.url, {
            'field_name': 'deposit_limit_daily',
            'new_value': '500.0000',
        }, format='json')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['deposit_limit_daily'] == '500.0000'

    def test_raise_limit_blocked_by_cooldown(self, auth_client):
        auth_client.post(self.url, {
            'field_name': 'deposit_limit_daily',
            'new_value': '100.0000',
        }, format='json')

        resp = auth_client.post(self.url, {
            'field_name': 'deposit_limit_daily',
            'new_value': '500.0000',
        }, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
        assert 'subir este límite' in str(resp.data)

    def test_lower_limit_instant(self, auth_client):
        auth_client.post(self.url, {
            'field_name': 'deposit_limit_daily',
            'new_value': '1000.0000',
        }, format='json')

        resp = auth_client.post(self.url, {
            'field_name': 'deposit_limit_daily',
            'new_value': '300.0000',
        }, format='json')
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data['deposit_limit_daily'] == '300.0000'

    def test_invalid_field_name(self, auth_client):
        resp = auth_client.post(self.url, {
            'field_name': 'invalid_field',
            'new_value': '500.0000',
        }, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_unauthenticated(self, api_client):
        resp = api_client.post(self.url, {
            'field_name': 'deposit_limit_daily',
            'new_value': '500.0000',
        }, format='json')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


class TestSelfExclusionView:
    url = '/api/auth/self-exclusion/'

    def test_exclude_temporal(self, auth_client):
        resp = auth_client.post(self.url, {
            'exclusion_type': '7_dias',
        }, format='json')
        assert resp.status_code == status.HTTP_201_CREATED
        assert resp.data['exclusion_id'] is not None

    def test_exclude_indefinite(self, auth_client):
        resp = auth_client.post(self.url, {
            'exclusion_type': 'indefinida',
        }, format='json')
        assert resp.status_code == status.HTTP_201_CREATED

    def test_double_exclusion_blocked(self, auth_client):
        auth_client.post(self.url, {'exclusion_type': '30_dias'}, format='json')

        resp = auth_client.post(self.url, {'exclusion_type': '7_dias'}, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST

    def test_unauthenticated(self, api_client):
        resp = api_client.post(self.url, {
            'exclusion_type': '7_dias',
        }, format='json')
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED


class TestVerifyAccountView:
    url = '/api/auth/verify-account/'

    def test_verify_account_ok_admin(self, api_client, db):
        admin = User.objects.create_superuser(
            email='adminverify@fairbet.pe',
            dni='746960471',
            first_name='Admin',
            last_name='Verify',
            birth_date='1990-01-01',
            password='SecurePass123!',
        )
        target = User.objects.create_user(
            email='pendingverify@fairbet.pe',
            dni='876543252',
            first_name='Pending',
            last_name='User',
            birth_date='1995-01-01',
            password='SecurePass123!',
        )
        api_client.force_authenticate(user=admin)

        resp = api_client.post(self.url, {'user_id': target.id}, format='json')

        assert resp.status_code == status.HTTP_200_OK
        target.refresh_from_db()
        assert target.account_status == AccountStatus.VERIFICADO
        assert resp.data['account_status'] == AccountStatus.VERIFICADO

    def test_verify_account_requires_admin(self, auth_client, user):
        resp = auth_client.post(self.url, {'user_id': user.id}, format='json')
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_verify_account_rejects_autoexcluded(self, api_client, db):
        admin = User.objects.create_superuser(
            email='adminverify2@fairbet.pe',
            dni='102687740',
            first_name='Admin',
            last_name='Verify',
            birth_date='1990-01-01',
            password='SecurePass123!',
        )
        target = User.objects.create_user(
            email='autoexcluded@fairbet.pe',
            dni='123456781',
            first_name='Auto',
            last_name='Excluded',
            birth_date='1995-01-01',
            password='SecurePass123!',
        )
        target.account_status = AccountStatus.AUTOEXCLUIDO
        target.save(update_fields=['account_status'])
        api_client.force_authenticate(user=admin)

        resp = api_client.post(self.url, {'user_id': target.id}, format='json')
        assert resp.status_code == status.HTTP_400_BAD_REQUEST
