# Fixtures GeoIP para pruebas

Estos archivos binarios se copian sin modificación desde el repositorio oficial [maxmind/MaxMind-DB](https://github.com/maxmind/MaxMind-DB), directorio `test-data/`.

| Archivo | Origen | Uso |
|---|---|---|
| `GeoIP2-City-Test.mmdb` | `test-data/GeoIP2-City-Test.mmdb` | Comprobar lectura real de país, ciudad y coordenadas |
| `GeoLite2-ASN-Test.mmdb` | `test-data/GeoLite2-ASN-Test.mmdb` | Comprobar número y organización ASN |

Los dos archivos se distribuyen con copyright de MaxMind, Inc. y bajo licencia Apache 2.0 o MIT. Se incluyen ambos textos completos en esta carpeta. No contienen inventarios ni registros de NetSentinel. No descargar bases reales ni consultar Internet durante las pruebas.

SHA del origen al incorporar los fixtures:
- City: `f622e28b8ba309cf2c5fd5738df3dab0af6f4876`
- ASN: `381f68b615d2a2ae729b9553a3553b0a1b7b5526`
