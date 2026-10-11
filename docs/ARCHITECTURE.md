# Arquitectura de NetSentinel (v0.2)

## Objetivo

Aplicación local de observabilidad de red con instalación sencilla, inventario de procedencia explícita y límites de seguridad conservadores. La ausencia de una observación no se interpreta como prueba de desconexión o intrusión.

## Componentes

- `cli.py`: opciones de inicio; loopback es el host predeterminado.
- `main.py`: API HTTP FastAPI y panel estático.
- `discovery.py`: contrato `DiscoveryProvider`, proveedor de comandos del sistema y combinación de fuentes ARP/vecinos/NDP.
- `vendor.py`: reconocimiento de prefijos OUI mediante archivo CSV local opcional; no hace consultas externas.
- `database.py`: SQLite, migraciones aditivas, inventario, direcciones por dispositivo, observaciones, eventos e historial de lecturas.
- `diagnostics.py`: pruebas de gateway, DNS y conectividad IP solo cuando el usuario lo solicita.
- `static/index.html`: interfaz en español, inventario, detalle agregado de direcciones, actividad y lecturas recientes.

## Flujo de descubrimiento

1. La interfaz solicita `POST /api/scan`.
2. `default_providers()` construye los proveedores compatibles con el sistema operativo actual.
3. Cada proveedor ejecuta únicamente un comando fijo de consulta de la tabla local de vecinos, con tiempo de espera acotado y sin `shell=True`.
4. `discover_from_providers()` combina las salidas, descarta duplicados IP/MAC y permite que los errores aislados se registren sin abortar toda la lectura.
5. `parse_neighbor_output()` valida IP y MAC, contempla IPv4/IPv6, y conserva el nombre de la fuente.
6. SQLite registra la ejecución, cada dirección observada y la relación de la dirección con el dispositivo.
7. Una MAC nueva crea un evento revisable. Un cambio de IPv4 principal solo se registra cuando la nueva lectura observa otra IPv4 y la anterior no está presente en ese conjunto de observaciones. Sigue siendo una pista, no una atribución de identidad.

## Modelo de datos

- `devices`: identidad de inventario por MAC, IP principal, confianza manual, nombre, notas, fabricante OUI opcional y metadatos de consulta OUI.
- `device_addresses`: conjunto histórico de direcciones IPv4/IPv6 vistas por MAC, primera/última observación, interfaz y fuente.
- `scans`: ejecución de la lectura, fuentes consultadas, recuento de dispositivos y avisos.
- `observations`: cada observación IP/MAC asociada a una lectura.
- `events`: eventos de revisión y estado de reconocimiento.

El inicio de v0.2 añade columnas y `device_addresses` de forma aditiva. Al inicializar una base v0.1, la IP previamente guardada se migra al historial para no perder la ficha existente.

## Fabricantes OUI

La aplicación no distribuye una base de fabricantes ni transmite las MAC. Si el usuario coloca `oui.csv` en el directorio de datos, `vendor.py` acepta un formato reducido `prefix,vendor` o el CSV de asignaciones con `Assignment,Organization Name`. Se admite el prefijo de 6, 7 o 9 dígitos hexadecimales y se prioriza la asignación más específica. La procedencia se registra como base OUI local y se guarda la fecha de consulta.

## Seguridad y privacidad

- API en loopback por defecto; no desplegar en una interfaz de red sin controles adicionales.
- Las fuentes de descubrimiento son pasivas: no se realiza escaneo activo ni se modifica la configuración de la red.
- Los comandos no contienen datos enviados desde el navegador y no se concatenan entradas de usuario en una shell.
- El diagnóstico tiene una acción separada porque genera tráfico.
- La MAC localmente administrada puede ser aleatoria o manual y no se trata como una prueba de riesgo.
- La IP puede cambiar por DHCP, movilidad o configuración; los eventos son pistas para revisión humana.
- En POSIX se limitan permisos del directorio de datos y SQLite cuando el sistema de archivos lo permite.

## Pruebas

Las pruebas de parser usan muestras fijas por plataforma; persistencia y API utilizan bases temporales. La suite no requiere escanear una red real. Se recomienda mantener CI en Windows, macOS y Linux.
