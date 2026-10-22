"""Errores de dominio compartidos por los servicios de NetSentinel Forense."""


class ForensicConflictError(ValueError):
    """La operación choca con el estado actual del caso o de la evidencia.

    El tipo permite que la API distinga un conflicto de negocio de un dato inválido
    sin depender de las palabras utilizadas en el mensaje.
    """
