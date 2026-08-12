"use client";

/**
 * Standing attribution for the datasets behind every answer.
 *
 * Named and linked rather than badged with a city seal: this analyses the City of Atlanta's
 * own equity designation, and an official mark would read as the city endorsing conclusions
 * it has never seen.
 */

const INK_MUTED = "#898781";
const GRIDLINE = "#2c2c2a";

const SOURCES = [
  {
    label: "MARTA GTFS schedule",
    href: "https://itsmarta.com/app-developer-resources.aspx",
  },
  {
    label: "MARTA GTFS-realtime",
    href: "https://gtfs-rt.itsmarta.com/TMGTFSRealTimeWebService/vehicle/vehiclepositions.pb",
  },
  {
    label: "City of Atlanta Communities of Concern 2025",
    href: "https://services2.arcgis.com/zLeajbicrDRLQcny/arcgis/rest/services/Communities_of_Concern_2025/FeatureServer/4",
  },
  {
    label: "City of Atlanta NPU boundaries",
    href: "https://gis.atlantaga.gov/dpcd/rest/services/AdministrativeArea/GeopoliticalArea/MapServer/2",
  },
];

export function Sources() {
  return (
    <footer
      className="mt-8 border-t pt-4 text-xs leading-relaxed"
      style={{ color: INK_MUTED, borderColor: GRIDLINE }}
    >
      <span className="font-semibold uppercase tracking-wider">Data</span>{" "}
      {SOURCES.map((source, i) => (
        <span key={source.href}>
          <a
            href={source.href}
            target="_blank"
            rel="noopener noreferrer"
            className="underline underline-offset-2 hover:no-underline"
            style={{ color: INK_MUTED }}
          >
            {source.label}
          </a>
          {i < SOURCES.length - 1 ? " · " : ""}
        </span>
      ))}
      <p className="mt-2">
        All public, unmodified at source. Not affiliated with or endorsed by the City of
        Atlanta or MARTA.
      </p>
    </footer>
  );
}
