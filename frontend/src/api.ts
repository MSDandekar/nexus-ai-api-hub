const API_BASE = ""; // Relative path allows serving directly from same host/port

export async function fetchMetrics() {
  const res = await fetch(`${API_BASE}/api/v1/analytics/dashboard`);
  if (!res.ok) throw new Error("Failed to load metrics");
  return res.json();
}

export async function fetchConnectors() {
  const res = await fetch(`${API_BASE}/api/v1/connectors`);
  if (!res.ok) throw new Error("Failed to load connectors");
  return res.json();
}

export async function fetchConnector(slug: string) {
  const res = await fetch(`${API_BASE}/api/v1/connectors/${slug}`);
  if (!res.ok) throw new Error("Failed to load connector");
  return res.json();
}

export async function createConnector(payload: any) {
  const res = await fetch(`${API_BASE}/api/v1/connectors`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to create connector");
  }
  return res.json();
}

export async function updateConnector(slug: string, payload: any) {
  const res = await fetch(`${API_BASE}/api/v1/connectors/${slug}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const err = await res.json();
    throw new Error(err.detail || "Failed to update connector");
  }
  return res.json();
}

export async function toggleConnector(slug: string) {
  const res = await fetch(`${API_BASE}/api/v1/connectors/${slug}/toggle`, {
    method: "PATCH",
  });
  if (!res.ok) throw new Error("Failed to toggle connector");
  return res.json();
}

export async function deleteConnector(slug: string) {
  const res = await fetch(`${API_BASE}/api/v1/connectors/${slug}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to delete connector");
  return res.json();
}

export async function fetchConnectorDocs(slug: string) {
  const res = await fetch(`${API_BASE}/api/v1/connectors/${slug}/docs`);
  if (!res.ok) throw new Error("Failed to load documentation");
  return res.json();
}

export async function runConnectorApi(slug: string, payload: any, apiKey: string, files?: Record<string, File>) {
  const hasFiles = files && Object.keys(files).length > 0;
  let headers: Record<string, string> = {
    "X-API-Key": apiKey,
  };
  let body: any;

  if (hasFiles) {
    const formData = new FormData();
    for (const [k, v] of Object.entries(payload)) {
      formData.append(k, typeof v === "object" ? JSON.stringify(v) : String(v));
    }
    for (const [k, file] of Object.entries(files)) {
      formData.append(k, file);
    }
    body = formData;
  } else {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(payload);
  }

  const res = await fetch(`${API_BASE}/api/v1/run/${slug}`, {
    method: "POST",
    headers,
    body,
  });

  const data = await res.json();
  return { status: res.status, ok: res.ok, data };
}

export async function fetchModels() {
  const res = await fetch(`${API_BASE}/api/v1/models`);
  if (!res.ok) throw new Error("Failed to load model catalog");
  return res.json();
}

export async function fetchKeys() {
  const res = await fetch(`${API_BASE}/api/v1/keys`);
  if (!res.ok) throw new Error("Failed to load keys");
  return res.json();
}

export async function createKey(name: string) {
  const res = await fetch(`${API_BASE}/api/v1/keys`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name }),
  });
  if (!res.ok) throw new Error("Failed to create key");
  return res.json();
}

export async function toggleKey(id: number) {
  const res = await fetch(`${API_BASE}/api/v1/keys/${id}/toggle`, {
    method: "PATCH",
  });
  if (!res.ok) throw new Error("Failed to toggle key");
  return res.json();
}

export async function deleteKey(id: number) {
  const res = await fetch(`${API_BASE}/api/v1/keys/${id}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error("Failed to delete key");
  return res.json();
}

export async function fetchLogs(limit = 50, offset = 0, connector?: string, status?: string) {
  const params = new URLSearchParams({ limit: String(limit), offset: String(offset) });
  if (connector) params.set("connector", connector);
  if (status) params.set("status", status);
  const res = await fetch(`${API_BASE}/api/v1/analytics/logs?${params.toString()}`);
  if (!res.ok) throw new Error("Failed to load logs");
  return res.json();
}

export async function generateBlueprint(description: string) {
  const res = await fetch(`${API_BASE}/api/v1/blueprint/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ description }),
  });
  if (!res.ok) throw new Error("Failed to generate blueprint");
  return res.json();
}

export async function compareModels(payload: any) {
  const res = await fetch(`${API_BASE}/api/v1/evaluations/compare`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Failed to execute model comparison");
  return res.json();
}
