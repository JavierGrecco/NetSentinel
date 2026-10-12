# Política de seguridad

NetSentinel es una herramienta local de observabilidad de red. Este archivo resume cómo reportar problemas de seguridad y enlaza la descripción técnica vigente.

## Versiones y alcance

Se priorizan los problemas reproducibles en la rama `main` y en la versión estable más reciente, cuando exista. La política técnica, los controles y las limitaciones se mantienen en [`docs/SECURITY.md`](docs/SECURITY.md).

NetSentinel está diseñado para ejecutarse localmente. El lanzador oficial solo permite direcciones loopback; rechaza enlaces a la LAN o a todas las interfaces porque el producto todavía no proporciona autenticación ni autorización para acceso remoto. El descubrimiento de red es manual, limitado a subredes IPv4 privadas y debe utilizarse únicamente sobre redes autorizadas.

## Cómo reportar una vulnerabilidad

**No publiques detalles explotables, pruebas de concepto, credenciales, tokens ni datos de usuarios en issues, discusiones o pull requests públicos.**

1. Si GitHub muestra la opción privada **Report a vulnerability** en la pestaña **Security** de este repositorio, úsala para enviar el reporte.
2. Si esa opción no está disponible, contacta al mantenedor por el canal público indicado en su [perfil de GitHub](https://github.com/JavierGrecco) y solicita un canal privado. En el primer mensaje no incluyas detalles explotables ni datos sensibles.

Incluye en el reporte privado la versión o commit afectado, el impacto observado, los pasos mínimos para reproducirlo y cualquier mitigación conocida. No hay un SLA de respuesta o de publicación prometido; los reportes se revisarán según severidad, alcance y capacidad de reproducción.

## Límites y prácticas responsables

- Prueba únicamente equipos, servicios y redes que administras o para los que tienes autorización explícita.
- La telemetría de navegación es opt-in y la extensión está desactivada por defecto. No recopiles ni adjuntes datos personales reales en reportes.
- La auditoría automatizada y CI reducen riesgos, pero no garantizan ausencia de vulnerabilidades.
