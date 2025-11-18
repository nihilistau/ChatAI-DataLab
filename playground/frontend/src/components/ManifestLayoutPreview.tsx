import type {
  PlaygroundAction,
  PlaygroundLayoutSection,
  PlaygroundManifestRecord,
  PlaygroundWidget
} from "../types";

interface ManifestLayoutPreviewProps {
  manifest: PlaygroundManifestRecord;
}

const getWidgetLabel = (widget: PlaygroundWidget, index: number): string => {
  if (widget.title) return widget.title;
  const labelProp = widget.props && typeof widget.props.label === "string" ? widget.props.label : undefined;
  if (labelProp) return labelProp;
  return `Widget ${index + 1}`;
};

const getWidgetHint = (widget: PlaygroundWidget): string => {
  const placeholder = widget.props && typeof widget.props.placeholder === "string" ? widget.props.placeholder : undefined;
  if (placeholder) {
    return placeholder;
  }
  const valuePreview = widget.props && typeof widget.props.value === "string" ? widget.props.value : undefined;
  return valuePreview ? valuePreview.slice(0, 70) : "";
};

const renderWidget = (widget: PlaygroundWidget, index: number) => {
  const hint = getWidgetHint(widget);
  return (
    <li key={widget.id ?? `${widget.type}-${index}`} className="manifest-widget-item">
      <div>
        <strong>{getWidgetLabel(widget, index)}</strong>
        <small>{widget.type}</small>
      </div>
      {hint && <p>{hint}</p>}
    </li>
  );
};

const renderSection = (section: PlaygroundLayoutSection, index: number) => {
  const widgets = section.widgets ?? [];
  return (
    <article key={section.id ?? `section-${index}`} className="manifest-section-card">
      <header>
        <p className="eyebrow">Section</p>
        <h3>{section.title ?? `Section ${index + 1}`}</h3>
      </header>
      {section.description && <p className="text-muted">{section.description}</p>}
      {widgets.length ? (
        <ul className="manifest-widget-list">{widgets.map(renderWidget)}</ul>
      ) : (
        <p className="text-muted">No widgets defined yet.</p>
      )}
    </article>
  );
};

const renderAction = (action: PlaygroundAction) => {
  return (
    <li key={action.id ?? action.route}>
      <div>
        <strong>{action.title ?? action.id ?? action.route}</strong>
        <small>
          {action.method ?? "POST"} · {action.route}
        </small>
      </div>
      {action.description && <p>{action.description}</p>}
    </li>
  );
};

const formatTimestamp = (value: number) => new Date(value).toLocaleString();

function ManifestLayoutPreview({ manifest }: ManifestLayoutPreviewProps) {
  const sections = manifest.manifest.layout?.sections ?? [];
  const actions = manifest.manifest.actions ?? [];
  const metadata = manifest.manifest.metadata ?? {};

  const getMetadataString = (key: string): string | undefined => {
    const value = (metadata as Record<string, unknown>)[key];
    return typeof value === "string" ? value : undefined;
  };

  const heroBlurb = getMetadataString("hero");
  const metadataNotes = getMetadataString("notes");

  return (
    <div className="manifest-preview">
      <div className="manifest-meta-grid">
        <article className="manifest-meta-card">
          <p className="eyebrow">Namespace</p>
          <h3>
            {manifest.tenant}/{manifest.playground}
          </h3>
          <small>
            Revision {manifest.revision}
            {manifest.revisionLabel ? ` · ${manifest.revisionLabel}` : ""}
          </small>
        </article>
        <article className="manifest-meta-card">
          <p className="eyebrow">Authorship</p>
          <h3>{manifest.author ?? "Unknown"}</h3>
          <small>{manifest.cookbook ?? "Cookbook"} · {manifest.recipe ?? "Recipe"}</small>
        </article>
        <article className="manifest-meta-card">
          <p className="eyebrow">Updated</p>
          <h3>{formatTimestamp(manifest.updatedAt)}</h3>
          <small>Checksum {manifest.checksum.slice(0, 8)}</small>
        </article>
      </div>
      {(manifest.notes || metadataNotes || heroBlurb) && (
        <p className="manifest-notes text-muted">
          {manifest.notes ?? metadataNotes ?? heroBlurb}
        </p>
      )}
      {sections.length > 0 ? (
        <div className="manifest-section-grid">{sections.map(renderSection)}</div>
      ) : (
        <p className="text-muted">Publish a layout with at least one section to preview it here.</p>
      )}
      {actions.length > 0 && (
        <div className="manifest-actions-panel">
          <header>
            <p className="eyebrow">Actions</p>
            <h3>Backend bindings</h3>
          </header>
          <ul>{actions.map(renderAction)}</ul>
        </div>
      )}
    </div>
  );
}

export default ManifestLayoutPreview;
