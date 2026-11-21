from django.contrib.auth.models import User
from django.db.models import Q

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status

from .models import Application, ApplicationClinician
from .serializers import ClinicianSerializer, ApplicationSerializer


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
    # Solo los administradores pueden crear aplicaciones.
    if not hasattr(request.user, 'profile') or not request.user.profile.is_admin:
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

    serializer = ApplicationSerializer(applications, many=True)

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