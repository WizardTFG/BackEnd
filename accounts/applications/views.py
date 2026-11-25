from datetime import date
from decimal import Decimal, InvalidOperation

from django.contrib.auth.models import User
from django.db.models import Q

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status

from .models import (
    Application,
    ApplicationClinician,
    ApplicationResponse
)

from .serializers import (
    ClinicianSerializer,
    ApplicationSerializer
)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def search_clinicians(request):
    query = request.GET.get('q', '').strip()

    if len(query) < 2:
        return Response([])

    users = User.objects.filter(
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(email__icontains=query)
    ).exclude(
        id=request.user.id
    ).distinct()[:10]

    serializer = ClinicianSerializer(users, many=True)

    return Response(serializer.data)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_application(request):

    if (
        not hasattr(request.user, 'profile')
        or not request.user.profile.is_admin
    ):
        return Response(
            {'error': 'No tienes permisos para crear aplicaciones.'},
            status=status.HTTP_403_FORBIDDEN
        )

    serializer = ApplicationSerializer(data=request.data)

    if serializer.is_valid():
        application = serializer.save(created_by=request.user)

        return Response(
            ApplicationSerializer(application).data,
            status=status.HTTP_201_CREATED
        )

    return Response(
        serializer.errors,
        status=status.HTTP_400_BAD_REQUEST
    )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def my_applications(request):

    is_admin = (
        hasattr(request.user, 'profile')
        and request.user.profile.is_admin
    )

    if is_admin:
        applications = Application.objects.filter(
            created_by=request.user
        )
    else:
        applications = Application.objects.filter(
            clinicians__clinician=request.user
        )

    applications = applications.distinct().prefetch_related(
        'forms',
        'clinicians__clinician'
    )

    serializer = ApplicationSerializer(
        applications,
        many=True
    )

    return Response(serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def application_by_slug(request, slug):

    try:
        application = Application.objects.prefetch_related(
            'forms'
        ).get(slug=slug)

    except Application.DoesNotExist:
        return Response(
            {'error': 'Aplicación no encontrada'},
            status=status.HTTP_404_NOT_FOUND
        )

    serializer = ApplicationSerializer(application)

    return Response(serializer.data)


def validate_answers(application, answers):

    if not isinstance(answers, dict):
        return {
            'answers': 'Las respuestas deben tener un formato válido.'
        }

    expected_fields = {}

    for form in application.forms.all():
        if not isinstance(form.fields, list):
            return {
                'fields': 'La configuración de los formularios no es válida.'
            }

        for index, field in enumerate(form.fields):

            if not isinstance(field, dict):
                return {
                    'fields': 'La configuración de los campos no es válida.'
                }

            key = f'field-{form.id}-{index}'
            expected_fields[key] = field

    errors = {}

    for key, field in expected_fields.items():

        value = answers.get(key)

        field_type = field.get('type')
        required = field.get('required', False)

        if not isinstance(required, bool):
            errors[key] = 'La configuración de obligatoriedad no es válida.'
            continue

        if required:
            if field_type == 'checkbox':
                if value is not True:
                    errors[key] = 'Este campo es obligatorio.'
                    continue
            elif value is None or value == '':
                errors[key] = 'Este campo es obligatorio.'
                continue

        if value is None or value == '':
            continue

        if field_type == 'number':
            try:
                Decimal(str(value))
            except (InvalidOperation, ValueError):
                errors[key] = 'Introduce un número válido.'

        elif field_type == 'date':
            try:
                date.fromisoformat(str(value))
            except (ValueError, TypeError):
                errors[key] = 'Introduce una fecha válida.'

        elif field_type == 'checkbox':
            if not isinstance(value, bool):
                errors[key] = 'El valor debe ser verdadero o falso.'

        elif field_type in ('text', 'textarea'):
            if not isinstance(value, str):
                errors[key] = 'Introduce un texto válido.'

        else:
            errors[key] = 'El tipo de campo no es válido.'

    unexpected_fields = set(answers.keys()) - set(expected_fields.keys())

    if unexpected_fields:
        errors['fields'] = 'Se han recibido campos no válidos.'

    return errors


@api_view(['POST'])
@permission_classes([AllowAny])
def submit_application_response(request, slug):

    try:
        application = Application.objects.prefetch_related(
            'forms'
        ).get(slug=slug)

    except Application.DoesNotExist:
        return Response(
            {'error': 'Aplicación no encontrada.'},
            status=status.HTTP_404_NOT_FOUND
        )

    answers = request.data.get('answers')

    errors = validate_answers(application, answers)

    if errors:
        return Response(
            errors,
            status=status.HTTP_400_BAD_REQUEST
        )

    response = ApplicationResponse.objects.create(
        application=application,
        answers=answers
    )

    return Response(
        {
            'message': 'Respuestas guardadas correctamente.',
            'id': response.id,
            'submitted_at': response.submitted_at
        },
        status=status.HTTP_201_CREATED
    )