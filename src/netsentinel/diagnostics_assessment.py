"""Evaluación pura de resultados de conectividad.

Traduce comprobaciones observadas a un resumen prudente y pasos recomendados.
No ejecuta comandos, abre sockets, escribe logs ni modifica la red.
"""
from __future__ import annotations

from typing import Any


def build_assessment(checks: list[dict[str, Any]]) -> dict[str, Any]:
    """Resume los hallazgos y propone pasos prudentes sin afirmar causas no verificadas."""
    statuses = {str(check.get("name")): check.get("status") for check in checks}
    gateway = statuses.get("Puerta de enlace")
    router = statuses.get("Respuesta del router")
    dns = statuses.get("Resolución DNS")
    external = statuses.get("Conectividad IP externa")

    if dns == "timeout":
        title = "La consulta DNS tardó demasiado"
        if external == "ok":
            summary = (
                "La prueba IP externa respondió, pero la consulta DNS superó el límite de espera. "
                "Puede ser un resolvedor lento o un problema temporal; no confirma una avería permanente."
            )
            next_steps = [
                "Volvé a ejecutar el diagnóstico una vez para comprobar si fue algo transitorio.",
                "Probá abrir un sitio HTTPS desde el navegador.",
                "No cambies la configuración DNS hasta tener una segunda señal del problema.",
            ]
        else:
            summary = (
                "La consulta DNS superó el límite de espera y la prueba de ping externa tampoco respondió. "
                "Con estos datos no se puede determinar una causa única."
            )
            next_steps = [
                "Confirmá que Wi-Fi o Ethernet estén conectados y probá abrir un sitio HTTPS.",
                "Si el problema continúa, revisá la VPN o consultá al administrador de la red.",
                "Volvé a ejecutar el diagnóstico antes de modificar DNS o firewall.",
            ]
        status = "warning"
    elif dns == "ok" and external == "ok":
        if router == "warning":
            title = "La conectividad funciona; el router no respondió al ping"
            summary = (
                "DNS resolvió el dominio y la prueba IP externa respondió. "
                "El router puede bloquear ICMP; ese resultado, por sí solo, no indica una avería."
            )
            next_steps = [
                "No cambies la configuración de la red solo por este resultado.",
                "Si una aplicación concreta falla, comprobá ese servicio con una prueba HTTP o TCP.",
            ]
        elif gateway != "ok":
            title = "La conectividad externa funciona"
            summary = (
                "La resolución DNS y la prueba IP externa respondieron, aunque no se pudo "
                "identificar automáticamente la puerta de enlace."
            )
            next_steps = [
                "La detección de la puerta de enlace varía según el sistema operativo.",
                "Si las aplicaciones funcionan, no hace falta corregir la ruta por este dato aislado.",
            ]
        else:
            title = "Conectividad básica correcta"
            summary = "Se pudo resolver un dominio y la prueba de conectividad IP externa respondió."
            next_steps = [
                "Si una aplicación sigue sin funcionar, revisá ese servicio con un monitor HTTP o TCP."
            ]
        status = "ok"
    elif dns != "ok" and external == "ok":
        title = "Posible problema de DNS"
        summary = (
            "La prueba IP externa respondió, pero el sistema no pudo resolver example.com. "
            "La conectividad por IP existe; la resolución de nombres podría estar fallando."
        )
        next_steps = [
            "Revisá la configuración DNS de la computadora o del router.",
            "Si el problema persiste, consultá al administrador de la red antes de cambiar otros ajustes.",
        ]
        status = "warning"
    elif dns == "ok" and external != "ok":
        title = "DNS funciona, pero el ping externo no respondió"
        summary = (
            "La resolución de nombres funciona. La prueba de ping a 1.1.1.1 no respondió; "
            "algunas redes filtran ICMP, así que esto no demuestra por sí solo una caída de Internet."
        )
        next_steps = [
            "Probá abrir un sitio HTTPS desde el navegador.",
            "Si tampoco carga, revisá la conexión, la VPN y el firewall, o consultá al administrador de la red.",
        ]
        status = "warning"
    else:
        if router == "ok":
            title = "La red local responde, pero no se confirmó la salida a Internet"
            summary = (
                "El router respondió, pero fallaron la resolución DNS y el ping externo. "
                "Podría haber un problema de DNS o de conectividad de salida."
            )
        elif gateway != "ok":
            title = "No se pudo confirmar la conexión"
            summary = (
                "No se identificó la puerta de enlace y tampoco se confirmaron DNS ni conectividad IP. "
                "Un filtro de ICMP también puede afectar parte de estas pruebas."
            )
        else:
            title = "No se pudo confirmar la conectividad externa"
            summary = (
                "No respondieron DNS ni el ping externo. Puede haber una falla de red, "
                "aunque las políticas de DNS o ICMP también pueden influir."
            )
        next_steps = [
            "Confirmá que Wi-Fi o Ethernet estén conectados.",
            "Revisá si una VPN, un firewall o la configuración del router afectan la conexión.",
            "Probá abrir un sitio HTTPS; no cambies la configuración DNS solo por un resultado de ping.",
        ]
        status = "warning"

    return {"status": status, "title": title, "summary": summary, "next_steps": next_steps}
