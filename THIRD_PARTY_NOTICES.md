# Aviso de terceros: cartografía para el mapa mundial

El archivo `src/netsentinel/static/world_110m.geojson` se distribuye en el repositorio de origen `ossianericson/netsentinel` como recurso cartográfico local.

**Copyright (c) 2024 Ossian Ericson — licencia MIT para el recurso tal como se distribuye en ese repositorio.**

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

Origen del recurso: https://github.com/ossianericson/netsentinel/blob/main/ui/assets/world_110m.geojson

La geometría describe fronteras territoriales aproximadas a escala mundial; no aporta ubicaciones de IP. Las coordenadas de IP proceden de la base GeoIP local que configure la persona usuaria y no de este archivo cartográfico.


## Datos de prueba GeoIP de MaxMind

Los archivos `tests/fixtures/geoip/GeoIP2-City-Test.mmdb` y `tests/fixtures/geoip/GeoLite2-ASN-Test.mmdb` proceden del directorio `test-data/` del repositorio [maxmind/MaxMind-DB](https://github.com/maxmind/MaxMind-DB). Son bases de prueba para validar el lector MMDB, no bases de producción ni datos de usuarios.

**Copyright (c) 2013–2026 MaxMind, Inc.** Los fixtures se ofrecen bajo licencia Apache 2.0 o MIT; los textos completos se conservan en `tests/fixtures/geoip/LICENSE-APACHE` y `tests/fixtures/geoip/LICENSE-MIT`. Se usan únicamente en pruebas y no forman parte de los recursos estáticos incluidos en el wheel de NetSentinel.
