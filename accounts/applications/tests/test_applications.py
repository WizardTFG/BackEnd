from django.contrib.auth.models import User
from django.urls import reverse

from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models.users import UserProfile
from accounts.applications.models import (
    Application,
    ApplicationClinician,
    Form,
)


class ApplicationTestBase(APITestCase):
    """Datos y utilidades compartidas por los tests de aplicaciones."""

    def create_user(self, username, email, is_admin=False):
        user = User.objects.create_user(
            username=username,
            email=email,
            password='test_password123',
        )

        UserProfile.objects.create(
            user=user,
            google_sub=f'google_{username}',
            is_admin=is_admin,
        )

        return user

    def create_application(self, creator, name='Aplicación de prueba'):
        return Application.objects.create(
            name=name,
            created_by=creator,
        )

    def application_payload(self, **overrides):
        payload = {
            'name': 'Nueva aplicación',
            'description': 'Descripción de prueba',
            'clinician_ids': [],
            'forms': [
                {
                    'name': 'Formulario inicial',
                    'fields': [
                        {
                            'label': 'Nombre',
                            'type': 'text',
                            'required': True,
                        },
                        {
                            'label': 'Edad',
                            'type': 'number',
                            'required': False,
                        },
                    ],
                },
            ],
        }

        payload.update(overrides)
        return payload


class CreateApplicationTests(ApplicationTestBase):

    def setUp(self):
        self.url = '/api/applications/'

        self.admin = self.create_user(
            'admin',
            'admin@example.com',
            is_admin=True,
        )

        self.clinician = self.create_user(
            'clinician',
            'clinician@example.com',
        )

        self.normal_user = self.create_user(
            'normal',
            'normal@example.com',
        )

    def test_no_autenticado_no_puede_crear_aplicacion(self):
        response = self.client.post(
            self.url,
            self.application_payload(),
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

        self.assertEqual(Application.objects.count(), 0)

    def test_usuario_normal_no_puede_crear_aplicacion(self):
        self.client.force_authenticate(user=self.normal_user)

        response = self.client.post(
            self.url,
            self.application_payload(),
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_403_FORBIDDEN,
        )

        self.assertEqual(Application.objects.count(), 0)

    def test_administrador_puede_crear_aplicacion(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            self.url,
            self.application_payload(),
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(Application.objects.count(), 1)

        application = Application.objects.first()

        self.assertEqual(application.name, 'Nueva aplicación')
        self.assertEqual(application.description, 'Descripción de prueba')
        self.assertEqual(application.created_by, self.admin)

        self.assertTrue(application.slug)
        self.assertEqual(response.data['slug'], application.slug)

    def test_crear_aplicacion_con_clinicos(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            self.url,
            self.application_payload(
                clinician_ids=[self.clinician.id],
            ),
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(ApplicationClinician.objects.count(), 1)

        assignment = ApplicationClinician.objects.first()

        self.assertEqual(
            assignment.clinician,
            self.clinician,
        )

        self.assertEqual(
            assignment.application,
            Application.objects.first(),
        )

    def test_crear_aplicacion_con_formularios(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            self.url,
            self.application_payload(),
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_201_CREATED,
        )

        application = Application.objects.first()

        self.assertEqual(application.forms.count(), 1)

        form = application.forms.first()

        self.assertEqual(form.name, 'Formulario inicial')
        self.assertEqual(len(form.fields), 2)

    def test_slug_se_genera_automaticamente_y_es_unico(self):
        self.client.force_authenticate(user=self.admin)

        first_response = self.client.post(
            self.url,
            self.application_payload(name='Mi aplicación'),
            format='json',
        )

        second_response = self.client.post(
            self.url,
            self.application_payload(name='Mi aplicación'),
            format='json',
        )

        self.assertEqual(
            first_response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(
            second_response.status_code,
            status.HTTP_201_CREATED,
        )

        self.assertEqual(first_response.data['slug'], 'mi-aplicacion')
        self.assertEqual(second_response.data['slug'], 'mi-aplicacion-1')

    def test_nombre_es_obligatorio(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.post(
            self.url,
            self.application_payload(name=''),
            format='json',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_400_BAD_REQUEST,
        )

        self.assertIn('name', response.data)


class MyApplicationsTests(ApplicationTestBase):

    def setUp(self):
        self.url = '/api/applications/my-applications/'

        self.admin = self.create_user(
            'admin',
            'admin@example.com',
            is_admin=True,
        )

        self.other_admin = self.create_user(
            'other_admin',
            'other_admin@example.com',
            is_admin=True,
        )

        self.clinician = self.create_user(
            'clinician',
            'clinician@example.com',
        )

        self.other_clinician = self.create_user(
            'other_clinician',
            'other_clinician@example.com',
        )

        self.admin_application = self.create_application(
            self.admin,
            'Aplicación del administrador',
        )

        self.other_application = self.create_application(
            self.other_admin,
            'Aplicación de otro administrador',
        )

        ApplicationClinician.objects.create(
            application=self.admin_application,
            clinician=self.clinician,
        )

    def test_no_autenticado_no_puede_consultar_aplicaciones(self):
        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_administrador_solo_ve_sus_aplicaciones(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]['id'],
            self.admin_application.id,
        )

    def test_clinico_ve_aplicaciones_asignadas(self):
        self.client.force_authenticate(user=self.clinician)

        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]['id'],
            self.admin_application.id,
        )

    def test_clinico_no_ve_aplicaciones_no_asignadas(self):
        self.client.force_authenticate(user=self.other_clinician)

        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(len(response.data), 0)


class PublicApplicationTests(ApplicationTestBase):

    def setUp(self):
        self.admin = self.create_user(
            'admin',
            'admin@example.com',
            is_admin=True,
        )

        self.application = self.create_application(
            self.admin,
            'Aplicación pública',
        )

        self.form = Form.objects.create(
            application=self.application,
            name='Formulario de prueba',
            fields=[
                {
                    'label': 'Nombre',
                    'type': 'text',
                    'required': True,
                },
            ],
        )

        self.url = f'/api/applications/{self.application.slug}/'

    def test_consultar_aplicacion_sin_autenticacion(self):
        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(
            response.data['id'],
            self.application.id,
        )

        self.assertEqual(
            response.data['slug'],
            self.application.slug,
        )

    def test_consultar_aplicacion_incluye_formularios(self):
        response = self.client.get(self.url)

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(len(response.data['forms']), 1)

        self.assertEqual(
            response.data['forms'][0]['name'],
            'Formulario de prueba',
        )

    def test_slug_inexistente_devuelve_404(self):
        response = self.client.get(
            '/api/applications/no-existe/',
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_404_NOT_FOUND,
        )


class SearchCliniciansTests(ApplicationTestBase):

    def setUp(self):
        self.url = '/api/applications/clinicians/'

        self.admin = self.create_user(
            'admin',
            'admin@example.com',
            is_admin=True,
        )

        self.clinician = self.create_user(
            'juan',
            'juan@example.com',
        )

        self.other_user = self.create_user(
            'pedro',
            'pedro@example.com',
        )

        self.clinician.first_name = 'Juan'
        self.clinician.last_name = 'García'
        self.clinician.save()

    def test_busqueda_requiere_autenticacion(self):
        response = self.client.get(
            self.url,
            {'q': 'Juan'},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_401_UNAUTHORIZED,
        )

    def test_buscar_clinico_por_nombre(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            self.url,
            {'q': 'Juan'},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]['id'],
            self.clinician.id,
        )

    def test_busqueda_corta_devuelve_lista_vacia(self):
        self.client.force_authenticate(user=self.admin)

        response = self.client.get(
            self.url,
            {'q': 'J'},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(response.data, [])

    def test_busqueda_no_devuelve_al_usuario_actual(self):
        self.client.force_authenticate(user=self.clinician)

        response = self.client.get(
            self.url,
            {'q': 'Juan'},
        )

        self.assertEqual(
            response.status_code,
            status.HTTP_200_OK,
        )

        self.assertEqual(response.data, [])
