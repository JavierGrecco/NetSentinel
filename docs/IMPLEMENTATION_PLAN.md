# Plan de implementación

## Estado actual — rama de trabajo 0.10

La versión estable 0.9.0 reúne inventario local, descubrimiento acotado a RFC 1918, confianza manual, historial, diagnóstico guiado, monitorización Ping/TCP/HTTP(S), incidentes, tendencias, exportaciones y respaldo SQLite.

Esta rama incorpora herramientas DNS de solo lectura. La pantalla `/tools` permite consultar direcciones A/AAAA a partir de un nombre de host y consultar el PTR de una IP ingresada explícitamente, usando el resolvedor del sistema operativo. No modifica la configuración DNS ni realiza escaneo de puertos. Los nombres obtenidos se presentan como datos declarados por DNS, nunca como identidad verificada.

## Etapas

1. **Módulo DNS básico:** implementado en la rama; validación estricta de host, resolución A/AAAA y pruebas con el resolvedor simulado.
2. **Interfaz DNS:** implementada en la rama con formularios separados, estados accesibles y consultas explícitas.
3. **DNS inverso y contexto local:** consulta PTR por IP implementada y probada con mocks; queda pendiente detectar la configuración DNS de forma portable y diferenciar mejor los tipos de fallo.
4. **Inventario enriquecido:** nombres DNS como metadatos opcionales con caché, procedencia y desactivación.
5. **DHCP/router:** adaptadores optativos, inicialmente de solo lectura y por proveedor.
6. **Topología y métricas:** cuando los datos disponibles sean suficientes y se definan límites de privacidad.

## Criterios de aceptación

Cada función nueva requiere pruebas automatizadas, mensajes de error comprensibles, documentación de permisos y tráfico, límites explícitos y una opción de desactivación cuando corresponda. Las pruebas no deben depender de Internet, una red real ni privilegios de administrador. La versión estable no debe cambiar hasta completar revisión y CI.
