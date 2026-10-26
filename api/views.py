from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response

@api_view(['GET'])
def test_conexion(request):
    return Response({"status": "conectado", "mensaje": "Backend Django funcionando con éxito"})