import { useMemo } from "react";
import { useManifest } from "../context/ManifestContext";

function ManifestWidgetSummary() {
  const { manifest, loading, error, status, tenant, playground } = useManifest();

  const sections = useMemo(() => manifest?.manifest.layout?.sections ?? [], [manifest]);
  const widgets = useMemo(() => sections.flatMap((section) => section.widgets ?? []), [sections]);
  const actions = manifest?.manifest.actions ?? [];

  const widgetTypeCounts = useMemo(() => {
    return widgets.reduce<Record<string, number>>((acc, widget) => {
      const key = widget.type ?? "widget";
      acc[key] = (acc[key] ?? 0) + 1;
      return acc;
    }, {});
  }, [widgets]);

  const topWidgetTypes = useMemo(() => {
    return Object.entries(widgetTypeCounts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 3);
  }, [widgetTypeCounts]);

  return (
    <section className="intel-card manifest-summary-card">
      <header>
        <p className="eyebrow">Manifest wiring</p>
        <h3>
          {tenant}/{playground}
        </h3>
      </header>
      {loading && <p className="text-muted">Syncing manifest…</p>}
      {!loading && error && <p className="error">{error}</p>}
      {!loading && !error && !manifest && status && <p className="text-muted">{status}</p>}
      {!loading && manifest && (
        <>
          <ul className="manifest-summary-stats">
            <li>
              <strong>{sections.length}</strong>
              <span>Sections</span>
            </li>
            <li>
              <strong>{widgets.length}</strong>
              <span>Widgets</span>
            </li>
            <li>
              <strong>{actions.length}</strong>
              <span>Actions</span>
            </li>
          </ul>
          {widgets.length === 0 && <p className="text-muted">No widgets defined yet—publish from Kitchen to hydrate.</p>}
          {widgets.length > 0 && (
            <div className="manifest-summary-types">
              <p className="eyebrow">Top widget types</p>
              <ul>
                {topWidgetTypes.map(([type, count]) => (
                  <li key={type}>
                    <span>{type}</span>
                    <small>{count}</small>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {actions.length > 0 && (
            <div className="manifest-summary-actions">
              <p className="eyebrow">Defined actions</p>
              <ul>
                {actions.slice(0, 3).map((action) => (
                  <li key={action.id ?? action.route}>
                    <strong>{action.title ?? action.route}</strong>
                    <small>{action.method ?? "POST"} · {action.route}</small>
                  </li>
                ))}
              </ul>
              {actions.length > 3 && <small className="text-muted">+{actions.length - 3} more actions in manifest</small>}
            </div>
          )}
        </>
      )}
    </section>
  );
}

export default ManifestWidgetSummary;
