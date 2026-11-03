# Vista general de la arquitectura

NetSentinel se instala y ejecuta como **una aplicación local**. FastAPI sirve la interfaz web y la API en loopback; los servicios organizan los casos de uso; los repositorios gestionan las operaciones SQLite. No se despliega como un conjunto de microservicios.

## Diagrama

```mermaid
flowchart TB
    operator["Persona operadora"]
    browser["Navegador local"]
    extension["Extensión Chromium opcional"]
    cli["CLI / lanzadores"]

    subgraph app["Proceso local de NetSentinel"]
        fastapi["FastAPI: páginas, API y controles transversales"]
        ui["Interfaz web estática"]
        services["Servicios de aplicación"]
        inventory["Inventario y descubrimiento"]
        monitoring["Monitorización e incidentes"]
        activity["Actividad e importaciones autorizadas"]
        geolocation["Mapa IP / geolocalización opcional"]
        tools["Diagnóstico, DNS y TLS"]
        findings["Hallazgos y contexto de evidencia"]
        forensic["Forense (experimental)"]
        repos["Repositorios por dominio"]
        sqlite[("SQLite local")]
    end

    osdata["Sistema operativo: interfaces y tabla de vecinos"]
    targets["Hosts y servicios configurados"]
    imported["CSV / registros Zeek importados"]
    geoip["Base GeoIP local opcional"]
    webhook["Webhook HTTPS opcional"]

    operator --> browser
    operator --> cli
    browser --> ui
    ui <--> fastapi
    extension -->|"sesiones y metadatos autorizados"| fastapi
    cli -->|"inicia el servidor local"| fastapi
    fastapi --> services
    services --> inventory
    services --> monitoring
    services --> activity
    services --> geolocation
    services --> tools
    services --> findings
    services --> forensic
    repos <--> sqlite
    inventory --> repos
    monitoring --> repos
    activity --> repos
    findings --> repos
    forensic --> repos
    inventory --> osdata
    monitoring --> targets
    tools --> targets
    imported --> activity
    geoip --> geolocation
    geolocation --> repos
    inventory --> findings
    monitoring --> findings
    monitoring -.->|"solo si se configura"| webhook
```

## Cómo leer el diseño

- **Una instalación, un proceso principal:** la interfaz y la API se sirven localmente. Los módulos internos se llaman mediante servicios Python; no se hacen llamadas HTTP entre módulos del mismo proceso.
- **Responsabilidades separadas:** los routers validan y traducen solicitudes; los servicios coordinan casos de uso; los repositorios poseen las consultas de cada dominio.
- **Persistencia local:** SQLite conserva inventario, observaciones, monitorización y datos importados. Compartir el archivo no significa que cada módulo pueda consultar directamente las tablas de los demás.
- **Fuentes explícitas:** el descubrimiento utiliza datos del sistema operativo y comprobaciones bajo demanda. La actividad externa llega mediante importación o extensión opcional habilitada expresamente; Zeek no se ejecuta dentro de NetSentinel.
- **Integraciones opcionales:** el mapa mundial requiere una base GeoIP instalada localmente. Los avisos por webhook solo se envían si la persona operadora configura un destino HTTPS.
- **Forense experimental:** comparte el marco de API y persistencia, pero no debe interpretarse como un sistema de custodia validado ni como una herramienta forense completa.

## Límites y decisiones

La arquitectura busca mantener simple el despliegue y estrictas las fronteras internas. No hay un broker, clúster, base de datos remota ni plano de control central. Separar módulos en procesos independientes solo se justificaría más adelante por una necesidad demostrada de escalado, aislamiento o despliegue independiente.

El diagrama es una vista conceptual, no un mapa de cada importación o ruta. Para los detalles actuales de composición, repositorios, reglas de dependencias y pruebas de arquitectura, consultá [Arquitectura](ARCHITECTURE.md) y [ADR-001](ADR-001-MODULAR-MONOLITH.md).
