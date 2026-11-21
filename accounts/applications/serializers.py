from rest_framework import serializers
from django.contrib.auth.models import User

from .models import Application, ApplicationClinician, Form


class ClinicianSerializer(serializers.ModelSerializer):
    name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'name', 'email']

    def get_name(self, obj):
        return obj.get_full_name() or obj.username


class FormSerializer(serializers.ModelSerializer):
    class Meta:
        model = Form
        fields = ['id', 'name', 'fields']


class ApplicationSerializer(serializers.ModelSerializer):
    slug = serializers.SlugField(read_only=True)

    clinician_ids = serializers.ListField(
        child=serializers.IntegerField(),
        write_only=True,
        required=False
    )

    forms = FormSerializer(many=True, required=False)

    class Meta:
        model = Application
        fields = [
            'id',
            'name',
            'slug',
            'description',
            'clinician_ids',
            'forms',
            'created_at'
        ]

    def create(self, validated_data):
        clinician_ids = validated_data.pop('clinician_ids', [])
        forms_data = validated_data.pop('forms', [])

        application = Application.objects.create(**validated_data)

        clinicians = User.objects.filter(id__in=set(clinician_ids))

        ApplicationClinician.objects.bulk_create([
            ApplicationClinician(
                application=application,
                clinician=clinician
            )
            for clinician in clinicians
        ])

        for form_data in forms_data:
            Form.objects.create(
                application=application,
                **form_data
            )

        return application