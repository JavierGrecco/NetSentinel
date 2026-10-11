# Base OUI local opcional

NetSentinel puede asociar un fabricante a una MAC a partir de una base CSV guardada localmente. No hay consultas externas por MAC.

## Ubicación

El archivo se llama `oui.csv` y va dentro del directorio de datos (`~/.netsentinel/` de forma predeterminada, también en Windows). Para pruebas, se puede cambiar el directorio completo mediante `NETSENTINEL_DATA_DIR`.

## Formatos admitidos

Formato mínimo:

```csv
prefix,vendor
AABBCC,Ejemplo de fabricante
AABBCCD,Fabricante de asignación más específica
```

Formato de registros de asignaciones:

```csv
Assignment,Organization Name
AABBCC,Ejemplo de fabricante
AABBCCD,Fabricante de asignación más específica
```

Se normalizan guiones, dos puntos y mayúsculas. Se consideran prefijos de 24 bits (6 dígitos hexadecimales, MA-L), 28 bits (7, MA-M) y 36 bits (9, MA-S), y se elige la coincidencia más larga. No se incorpora una base de terceros al repositorio: revisá los términos de uso, redistribución y la fecha del registro que elijas. Si la MAC no coincide con la base disponible, el panel muestra que el fabricante no se pudo identificar.

El fabricante es una asociación del prefijo, no una autenticación del dispositivo. Las MAC locales/aleatorias pueden no tener una asignación OUI útil.
