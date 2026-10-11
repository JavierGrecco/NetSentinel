# Plan de implementación

## Estado actual — rama de trabajo 0.10

La versión estable 0.9.0 reúne inventario local, descubrimiento acotado a RFC 1918, confianza manual, historial, diagnóstico guiado, monitorización Ping/TCP/HTTP(S), incidentes, tendencias, exportaciones y respaldo SQLite.

Esta rama inicia el primer módulo de herramientas: **consulta DNS de solo lectura**. La API permite consultar un nombre de host mediante el resolvedor del sistema operativo y devuelve las direcciones A/AAAA que el sistema logra resolver. No modifica DNS, no realiza escaneo de puertos y no acepta URLs completas.

## Etapas

1. **Módulo DNS básico:** validación estricta de host, resolución A/AAAA, salida estable y pruebas con el resolvedor simulado.
2. **Interfaz DNS:** formulario separado con validación, estados vacíos y errores comprensibles; sin ejecutar consultas automáticamente al abrir la aplicación.
3. **DNS inverso y contexto local:** PTR opcional y detección portable de configuración DNS, distinguiendo datos conocidos de inferencias.
4. **Inventario enriquecido:** nombres DNS como metadatos opcionales con caché, procedencia y desactivación.
5. **DHCP/router:** adaptadores optativos, inicialmente de solo lectura y por proveedor.
6. **Topología y métricas:** cuando los datos disponibles sean suficientes y se definan límites de privacidad.

## Criterios de aceptación

Cada función nueva requiere pruebas automatizadas, mensajes de error comprensibles, documentación de permisos y tráfico, límites explícitos y una opción de desactivación cuando corresponda. Las pruebas no deben depender de Internet, una red real ni privilegios de administrador. La versión estable no debe cambiar hasta completar revisión y CI.
